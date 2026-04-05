"""
Natural Language Network Query Service

Single LLM call with platform data as context.
The LLM decides whether to use the data, answer technically,
or respond conversationally — all in one pass.

Platform data is pre-fetched in parallel (fast) and provided as
context so the LLM can reference it when relevant.

Persistent memory: conversations are stored per-session so the AI
remembers past exchanges across page reloads.
"""

import json
import os
import asyncio
import httpx
from datetime import datetime
from typing import Optional, Dict, List
from sqlalchemy.orm import Session
from models.schemas import ChatRequest, ChatResponse, LLMRequest, LLMMessage, InteractionType
from services.llm_adapter import call_llm
from shared.logger import setup_logger

logger = setup_logger(__name__)

# Internal service URLs
DEVICE_SERVICE_URL = os.getenv("DEVICE_SERVICE_URL", "http://device-service:3001")
RULE_SERVICE_URL = os.getenv("RULE_SERVICE_URL", "http://rule-service:3002")
BACKUP_SERVICE_URL = os.getenv("BACKUP_SERVICE_URL", "http://backup-service:3003")
INVENTORY_SERVICE_URL = os.getenv("INVENTORY_SERVICE_URL", "http://inventory-service:3004")
ADMIN_SERVICE_URL = os.getenv("ADMIN_SERVICE_URL", "http://admin-service:3005")
ANALYTICS_SERVICE_URL = os.getenv("ANALYTICS_SERVICE_URL", "http://analytics-service:3006")

# All platform data endpoints for AI context (all GET, all fast)
CONTEXT_ENDPOINTS = {
    # Device Service
    "devices": f"{DEVICE_SERVICE_URL}/devices/",
    "device_groups": f"{DEVICE_SERVICE_URL}/device-groups/",
    "health_summary": f"{DEVICE_SERVICE_URL}/health/summary",
    "metadata_overlaps": f"{DEVICE_SERVICE_URL}/devices/metadata/overlaps",
    # Rule Service
    "compliance": f"{RULE_SERVICE_URL}/audit/compliance",
    "rules": f"{RULE_SERVICE_URL}/rules/",
    "audit_results": f"{RULE_SERVICE_URL}/audit/results",
    # Backup Service
    "backup_summary": f"{BACKUP_SERVICE_URL}/config-backups/devices/summary",
    "drift_summary": f"{BACKUP_SERVICE_URL}/drift-detection/summary",
    # Inventory Service
    "hardware_inventory": f"{INVENTORY_SERVICE_URL}/hardware/inventory",
    # Analytics Service
    "analytics_dashboard": f"{ANALYTICS_SERVICE_URL}/analytics/dashboard/quick-stats",
    "compliance_anomalies": f"{ANALYTICS_SERVICE_URL}/analytics/anomalies",
}

# Max messages to send to LLM (recent ones). Older messages get summarized.
MAX_HISTORY_MESSAGES = 10
# When total messages exceed this, trigger summarization of older ones
SUMMARIZE_THRESHOLD = 20

SYSTEM_PROMPT_BASE = """You are the AI assistant for the Network Audit Platform (NAP), a senior network engineer assistant.

You handle all types of queries naturally:
- Data questions — reference the platform data provided below
- Technical questions — give detailed guidance with CLI examples
- Troubleshooting — step-by-step guidance
- Conversational — respond naturally and briefly

Supported vendors: Cisco IOS-XR, Cisco IOS-XE, Nokia SR OS, Juniper JunOS, Arista EOS.

Guidelines:
- Be concise but thorough. Only respond to the user's latest message.
- Use markdown: **bold**, `code`, tables, lists
- CLI examples in ```code blocks``` with vendor name
- If platform data is empty, say so and suggest next steps
- Do NOT repeat or summarize platform data unless the user asks about it
- You remember our conversation history — use it naturally when relevant"""


async def _fetch_platform_context(auth_token: str = "") -> str:
    """Fetch a compact summary of all platform state in parallel.
    Fetches devices, audit results, backups, drift, hardware, analytics — everything
    the AI might need to answer data questions."""
    headers = {"Authorization": auth_token} if auth_token else {}
    context_parts = []

    async def fetch_one(name: str, url: str) -> tuple:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    return name, resp.json()
                return name, None
        except Exception:
            return name, None

    # Fetch ALL endpoints in parallel
    tasks = [fetch_one(name, url) for name, url in CONTEXT_ENDPOINTS.items()]
    results = await asyncio.gather(*tasks)
    data_map = {name: data for name, data in results if data is not None}

    # --- Devices ---
    if "devices" in data_map:
        devices = data_map["devices"]
        devices = devices if isinstance(devices, list) else devices.get("items", devices.get("devices", []))
        if devices:
            lines = []
            for d in devices[:30]:
                meta = d.get("metadata") or d.get("device_metadata") or {}
                meta_str = ""
                if meta:
                    meta_parts = []
                    if meta.get("system_name"):
                        meta_parts.append(f"sys:{meta['system_name']}")
                    if meta.get("software_version"):
                        meta_parts.append(f"sw:{meta['software_version']}")
                    if meta.get("chassis_type"):
                        meta_parts.append(f"chassis:{meta['chassis_type']}")
                    if meta.get("bgp_asn"):
                        meta_parts.append(f"AS{meta['bgp_asn']}")
                    if meta.get("isis_net"):
                        meta_parts.append(f"ISIS:{meta['isis_net']}")
                    if meta_parts:
                        meta_str = f" [{', '.join(meta_parts)}]"
                lines.append(
                    f"  - {d.get('hostname','?')} | {d.get('vendor','?')} | {d.get('ip','?')} | "
                    f"status:{d.get('status','?')} | compliance:{d.get('compliance','?')}%{meta_str}"
                )
            context_parts.append(f"DEVICES ({len(devices)} total):\n" + "\n".join(lines))

    # --- Device Groups ---
    if "device_groups" in data_map:
        groups = data_map["device_groups"]
        groups = groups if isinstance(groups, list) else groups.get("items", groups.get("groups", []))
        if groups:
            context_parts.append(
                f"DEVICE GROUPS ({len(groups)}): "
                + ", ".join(f"{g.get('name','?')} ({g.get('device_count', '?')} devices)" for g in groups[:10])
            )

    # --- Compliance Summary ---
    if "compliance" in data_map:
        c = data_map["compliance"]
        if isinstance(c, dict):
            context_parts.append(
                f"COMPLIANCE: total_devices={c.get('total_devices',0)}, "
                f"compliant={c.get('compliant_devices',0)}, "
                f"non_compliant={c.get('non_compliant_devices',0)}, "
                f"average_score={c.get('average_compliance',0)}%"
            )

    # --- Health Summary ---
    if "health_summary" in data_map:
        h = data_map["health_summary"]
        if isinstance(h, dict):
            parts = [f"{k}={v}" for k, v in h.items()]
            context_parts.append(f"HEALTH: {', '.join(parts)}")

    # --- Audit Rules ---
    if "rules" in data_map:
        rules = data_map["rules"]
        rules = rules if isinstance(rules, list) else rules.get("items", rules.get("rules", []))
        if rules:
            enabled = [r for r in rules if r.get("enabled", True)]
            context_parts.append(
                f"AUDIT RULES ({len(rules)} total, {len(enabled)} enabled): "
                + ", ".join(f"{r.get('name','?')} [{r.get('severity','?')}]" for r in rules[:15])
            )

    # --- Audit Results ---
    if "audit_results" in data_map:
        results_data = data_map["audit_results"]
        results_list = results_data if isinstance(results_data, list) else results_data.get("items", [])
        if results_list:
            lines = []
            for r in results_list[:20]:
                findings = r.get("findings", [])
                failed = sum(1 for f in findings if f.get("status") == "fail") if findings else 0
                passed = sum(1 for f in findings if f.get("status") == "pass") if findings else 0
                lines.append(
                    f"  - {r.get('device_name', r.get('hostname','?'))}: "
                    f"passed={passed}, failed={failed}, "
                    f"compliance={r.get('compliance_score', r.get('compliance','?'))}%"
                )
            context_parts.append(f"LATEST AUDIT RESULTS ({len(results_list)} devices):\n" + "\n".join(lines))

    # --- Config Backup Summary ---
    if "backup_summary" in data_map:
        backups = data_map["backup_summary"]
        backups = backups if isinstance(backups, list) else backups.get("items", [])
        if backups:
            lines = []
            for b in backups[:15]:
                lines.append(
                    f"  - {b.get('hostname','?')}: {b.get('backup_count',0)} backups, "
                    f"last: {b.get('last_backup','never')}"
                )
            context_parts.append(f"CONFIG BACKUPS ({len(backups)} devices):\n" + "\n".join(lines))

    # --- Drift Detection Summary ---
    if "drift_summary" in data_map:
        drift = data_map["drift_summary"]
        if isinstance(drift, dict):
            context_parts.append(
                f"DRIFT DETECTION: total_devices={drift.get('total_devices',0)}, "
                f"drifted={drift.get('drifted_devices', drift.get('drifted',0))}, "
                f"no_drift={drift.get('no_drift_devices', drift.get('no_drift',0))}, "
                f"no_baseline={drift.get('no_baseline_devices', drift.get('no_baseline',0))}"
            )

    # --- Hardware Inventory ---
    if "hardware_inventory" in data_map:
        inv = data_map["hardware_inventory"]
        inv = inv if isinstance(inv, list) else inv.get("items", [])
        if inv:
            lines = []
            for item in inv[:15]:
                components = item.get("components", [])
                chassis = next((c.get("component_name", "?") for c in components if c.get("component_type") == "chassis"), None)
                lines.append(
                    f"  - {item.get('hostname','?')}: {chassis or 'unknown chassis'}, "
                    f"{len(components)} components"
                )
            context_parts.append(f"HARDWARE INVENTORY ({len(inv)} devices):\n" + "\n".join(lines))

    # --- Metadata Overlaps ---
    if "metadata_overlaps" in data_map:
        overlaps = data_map["metadata_overlaps"]
        if isinstance(overlaps, dict) and any(overlaps.values()):
            overlap_strs = []
            for key, items in overlaps.items():
                if items:
                    overlap_strs.append(f"{key}: {len(items)} conflicts")
            if overlap_strs:
                context_parts.append(f"METADATA OVERLAPS: {', '.join(overlap_strs)}")

    # --- Analytics Dashboard ---
    if "analytics_dashboard" in data_map:
        stats = data_map["analytics_dashboard"]
        if isinstance(stats, dict):
            parts = [f"{k}={v}" for k, v in stats.items() if not isinstance(v, (dict, list))]
            context_parts.append(f"ANALYTICS: {', '.join(parts[:10])}")

    # --- Compliance Anomalies ---
    if "compliance_anomalies" in data_map:
        anomalies = data_map["compliance_anomalies"]
        anomalies = anomalies if isinstance(anomalies, list) else anomalies.get("items", [])
        if anomalies:
            active = [a for a in anomalies if not a.get("acknowledged")]
            if active:
                context_parts.append(
                    f"COMPLIANCE ANOMALIES ({len(active)} active): "
                    + ", ".join(f"{a.get('description', a.get('type','?'))}" for a in active[:5])
                )

    if not context_parts:
        return "Platform data: No devices or data available yet. The platform appears empty."

    return "PLATFORM DATA:\n" + "\n".join(context_parts)


def _load_session(db: Session, session_id: int, user_id: int):
    """Load a chat session from DB. Returns (session_obj, messages_list, summary_str)."""
    from shared.db_models import ChatSessionDB

    session = (
        db.query(ChatSessionDB)
        .filter(ChatSessionDB.id == session_id, ChatSessionDB.user_id == user_id)
        .first()
    )
    if not session:
        return None, [], None
    return session, session.messages or [], session.summary


def _create_session(db: Session, user_id: int, first_message: str):
    """Create a new chat session and auto-title it from the first message."""
    from shared.db_models import ChatSessionDB

    # Auto-title: first 50 chars of the message
    title = first_message[:50].strip()
    if len(first_message) > 50:
        title += "..."

    session = ChatSessionDB(user_id=user_id, title=title, messages=[])
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def _save_messages(db: Session, session, user_msg: str, assistant_msg: str):
    """Append user + assistant messages to the session and save."""
    messages = list(session.messages or [])
    now = datetime.utcnow().isoformat()
    messages.append({"role": "user", "content": user_msg, "timestamp": now})
    messages.append({"role": "assistant", "content": assistant_msg, "timestamp": now})
    session.messages = messages
    session.updated_at = datetime.utcnow()
    db.commit()


async def _maybe_summarize(db: Session, session, llm_request_fn):
    """If conversation is getting long, summarize older messages to save context."""
    messages = session.messages or []
    if len(messages) < SUMMARIZE_THRESHOLD:
        return

    # Keep the last MAX_HISTORY_MESSAGES, summarize the rest
    older = messages[:-MAX_HISTORY_MESSAGES]
    recent = messages[-MAX_HISTORY_MESSAGES:]

    # Build text of older messages for summarization
    older_text = "\n".join(f"{m['role']}: {m['content']}" for m in older)

    summary_prompt = LLMRequest(
        system_prompt="Summarize this conversation concisely. Keep key facts, decisions, device names, and technical details. Be brief (2-4 sentences).",
        user_prompt=older_text[:3000],  # cap input size
        temperature=0.2,
        max_tokens=256,
    )

    try:
        resp = await call_llm(summary_prompt)
        existing_summary = session.summary or ""
        if existing_summary:
            session.summary = f"{existing_summary}\n{resp.content}"
        else:
            session.summary = resp.content

        # Keep only recent messages
        session.messages = recent
        db.commit()
        logger.info(f"Summarized session {session.id}: {len(older)} old messages condensed")
    except Exception as e:
        logger.warning(f"Failed to summarize session {session.id}: {e}")


async def process_chat(
    request: ChatRequest,
    db: Session,
    auth_token: str = "",
    user_id: int = None,
) -> ChatResponse:
    """Process a chat query with proper separation:
    - System prompt: role definition + platform data (reference only)
    - Messages: proper role-based conversation history
    - Current message: the user's actual question (last in messages)
    """

    message = request.message.strip()

    # --- Session management ---
    session_obj = None
    history_messages: List[LLMMessage] = []
    summary_text = ""

    if user_id:
        if request.session_id:
            session_obj, stored_messages, summary = _load_session(db, request.session_id, user_id)
            if session_obj:
                summary_text = summary or ""
                # Convert stored messages to LLMMessage objects
                for msg in stored_messages[-MAX_HISTORY_MESSAGES:]:
                    history_messages.append(LLMMessage(role=msg["role"], content=msg["content"]))
        else:
            session_obj = _create_session(db, user_id, message)

    # Fallback: use conversation_history from request (for clients that don't use sessions)
    if not history_messages and request.conversation_history:
        for msg in (request.conversation_history or [])[-6:]:
            history_messages.append(LLMMessage(role=msg.role, content=msg.content))

    # Pre-fetch platform data (fast, ~100-500ms) — goes into system prompt
    logger.info("Fetching platform context...")
    platform_context = await _fetch_platform_context(auth_token)

    # Build system prompt: base instructions + platform data as reference
    system_prompt = SYSTEM_PROMPT_BASE + "\n\n" + platform_context
    if summary_text:
        system_prompt += f"\n\n[Earlier conversation summary: {summary_text}]"

    # Build messages: history turns + current user message
    messages = list(history_messages)
    messages.append(LLMMessage(role="user", content=message))

    llm_request = LLMRequest(
        system_prompt=system_prompt,
        messages=messages,
        temperature=0.3,
        max_tokens=1024,
    )

    logger.info(f"Calling LLM for: {message[:80]} (history: {len(history_messages)} msgs)")
    llm_response = await call_llm(llm_request)

    # Save to session
    if session_obj:
        _save_messages(db, session_obj, message, llm_response.content)
        await _maybe_summarize(db, session_obj, call_llm)

    interaction_id = _log_interaction(db, message, llm_response)

    return ChatResponse(
        message=llm_response.content,
        session_id=session_obj.id if session_obj else None,
        confidence=0.8,
        interaction_id=interaction_id,
    )


def _log_interaction(db, message, llm_response) -> Optional[int]:
    """Log AI interaction."""
    try:
        from shared.db_models import AIInteractionDB
        interaction = AIInteractionDB(
            interaction_type=InteractionType.CHAT_QUERY.value,
            input_prompt=message,
            ai_response={"content": llm_response.content[:2000]},
            model_used=llm_response.model,
            tokens_used=llm_response.tokens_used,
        )
        db.add(interaction)
        db.commit()
        db.refresh(interaction)
        return interaction.id
    except Exception as e:
        logger.warning(f"Failed to log interaction: {e}")
        return None
