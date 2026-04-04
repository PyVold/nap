"""
Natural Language Network Query Service

Single LLM call with platform data as context.
The LLM decides whether to use the data, answer technically,
or respond conversationally — all in one pass.

Platform data is pre-fetched in parallel (fast) and provided as
context so the LLM can reference it when relevant.
"""

import json
import os
import asyncio
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

# Quick-fetch endpoints for platform context (all GET, all fast)
CONTEXT_ENDPOINTS = {
    "devices": f"{DEVICE_SERVICE_URL}/devices/",
    "compliance": f"{RULE_SERVICE_URL}/audit/compliance",
    "health": f"{DEVICE_SERVICE_URL}/health/summary",
    "rules": f"{RULE_SERVICE_URL}/rules/",
    "device_groups": f"{DEVICE_SERVICE_URL}/device-groups/",
}

SYSTEM_PROMPT = """You are the AI assistant for the Network Audit Platform (NAP), an enterprise network compliance and audit tool.

You are a senior network engineer assistant. You handle all types of queries naturally:

- **Data questions** ("show me devices", "what's the compliance score?") — Use the PLATFORM DATA below to answer. Present data clearly with markdown tables, lists, and bold metrics.
- **Technical questions** ("how do I configure BGP on IOS-XR?", "explain MPLS LDP") — Answer with detailed technical guidance, CLI examples in code blocks, and best practices.
- **Troubleshooting** ("device is unreachable", "audit failing") — Provide step-by-step troubleshooting guidance.
- **Conversational** ("hello", "what can you do?", "thanks") — Respond naturally and briefly.

Supported vendors: Cisco IOS-XR, Cisco IOS-XE, Nokia SR OS, Juniper JunOS, Arista EOS.

Guidelines:
- Be concise but thorough
- Use markdown formatting: **bold**, `code`, tables, lists
- Show CLI examples in ```code blocks``` with the vendor name
- If platform data is empty or has errors, say so and suggest next steps
- If the question is unrelated to networking, politely redirect"""


async def _fetch_platform_context(auth_token: str = "") -> str:
    """Fetch a compact summary of platform state in parallel.
    This runs fast (~100-500ms) and gives the LLM real data to work with."""
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

    # Fetch all endpoints in parallel
    tasks = [fetch_one(name, url) for name, url in CONTEXT_ENDPOINTS.items()]
    results = await asyncio.gather(*tasks)

    for name, data in results:
        if data is None:
            continue

        if name == "devices":
            devices = data if isinstance(data, list) else data.get("items", data.get("devices", []))
            if devices:
                summary = []
                for d in devices[:30]:
                    summary.append(
                        f"  - {d.get('hostname','?')} | {d.get('vendor','?')} | {d.get('ip','?')} | "
                        f"status:{d.get('status','?')} | compliance:{d.get('compliance','?')}%"
                    )
                context_parts.append(f"Devices ({len(devices)} total):\n" + "\n".join(summary))

        elif name == "compliance":
            if isinstance(data, dict) and data:
                context_parts.append(
                    f"Compliance: total_devices={data.get('total_devices',0)}, "
                    f"compliant={data.get('compliant_devices',0)}, "
                    f"average_score={data.get('average_compliance',0)}%"
                )

        elif name == "health":
            if isinstance(data, dict) and data:
                parts = [f"{k}={v}" for k, v in data.items()]
                context_parts.append(f"Health: {', '.join(parts)}")

        elif name == "rules":
            rules = data if isinstance(data, list) else data.get("items", data.get("rules", []))
            if rules:
                context_parts.append(
                    f"Audit Rules ({len(rules)} total): "
                    + ", ".join(r.get("name", "?") for r in rules[:15])
                )

        elif name == "device_groups":
            groups = data if isinstance(data, list) else data.get("items", data.get("groups", []))
            if groups:
                context_parts.append(
                    f"Device Groups ({len(groups)}): "
                    + ", ".join(g.get("name", "?") for g in groups[:10])
                )

    if not context_parts:
        return "Platform data: No devices or data available yet. The platform appears empty."

    return "PLATFORM DATA:\n" + "\n".join(context_parts)


async def process_chat(
    request: ChatRequest,
    db: Session,
    auth_token: str = "",
) -> ChatResponse:
    """Process any query with a single LLM call, platform data as context."""

    message = request.message.strip()

    # Build conversation history
    history = ""
    for msg in (request.conversation_history or [])[-3:]:
        history += f"{msg.role}: {msg.content}\n"

    # Pre-fetch platform data in parallel (fast, ~100-500ms)
    logger.info("Fetching platform context...")
    platform_context = await _fetch_platform_context(auth_token)

    # Single LLM call with full context
    user_prompt = f"""{platform_context}

{history}User: {message}"""

    llm_request = LLMRequest(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        temperature=0.3,
        max_tokens=1024,
    )

    logger.info(f"Calling LLM for: {message[:80]}")
    llm_response = await call_llm(llm_request)

    # Log interaction
    interaction_id = _log_interaction(db, message, llm_response)

    return ChatResponse(
        message=llm_response.content,
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
