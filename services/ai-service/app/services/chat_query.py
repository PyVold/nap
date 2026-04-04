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

# Max messages to send to LLM (recent ones). Older messages get summarized.
MAX_HISTORY_MESSAGES = 10
# When total messages exceed this, trigger summarization of older ones
SUMMARIZE_THRESHOLD = 20

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
- If the question is unrelated to networking, politely redirect
- You have memory of our previous conversations in this session — use it naturally"""


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
    """Process any query with a single LLM call, platform data as context, persistent memory."""

    message = request.message.strip()

    # --- Session management ---
    session_obj = None
    history_for_llm = ""

    if user_id:
        if request.session_id:
            # Load existing session
            session_obj, stored_messages, summary = _load_session(db, request.session_id, user_id)
            if session_obj:
                # Build history from summary + recent messages
                if summary:
                    history_for_llm += f"[Previous conversation summary: {summary}]\n\n"
                for msg in stored_messages[-MAX_HISTORY_MESSAGES:]:
                    history_for_llm += f"{msg['role']}: {msg['content']}\n"
        else:
            # Create new session
            session_obj = _create_session(db, user_id, message)

    # Fallback: use conversation_history from request (for clients that don't use sessions yet)
    if not history_for_llm and request.conversation_history:
        for msg in (request.conversation_history or [])[-3:]:
            history_for_llm += f"{msg.role}: {msg.content}\n"

    # Pre-fetch platform data in parallel (fast, ~100-500ms)
    logger.info("Fetching platform context...")
    platform_context = await _fetch_platform_context(auth_token)

    # Single LLM call with full context
    user_prompt = f"""{platform_context}

{history_for_llm}User: {message}"""

    llm_request = LLMRequest(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        temperature=0.3,
        max_tokens=1024,
    )

    logger.info(f"Calling LLM for: {message[:80]}")
    llm_response = await call_llm(llm_request)

    # Save to session
    if session_obj:
        _save_messages(db, session_obj, message, llm_response.content)
        # Summarize old messages if conversation is getting long
        await _maybe_summarize(db, session_obj, call_llm)

    # Log interaction
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
