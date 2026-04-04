"""
Natural Language Network Query Service
Translates user questions into NAP API calls and returns formatted results.

Optimized for local LLM performance:
- Keyword-based routing detects data queries vs conversational queries
- Data queries use a single LLM call (fetches data first, then asks LLM to summarize)
- Conversational/technical queries go directly to LLM with NAP context
- No JSON parsing required from the LLM for routing
"""

import json
import os
import re
import httpx
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from models.schemas import ChatRequest, ChatResponse, ChatMessage, LLMRequest, InteractionType
from services.llm_adapter import call_llm
from shared.logger import setup_logger

logger = setup_logger(__name__)

# Internal service URLs for direct querying
DEVICE_SERVICE_URL = os.getenv("DEVICE_SERVICE_URL", "http://device-service:3001")
RULE_SERVICE_URL = os.getenv("RULE_SERVICE_URL", "http://rule-service:3002")
BACKUP_SERVICE_URL = os.getenv("BACKUP_SERVICE_URL", "http://backup-service:3003")
ADMIN_SERVICE_URL = os.getenv("ADMIN_SERVICE_URL", "http://admin-service:3005")
ANALYTICS_SERVICE_URL = os.getenv("ANALYTICS_SERVICE_URL", "http://analytics-service:3006")

# Keyword-based intent detection — avoids burning an LLM call just to classify the query
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

# System prompt for the single LLM call
CONVERSATIONAL_PROMPT = """You are the AI assistant for the Network Audit Platform (NAP), a network compliance and audit tool.

You help network engineers with:
- Network compliance, auditing, and troubleshooting questions
- Explaining networking concepts (BGP, OSPF, MPLS, VPN, ACL, NTP, SNMP, etc.)
- Cisco IOS-XR, Cisco IOS-XE, Nokia SR OS, Juniper JunOS, and Arista EOS configuration guidance
- Best practices for network security, routing, and operations
- Interpreting audit results and compliance data
- Remediation advice for configuration issues

Be concise, technical, and helpful. Use markdown formatting (bold, lists, code blocks) for readability.
When discussing vendor-specific configs, show example CLI commands in code blocks."""

DATA_SUMMARY_PROMPT = """You are the AI assistant for the Network Audit Platform (NAP).
The user asked a question and I've fetched relevant data from the platform.

Summarize the data clearly and concisely to answer the user's question.
Use markdown formatting: tables for tabular data, bold for key metrics, lists for items.
If the data is empty or shows errors, say so clearly and suggest what the user can do."""


def _detect_data_intent(message: str) -> Optional[Dict]:
    """Detect if the user's message requires fetching platform data.
    Returns matched intent or None for conversational queries."""
    msg_lower = message.lower()

    best_match = None
    best_score = 0

    for pattern in DATA_INTENT_PATTERNS:
        score = sum(1 for kw in pattern["keywords"] if kw in msg_lower)
        if score > best_score:
            best_score = score
            best_match = pattern

    # Require at least one keyword match
    if best_score > 0:
        return best_match
    return None


async def _fetch_platform_data(func_names: List[str], auth_token: str = "") -> tuple:
    """Fetch data from platform APIs. Returns (results_dict, queries_executed)."""
    results = {}
    queries_executed = []
    headers = {}
    if auth_token:
        headers["Authorization"] = auth_token

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


async def process_chat(
    request: ChatRequest,
    db: Session,
    auth_token: str = "",
) -> ChatResponse:
    """Process a natural language query about network state"""

    message = request.message.strip()

    # Build conversation history context
    history = ""
    for msg in (request.conversation_history or [])[-3:]:
        history += f"{msg.role}: {msg.content}\n"

    # Step 1: Detect if this is a data query or conversational
    intent = _detect_data_intent(message)

    if intent:
        # DATA QUERY: fetch data first, then one LLM call to summarize
        logger.info(f"Data query detected: {intent['description']} (functions: {intent['functions']})")

        results, queries_executed = await _fetch_platform_data(intent["functions"], auth_token)

        # Truncate data to fit in context
        data_str = json.dumps(results, indent=2, default=str)
        if len(data_str) > 6000:
            data_str = data_str[:6000] + "\n... (truncated)"

        user_prompt = f"""{history}User question: {message}

Platform data ({intent['description']}):
{data_str}

Answer the question based on this data."""

        llm_request = LLMRequest(
            system_prompt=DATA_SUMMARY_PROMPT,
            user_prompt=user_prompt,
            temperature=0.2,
            max_tokens=2048,
        )

        llm_response = await call_llm(llm_request)

        interaction_id = _log_interaction(
            db, message, llm_response, queries_executed
        )

        return ChatResponse(
            message=llm_response.content,
            data={"raw_results": results} if len(results) <= 3 else None,
            query_executed=", ".join(queries_executed),
            confidence=0.8,
            interaction_id=interaction_id,
        )

    else:
        # CONVERSATIONAL / TECHNICAL QUERY: single LLM call, no data fetch
        logger.info("Conversational/technical query detected")

        user_prompt = f"{history}User: {message}" if history else message

        llm_request = LLMRequest(
            system_prompt=CONVERSATIONAL_PROMPT,
            user_prompt=user_prompt,
            temperature=0.3,
            max_tokens=2048,
        )

        llm_response = await call_llm(llm_request)

        interaction_id = _log_interaction(db, message, llm_response, [])

        return ChatResponse(
            message=llm_response.content,
            confidence=0.8,
            interaction_id=interaction_id,
        )


def _log_interaction(
    db: Session,
    message: str,
    llm_response,
    queries_executed: List[str],
) -> Optional[int]:
    """Log AI interaction for feedback loop."""
    try:
        from shared.db_models import AIInteractionDB
        interaction = AIInteractionDB(
            interaction_type=InteractionType.CHAT_QUERY.value,
            input_prompt=message,
            ai_response={
                "content": llm_response.content[:2000],
                "queries": queries_executed,
            },
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
