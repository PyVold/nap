"""
Natural Language Network Query Service

Optimized for local LLM performance:
- Data queries are formatted DIRECTLY (no LLM needed) — instant response
- Only conversational/technical questions use the LLM
- Keyword-based routing, no JSON parsing from LLM
"""

import json
import os
import httpx
from typing import Optional, Dict, List
from sqlalchemy.orm import Session
from models.schemas import ChatRequest, ChatResponse, LLMRequest, InteractionType
from services.llm_adapter import call_llm
from shared.logger import setup_logger

logger = setup_logger(__name__)

# Internal service URLs
DEVICE_SERVICE_URL = os.getenv("DEVICE_SERVICE_URL", "http://device-service:3001")
RULE_SERVICE_URL = os.getenv("RULE_SERVICE_URL", "http://rule-service:3002")
BACKUP_SERVICE_URL = os.getenv("BACKUP_SERVICE_URL", "http://backup-service:3003")
ANALYTICS_SERVICE_URL = os.getenv("ANALYTICS_SERVICE_URL", "http://analytics-service:3006")

# Keyword-based intent detection
DATA_INTENT_PATTERNS = [
    {
        "keywords": ["device", "devices", "router", "switch", "routers", "switches", "inventory"],
        "functions": ["get_devices"],
        "description": "device inventory",
    },
    {
        "keywords": ["compliance", "compliant", "non-compliant", "score", "posture"],
        "functions": ["get_compliance"],
        "description": "compliance status",
    },
    {
        "keywords": ["audit", "audit result", "findings", "failed", "failures", "violations"],
        "functions": ["get_audit_results"],
        "description": "audit results",
    },
    {
        "keywords": ["rule", "rules", "policy", "policies", "checks"],
        "functions": ["get_rules"],
        "description": "audit rules",
    },
    {
        "keywords": ["health", "status", "up", "down", "unreachable", "reachable"],
        "functions": ["get_health_summary"],
        "description": "device health",
    },
    {
        "keywords": ["config change", "configuration change", "changed", "modified", "changes"],
        "functions": ["get_config_changes"],
        "description": "configuration changes",
    },
    {
        "keywords": ["drift", "drifted", "out of sync", "deviation"],
        "functions": ["get_drift_summary"],
        "description": "configuration drift",
    },
    {
        "keywords": ["group", "groups", "device group"],
        "functions": ["get_device_groups"],
        "description": "device groups",
    },
    {
        "keywords": ["backup", "backups", "config backup", "saved config"],
        "functions": ["get_backup_summary"],
        "description": "configuration backups",
    },
    {
        "keywords": ["overview", "summary", "dashboard", "how is the network", "network status"],
        "functions": ["get_devices", "get_compliance", "get_health_summary"],
        "description": "network overview",
    },
]

# Map function names to actual API calls
FUNCTION_MAP = {
    "get_devices": {"url": f"{DEVICE_SERVICE_URL}/devices/", "method": "GET"},
    "get_device": {"url": f"{DEVICE_SERVICE_URL}/devices/{{device_id}}", "method": "GET"},
    "get_audit_results": {"url": f"{RULE_SERVICE_URL}/audit/results", "method": "GET"},
    "get_compliance": {"url": f"{RULE_SERVICE_URL}/audit/compliance", "method": "GET"},
    "get_rules": {"url": f"{RULE_SERVICE_URL}/rules/", "method": "GET"},
    "get_health_summary": {"url": f"{DEVICE_SERVICE_URL}/health/summary", "method": "GET"},
    "get_config_changes": {"url": f"{BACKUP_SERVICE_URL}/drift-detection/changes", "method": "GET"},
    "get_drift_summary": {"url": f"{BACKUP_SERVICE_URL}/drift-detection/summary", "method": "GET"},
    "get_device_groups": {"url": f"{DEVICE_SERVICE_URL}/device-groups/", "method": "GET"},
    "get_backup_summary": {"url": f"{BACKUP_SERVICE_URL}/config-backups/devices/summary", "method": "GET"},
}

CONVERSATIONAL_PROMPT = """You are the AI assistant for the Network Audit Platform (NAP).

You help network engineers with:
- Networking concepts (BGP, OSPF, MPLS, VPN, ACL, NTP, SNMP, etc.)
- Cisco IOS-XR, Cisco IOS-XE, Nokia SR OS, Juniper JunOS, Arista EOS configuration
- Network security, routing, and operations best practices
- Troubleshooting guidance
- Remediation advice for configuration issues

Be concise and technical. Use markdown: **bold** for emphasis, `code` for commands, lists for steps.
Show vendor CLI examples in code blocks when relevant. Keep answers under 300 words."""


def _detect_data_intent(message: str) -> Optional[Dict]:
    """Detect if the message needs platform data. Returns intent or None."""
    msg_lower = message.lower()
    best_match = None
    best_score = 0
    for pattern in DATA_INTENT_PATTERNS:
        score = sum(1 for kw in pattern["keywords"] if kw in msg_lower)
        if score > best_score:
            best_score = score
            best_match = pattern
    return best_match if best_score > 0 else None


async def _fetch_platform_data(func_names: List[str], auth_token: str = "") -> tuple:
    """Fetch data from platform APIs."""
    results = {}
    queries_executed = []
    headers = {"Authorization": auth_token} if auth_token else {}

    async with httpx.AsyncClient(timeout=15.0) as client:
        for func_name in func_names:
            if func_name not in FUNCTION_MAP:
                continue
            func_config = FUNCTION_MAP[func_name]
            try:
                response = await client.request(
                    method=func_config["method"],
                    url=func_config["url"],
                    headers=headers,
                )
                if response.status_code == 200:
                    results[func_name] = response.json()
                else:
                    results[func_name] = {"error": f"API returned {response.status_code}"}
                queries_executed.append(func_name)
            except Exception as e:
                logger.error(f"Error calling {func_name}: {e}")
                results[func_name] = {"error": str(e)}
    return results, queries_executed


# ============================================================================
# Direct data formatters — no LLM needed, instant response
# ============================================================================

def _format_devices(data) -> str:
    """Format device list into markdown."""
    if isinstance(data, dict) and "error" in data:
        return f"Failed to fetch devices: {data['error']}"
    devices = data if isinstance(data, list) else data.get("items", data.get("devices", []))
    if not devices:
        return "No devices found. Add devices via **Network > Devices** or use **Discovery** to scan your network."

    lines = ["### Devices\n"]
    lines.append("| # | Hostname | Vendor | IP | Status | Compliance |")
    lines.append("|---|----------|--------|----|--------|------------|")
    for i, d in enumerate(devices[:50], 1):
        hostname = d.get("hostname", "N/A")
        vendor = d.get("vendor", "N/A")
        ip = d.get("ip", "N/A")
        status = d.get("status", "N/A")
        comp = d.get("compliance")
        comp_str = f"{comp:.0f}%" if comp is not None else "N/A"
        lines.append(f"| {i} | **{hostname}** | {vendor} | {ip} | {status} | {comp_str} |")

    lines.append(f"\n**Total: {len(devices)} device(s)**")
    return "\n".join(lines)


def _format_compliance(data) -> str:
    """Format compliance summary."""
    if isinstance(data, dict) and "error" in data:
        return f"Failed to fetch compliance data: {data['error']}"
    if not data:
        return "No compliance data available. Run an audit first."

    lines = ["### Compliance Summary\n"]
    total = data.get("total_devices", 0)
    compliant = data.get("compliant_devices", 0)
    avg = data.get("average_compliance", 0)
    lines.append(f"- **Total Devices**: {total}")
    lines.append(f"- **Compliant Devices**: {compliant}")
    lines.append(f"- **Average Compliance Score**: {avg:.1f}%")

    if total > 0:
        non_compliant = total - compliant
        if non_compliant > 0:
            lines.append(f"- **Non-Compliant**: {non_compliant} device(s) need attention")
    return "\n".join(lines)


def _format_audit_results(data) -> str:
    """Format audit results."""
    if isinstance(data, dict) and "error" in data:
        return f"Failed to fetch audit results: {data['error']}"
    results = data if isinstance(data, list) else data.get("items", data.get("results", []))
    if not results:
        return "No audit results found. Run an audit from **Compliance > Run Audit**."

    lines = ["### Audit Results\n"]
    # Count by status
    passed = sum(1 for r in results if r.get("status") == "passed" or r.get("result") == "pass")
    failed = sum(1 for r in results if r.get("status") == "failed" or r.get("result") == "fail")
    lines.append(f"- **Passed**: {passed}")
    lines.append(f"- **Failed**: {failed}")
    lines.append(f"- **Total**: {len(results)}")

    # Show top failures
    failures = [r for r in results if r.get("status") == "failed" or r.get("result") == "fail"][:10]
    if failures:
        lines.append("\n**Top Failures:**")
        for f in failures:
            rule = f.get("rule_name", f.get("rule", "Unknown"))
            device = f.get("device_hostname", f.get("device", "Unknown"))
            severity = f.get("severity", "")
            lines.append(f"- [{severity.upper()}] **{rule}** on {device}")
    return "\n".join(lines)


def _format_rules(data) -> str:
    """Format rules list."""
    if isinstance(data, dict) and "error" in data:
        return f"Failed to fetch rules: {data['error']}"
    rules = data if isinstance(data, list) else data.get("items", data.get("rules", []))
    if not rules:
        return "No audit rules configured. Add rules via **Compliance > Rules** or deploy rule templates."

    lines = ["### Audit Rules\n"]
    lines.append("| Rule | Severity | Category | Enabled |")
    lines.append("|------|----------|----------|---------|")
    for r in rules[:30]:
        name = r.get("name", "N/A")
        severity = r.get("severity", "N/A")
        category = r.get("category", "N/A")
        enabled = "Yes" if r.get("enabled") else "No"
        lines.append(f"| **{name}** | {severity} | {category} | {enabled} |")
    lines.append(f"\n**Total: {len(rules)} rule(s)**")
    return "\n".join(lines)


def _format_health(data) -> str:
    """Format health summary."""
    if isinstance(data, dict) and "error" in data:
        return f"Failed to fetch health data: {data['error']}"
    if not data:
        return "No health data available."

    lines = ["### Device Health Summary\n"]
    if isinstance(data, dict):
        for key, val in data.items():
            label = key.replace("_", " ").title()
            lines.append(f"- **{label}**: {val}")
    return "\n".join(lines)


def _format_generic(func_name: str, data) -> str:
    """Generic formatter for data that doesn't have a specific formatter."""
    if isinstance(data, dict) and "error" in data:
        return f"Failed to fetch {func_name}: {data['error']}"
    if not data:
        return f"No data returned for {func_name}."

    label = func_name.replace("get_", "").replace("_", " ").title()
    lines = [f"### {label}\n"]

    if isinstance(data, list):
        if len(data) == 0:
            lines.append("No items found.")
        else:
            for i, item in enumerate(data[:20], 1):
                if isinstance(item, dict):
                    summary = ", ".join(f"{k}: {v}" for k, v in list(item.items())[:4])
                    lines.append(f"{i}. {summary}")
                else:
                    lines.append(f"{i}. {item}")
            if len(data) > 20:
                lines.append(f"\n... and {len(data) - 20} more")
    elif isinstance(data, dict):
        for key, val in list(data.items())[:15]:
            label_k = key.replace("_", " ").title()
            lines.append(f"- **{label_k}**: {val}")
    else:
        lines.append(str(data))
    return "\n".join(lines)


# Formatter dispatch
DATA_FORMATTERS = {
    "get_devices": _format_devices,
    "get_compliance": _format_compliance,
    "get_audit_results": _format_audit_results,
    "get_rules": _format_rules,
    "get_health_summary": _format_health,
}


def _format_data_response(results: Dict, intent_desc: str) -> str:
    """Format all fetched data into a single markdown response."""
    sections = []
    for func_name, data in results.items():
        formatter = DATA_FORMATTERS.get(func_name, lambda d: _format_generic(func_name, d))
        sections.append(formatter(data))
    return "\n\n".join(sections)


# ============================================================================
# Main chat processor
# ============================================================================

async def process_chat(
    request: ChatRequest,
    db: Session,
    auth_token: str = "",
) -> ChatResponse:
    """Process a natural language query about network state"""

    message = request.message.strip()
    history = ""
    for msg in (request.conversation_history or [])[-3:]:
        history += f"{msg.role}: {msg.content}\n"

    # Step 1: Detect if this is a data query or conversational
    intent = _detect_data_intent(message)

    if intent:
        # DATA QUERY: fetch data and format directly — NO LLM call, instant response
        logger.info(f"Data query detected: {intent['description']} (functions: {intent['functions']})")

        results, queries_executed = await _fetch_platform_data(intent["functions"], auth_token)

        # Format data directly without LLM
        formatted = _format_data_response(results, intent["description"])

        _log_interaction_direct(db, message, formatted, queries_executed)

        return ChatResponse(
            message=formatted,
            data={"raw_results": results} if len(results) <= 3 else None,
            query_executed=", ".join(queries_executed),
            confidence=1.0,
        )

    else:
        # CONVERSATIONAL / TECHNICAL: single LLM call
        logger.info("Conversational/technical query — calling LLM")

        user_prompt = f"{history}User: {message}" if history else message

        llm_request = LLMRequest(
            system_prompt=CONVERSATIONAL_PROMPT,
            user_prompt=user_prompt,
            temperature=0.3,
            max_tokens=1024,
        )

        llm_response = await call_llm(llm_request)

        interaction_id = _log_interaction_llm(db, message, llm_response)

        return ChatResponse(
            message=llm_response.content,
            confidence=0.8,
            interaction_id=interaction_id,
        )


def _log_interaction_direct(db, message, response_text, queries):
    """Log a data-query interaction (no LLM used)."""
    try:
        from shared.db_models import AIInteractionDB
        interaction = AIInteractionDB(
            interaction_type=InteractionType.CHAT_QUERY.value,
            input_prompt=message,
            ai_response={"content": response_text[:2000], "queries": queries},
            model_used="direct_format",
            tokens_used=0,
        )
        db.add(interaction)
        db.commit()
    except Exception as e:
        logger.warning(f"Failed to log interaction: {e}")


def _log_interaction_llm(db, message, llm_response) -> Optional[int]:
    """Log an LLM-based interaction."""
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
