"""
Vendor Knowledge Base & RAG Service
Stores vendor documentation, best practices, and troubleshooting guides.
Powers RAG (Retrieval Augmented Generation) for all AI features.
"""

import json
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_
from models.schemas import LLMRequest
from services.llm_adapter import call_llm
from services.llm_response_parser import safe_extract_json
from shared.logger import setup_logger

logger = setup_logger(__name__)

# Default knowledge base entries for bootstrapping
DEFAULT_ENTRIES = [
    {
        "title": "Cisco IOS-XR BGP Best Practices",
        "content": """BGP Configuration Best Practices for Cisco IOS-XR:
1. Always use MD5 authentication for eBGP peers: neighbor X.X.X.X password <key>
2. Set maximum-prefix limits to prevent route leaks: neighbor X.X.X.X maximum-prefix <limit> <threshold>%
3. Use route-policies for inbound/outbound filtering: neighbor X.X.X.X route-policy <name> in/out
4. Enable BFD for fast failure detection: neighbor X.X.X.X bfd fast-detect
5. Use update-source loopback for iBGP: neighbor X.X.X.X update-source Loopback0
6. Set appropriate timers: timers bgp 10 30 (keepalive 10s, hold 30s)
7. Enable graceful-restart for hitless failover: bgp graceful-restart
8. Use address-family configuration for clean separation
9. Configure soft-reconfiguration inbound for policy changes without reset
10. Use route-reflectors for iBGP scalability""",
        "category": "best_practices",
        "vendor": "cisco_xr",
        "tags": ["bgp", "routing", "security"],
    },
    {
        "title": "Nokia SR OS BGP Best Practices",
        "content": """BGP Configuration Best Practices for Nokia SR OS:
1. Use authentication for all eBGP peers: auth-keychain or tcp-authentication
2. Configure prefix-limit to prevent route table overflow
3. Apply import/export policies on all peers
4. Enable BFD: bfd-enable with appropriate intervals
5. Use system interface as update source for iBGP
6. Configure graceful-restart for NSR
7. Use route-reflectors with cluster-id for iBGP scaling
8. Enable peer-tracking for fast convergence
9. Use communities for traffic engineering
10. Configure damping for unstable prefixes""",
        "category": "best_practices",
        "vendor": "nokia_sros",
        "tags": ["bgp", "routing", "security"],
    },
    {
        "title": "NTP Configuration Standards",
        "content": """NTP Best Practices (Multi-Vendor):
- Configure at least 3 NTP servers for redundancy and accuracy
- Use authentication (MD5 or SHA) for NTP sources
- Prefer local/regional NTP servers over public ones
- Set proper stratum levels
- Cisco IOS-XR: ntp server <ip> prefer, ntp authenticate, ntp authentication-key <id> md5 <key>
- Nokia SR OS: configure system time ntp server <ip> prefer
- Monitor NTP sync status: show ntp status / show system time ntp
- Alert if clock offset exceeds 100ms
- Use loopback interfaces as NTP source""",
        "category": "best_practices",
        "vendor": None,
        "tags": ["ntp", "management", "security"],
    },
    {
        "title": "ACL Security Hardening",
        "content": """Access Control List Security Guidelines:
1. Implement infrastructure ACLs to protect management plane
2. Filter RFC 1918 addresses on external interfaces
3. Block bogon/martian addresses
4. Apply rate-limiting ACLs for control plane protection
5. Use extended ACLs with explicit deny and logging
6. Review and remove unused ACL entries quarterly
7. Cisco IOS-XR: ipv4 access-list <name>, use sequence numbers for easier management
8. Nokia SR OS: configure filter ip-filter/ipv6-filter
9. Document purpose of each ACL entry
10. Test ACLs in lab before production deployment""",
        "category": "best_practices",
        "vendor": None,
        "tags": ["acl", "security", "access-control"],
    },
    {
        "title": "Cisco IOS-XR NETCONF Troubleshooting",
        "content": """Common NETCONF issues on Cisco IOS-XR:
1. Connection refused: Ensure 'netconf-yang agent ssh' is configured
2. Authentication failure: Check AAA config and user credentials
3. Capability mismatch: Verify yang model versions with 'show netconf-yang capabilities'
4. RPC timeout: Increase timeout for large configs, check device load
5. Edit-config failures: Validate XML against yang schema
6. Lock contention: Another session may hold config lock, use 'show netconf-yang sessions'
7. Subscription issues: Check notif-provider configuration
8. Memory issues: Monitor 'show processes memory' for netconf agent
9. SSH subsystem: Ensure 'ssh server netconf port 830' is configured
10. ACL blocking: Check if management ACLs allow port 830""",
        "category": "troubleshooting",
        "vendor": "cisco_xr",
        "tags": ["netconf", "connectivity", "troubleshooting"],
    },
    {
        "title": "Nokia SR OS SSH/NETCONF Troubleshooting",
        "content": """Common NETCONF/SSH issues on Nokia SR OS:
1. Connection refused: Enable NETCONF in 'configure system management-interface netconf'
2. Authentication: Check user profile and access permissions
3. Model-driven: Ensure MD-CLI is enabled for YANG model access
4. Port configuration: Default NETCONF port 830, verify with 'show system security ssh'
5. Session limits: Check max concurrent sessions
6. TLS issues: Verify certificate configuration if using TLS
7. gRPC alternative: Consider gNMI for streaming telemetry
8. Response timeout: Large show commands may time out, increase client timeout
9. Filter issues: Use proper XPATH in get/get-config filters
10. Commit failures: Check candidate config validity before commit""",
        "category": "troubleshooting",
        "vendor": "nokia_sros",
        "tags": ["netconf", "ssh", "connectivity", "troubleshooting"],
    },
    {
        "title": "Config Drift Prevention Strategies",
        "content": """Strategies to Prevent Configuration Drift:
1. Use configuration management tools (Ansible, Terraform) as single source of truth
2. Implement config change approval workflows
3. Schedule regular config backups and comparisons
4. Use NETCONF confirmed-commit with rollback timer
5. Implement RBAC to limit who can make changes
6. Enable config change logging (syslog, TACACS+ accounting)
7. Set up drift detection alerts in NAP
8. Use golden configs/templates per device role
9. Automate compliance audits on schedule
10. Review and remediate drift in maintenance windows""",
        "category": "best_practices",
        "vendor": None,
        "tags": ["drift", "compliance", "management"],
    },
    {
        "title": "MPLS/LDP Security Considerations",
        "content": """MPLS and LDP Security Best Practices:
1. Enable LDP session authentication (MD5)
2. Filter LDP hello messages on untrusted interfaces
3. Use targeted LDP sessions where possible
4. Implement MPLS ACLs on PE-CE boundaries
5. Enable TTL propagation controls
6. Cisco: mpls ldp password required for <acl>
7. Nokia: configure router ldp authentication-keychain
8. Monitor for label spoofing attacks
9. Segment routing preferred over LDP for new deployments
10. Use VRF-aware security policies for L3VPN""",
        "category": "best_practices",
        "vendor": None,
        "tags": ["mpls", "ldp", "security", "routing"],
    },
]


async def list_entries(
    db: Session,
    category: Optional[str] = None,
    vendor: Optional[str] = None,
    limit: int = 50,
) -> dict:
    """List knowledge base entries with optional filtering"""
    from shared.db_models import KnowledgeBaseDB

    query = db.query(KnowledgeBaseDB)
    if category:
        query = query.filter(KnowledgeBaseDB.category == category)
    if vendor:
        query = query.filter(
            or_(KnowledgeBaseDB.vendor == vendor, KnowledgeBaseDB.vendor.is_(None))
        )

    entries = query.order_by(KnowledgeBaseDB.created_at.desc()).limit(limit).all()

    # If no entries exist, bootstrap with defaults
    if not entries and not category and not vendor:
        await _bootstrap_defaults(db)
        entries = db.query(KnowledgeBaseDB).order_by(KnowledgeBaseDB.created_at.desc()).limit(limit).all()

    return {
        "total": len(entries),
        "entries": [
            {
                "id": e.id,
                "title": e.title,
                "content": e.content[:500] + "..." if len(e.content) > 500 else e.content,
                "category": e.category,
                "vendor": e.vendor,
                "tags": e.tags or [],
                "created_by": e.created_by,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in entries
        ],
    }


async def add_entry(
    db: Session,
    title: str,
    content: str,
    category: str = "general",
    vendor: Optional[str] = None,
    tags: Optional[List[str]] = None,
    created_by: Optional[str] = None,
) -> dict:
    """Add a new knowledge base entry"""
    from shared.db_models import KnowledgeBaseDB

    entry = KnowledgeBaseDB(
        title=title,
        content=content,
        category=category,
        vendor=vendor,
        tags=tags or [],
        created_by=created_by,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    return {
        "id": entry.id,
        "title": entry.title,
        "category": entry.category,
        "message": "Knowledge base entry added successfully",
    }


async def delete_entry(db: Session, entry_id: int) -> dict:
    """Delete a knowledge base entry"""
    from shared.db_models import KnowledgeBaseDB

    entry = db.query(KnowledgeBaseDB).filter(KnowledgeBaseDB.id == entry_id).first()
    if not entry:
        raise ValueError(f"Knowledge base entry {entry_id} not found")

    db.delete(entry)
    db.commit()

    return {"status": "deleted", "id": entry_id}


async def query_knowledge(
    db: Session,
    query: str,
    category: Optional[str] = None,
    vendor: Optional[str] = None,
) -> dict:
    """Query the knowledge base using RAG (Retrieval Augmented Generation)"""
    from shared.db_models import KnowledgeBaseDB

    # Step 1: Retrieve relevant entries
    kb_query = db.query(KnowledgeBaseDB)
    if category:
        kb_query = kb_query.filter(KnowledgeBaseDB.category == category)
    if vendor:
        kb_query = kb_query.filter(
            or_(KnowledgeBaseDB.vendor == vendor, KnowledgeBaseDB.vendor.is_(None))
        )

    entries = kb_query.all()

    if not entries:
        # Bootstrap defaults if empty
        await _bootstrap_defaults(db)
        entries = db.query(KnowledgeBaseDB).all()

    # Step 2: Build context from knowledge base
    kb_context = "\n\n---\n\n".join([
        f"[{e.title}] (Category: {e.category}, Vendor: {e.vendor or 'generic'})\n{e.content}"
        for e in entries
    ])

    # Step 3: Use LLM with RAG context
    prompt = f"""Answer this question using ONLY the knowledge base context provided below.
If the knowledge base doesn't contain relevant information, say so clearly.

QUESTION: {query}

KNOWLEDGE BASE:
{kb_context[:12000]}

Provide a clear, actionable answer with specific recommendations. Reference which knowledge base entries you used.

Return JSON:
{{
  "answer": "Your detailed answer here",
  "sources_used": ["Title of KB entry 1", "Title of KB entry 2"],
  "confidence": 0.85,
  "additional_recommendations": ["Any extra suggestions"]
}}"""

    llm_request = LLMRequest(
        system_prompt="You are a network engineering knowledge base assistant. Answer questions using provided documentation context. Be specific and cite your sources.",
        user_prompt=prompt,
        temperature=0.2,
        max_tokens=4096,
    )

    llm_response = await call_llm(llm_request)

    result = safe_extract_json(llm_response.content, fallback={
        "answer": llm_response.content,
        "sources_used": [],
        "confidence": 0.5,
    })

    result["total_entries_searched"] = len(entries)
    result["query"] = query

    # Log interaction
    try:
        from shared.db_models import AIInteractionDB
        interaction = AIInteractionDB(
            interaction_type="knowledge_base_query",
            input_prompt=query,
            ai_response={"answer_length": len(result.get("answer", "")), "sources": result.get("sources_used", [])},
            model_used=llm_response.model,
            tokens_used=llm_response.tokens_used,
        )
        db.add(interaction)
        db.commit()
    except Exception as e:
        logger.warning(f"Failed to log interaction: {e}")

    return result


async def _bootstrap_defaults(db: Session):
    """Bootstrap the knowledge base with default entries"""
    from shared.db_models import KnowledgeBaseDB

    for entry_data in DEFAULT_ENTRIES:
        entry = KnowledgeBaseDB(
            title=entry_data["title"],
            content=entry_data["content"],
            category=entry_data["category"],
            vendor=entry_data.get("vendor"),
            tags=entry_data.get("tags", []),
            created_by="system",
        )
        db.add(entry)

    try:
        db.commit()
        logger.info(f"Bootstrapped {len(DEFAULT_ENTRIES)} default knowledge base entries")
    except Exception as e:
        db.rollback()
        logger.warning(f"Failed to bootstrap knowledge base: {e}")
