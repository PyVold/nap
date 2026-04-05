"""
Natural Language Network Query Service — Agentic MCP Tool-Use

The AI agent has access to MCP tools (get devices, audit results, configs,
drift, health, hardware, etc.) and decides which tools to call based on the
user's question.

Flow:
1. User sends a message
2. LLM sees the tool definitions + conversation history
3. LLM either responds directly (conversational/technical) or calls tools
4. If tools are called → execute them via mcp_server → feed results back
5. Repeat until LLM gives a final text response (max 5 rounds)
"""

import json
import os
import httpx
from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from models.schemas import (
    ChatRequest, ChatResponse, LLMRequest, LLMMessage,
    LLMToolDef, InteractionType,
)
from services.llm_adapter import call_llm
from services.mcp_server import MCP_TOOLS, execute_tool
from shared.logger import setup_logger

DEVICE_SERVICE_URL = os.getenv("DEVICE_SERVICE_URL", "http://device-service:3001")
RULE_SERVICE_URL = os.getenv("RULE_SERVICE_URL", "http://rule-service:3002")

logger = setup_logger(__name__)

MAX_TOOL_ROUNDS = 5
MAX_HISTORY_MESSAGES = 10
SUMMARIZE_THRESHOLD = 20

SYSTEM_PROMPT = """You are the AI assistant for the Network Audit Platform (NAP), a senior network engineer assistant.

You have access to tools that let you query live platform data and the knowledge base. **Always use the appropriate tool** when the user's question can be answered with platform data or knowledge base content. Do NOT guess or make up data — use tools to get real information.

Tool usage guide:
- Devices, device status, compliance scores → nap_get_devices or nap_get_compliance_score
- Specific device details (software version, ASN, interfaces) → nap_get_device_detail
- Audit results, failed checks → nap_get_audit_results
- Config backups, config changes, diffs → nap_get_device_config, nap_compare_configs, nap_get_config_changes
- Backup history → nap_get_backup_history
- Health status → nap_get_health_status
- Hardware inventory → nap_get_hardware_inventory
- Audit rules → nap_search_rules
- Configuration drift → nap_get_drift_summary
- Running audits → nap_run_audit (inform user this was triggered)
- **Any technical question, best practice, how-to, troubleshooting, vendor documentation, configuration guidance** → nap_query_knowledge_base (ALWAYS search this first for technical/networking questions)

IMPORTANT: For ANY question about networking concepts, protocols (BGP, OSPF, MPLS, NTP, ACL, etc.), best practices, troubleshooting, or vendor-specific configurations — ALWAYS call nap_query_knowledge_base FIRST to check if the knowledge base has relevant information. Combine KB results with your own knowledge for the best answer.

Supported vendors: Cisco IOS-XR, Cisco IOS-XE, Nokia SR OS, Juniper JunOS, Arista EOS.

Guidelines:
- Only respond to the user's latest message
- Use markdown: **bold**, `code`, tables, lists
- CLI examples in ```code blocks``` with vendor name
- When using tool results, present data clearly — don't dump raw JSON
- You remember our conversation history — use it naturally"""


def _get_tool_definitions() -> List[LLMToolDef]:
    """Convert MCP_TOOLS to LLMToolDef for the LLM adapter."""
    return [
        LLMToolDef(
            name=tool["name"],
            description=tool["description"],
            input_schema=tool.get("inputSchema", {"type": "object", "properties": {}}),
        )
        for tool in MCP_TOOLS
    ]


# ============================================================================
# Session Management
# ============================================================================

def _load_session(db: Session, session_id: int, user_id: int):
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
    from shared.db_models import ChatSessionDB
    title = first_message[:50].strip()
    if len(first_message) > 50:
        title += "..."
    session = ChatSessionDB(user_id=user_id, title=title, messages=[])
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def _save_messages(db: Session, session, user_msg: str, assistant_msg: str):
    messages = list(session.messages or [])
    now = datetime.utcnow().isoformat()
    messages.append({"role": "user", "content": user_msg, "timestamp": now})
    messages.append({"role": "assistant", "content": assistant_msg, "timestamp": now})
    session.messages = messages
    session.updated_at = datetime.utcnow()
    db.commit()


async def _maybe_summarize(db: Session, session):
    messages = session.messages or []
    if len(messages) < SUMMARIZE_THRESHOLD:
        return

    older = messages[:-MAX_HISTORY_MESSAGES]
    recent = messages[-MAX_HISTORY_MESSAGES:]
    older_text = "\n".join(f"{m['role']}: {m['content']}" for m in older)

    summary_prompt = LLMRequest(
        system_prompt="Summarize this conversation concisely. Keep key facts, decisions, device names, and technical details. Be brief (2-4 sentences).",
        user_prompt=older_text[:3000],
        temperature=0.2,
        max_tokens=256,
    )
    try:
        resp = await call_llm(summary_prompt)
        existing = session.summary or ""
        session.summary = f"{existing}\n{resp.content}" if existing else resp.content
        session.messages = recent
        db.commit()
        logger.info(f"Summarized session {session.id}: {len(older)} old messages condensed")
    except Exception as e:
        logger.warning(f"Failed to summarize session {session.id}: {e}")


# ============================================================================
# Agentic Tool-Call Loop
# ============================================================================

async def _run_agent_loop(
    system_prompt: str,
    messages: List[LLMMessage],
    tools: List[LLMToolDef],
) -> tuple:
    """Run the agentic loop: call LLM → execute tools → repeat.
    Returns (final_text, total_tokens, model, tools_used)
    """
    total_tokens = 0
    tools_used = []
    model = ""

    for round_num in range(MAX_TOOL_ROUNDS):
        request_tools = tools if round_num < MAX_TOOL_ROUNDS - 1 else None

        llm_request = LLMRequest(
            system_prompt=system_prompt,
            messages=messages,
            tools=request_tools,
            temperature=0.3,
            max_tokens=2048,
        )

        logger.info(f"Agent round {round_num + 1}: calling LLM...")
        response = await call_llm(llm_request)
        total_tokens += response.tokens_used
        model = response.model

        if not response.tool_calls:
            logger.info(f"Agent done after {round_num + 1} round(s), {len(tools_used)} tool calls")
            return response.content, total_tokens, model, tools_used

        messages.append(LLMMessage(
            role="assistant",
            content=response.raw_content or response.content,
        ))

        for tc in response.tool_calls:
            logger.info(f"Executing tool: {tc.name}({json.dumps(tc.arguments)[:200]})")
            tools_used.append(tc.name)

            try:
                result = await execute_tool(tc.name, tc.arguments)
                result_str = json.dumps(result, default=str)
                if len(result_str) > 8000:
                    result_str = result_str[:8000] + "... (truncated)"
            except Exception as e:
                logger.error(f"Tool {tc.name} failed: {e}")
                result_str = json.dumps({"error": str(e)})

            messages.append(LLMMessage(
                role="tool",
                content=result_str,
                tool_call_id=tc.id,
                name=tc.name,
            ))

    logger.warning(f"Agent hit max rounds ({MAX_TOOL_ROUNDS})")
    return response.content or "I gathered data but couldn't complete the response. Please try a more specific question.", total_tokens, model, tools_used


# ============================================================================
# Platform Context Enrichment
# ============================================================================

async def _fetch_platform_context() -> str:
    """Fetch a summary of managed devices and compliance to include in system prompt.
    This ensures the AI knows about the platform state even if tool-calling fails."""
    context_parts = []
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            # Fetch devices summary
            try:
                resp = await client.get(f"{DEVICE_SERVICE_URL}/devices/")
                if resp.status_code == 200:
                    devices = resp.json()
                    if devices:
                        device_lines = []
                        for d in devices[:20]:  # Cap at 20
                            meta = d.get("device_metadata") or {}
                            line = f"- ID:{d.get('id')} {d.get('hostname', '?')} ({d.get('vendor', '?')}) IP:{d.get('ip_address', '?')} Status:{d.get('status', '?')}"
                            if d.get('compliance_score') is not None:
                                line += f" Compliance:{d['compliance_score']}%"
                            if meta.get("software_version"):
                                line += f" SW:{meta['software_version']}"
                            if meta.get("bgp_asn"):
                                line += f" ASN:{meta['bgp_asn']}"
                            if meta.get("chassis"):
                                line += f" Chassis:{meta['chassis']}"
                            device_lines.append(line)
                        context_parts.append(f"Managed devices ({len(devices)} total):\n" + "\n".join(device_lines))
            except Exception as e:
                logger.debug(f"Failed to fetch devices for context: {e}")

            # Fetch compliance summary
            try:
                resp = await client.get(f"{RULE_SERVICE_URL}/audit/compliance")
                if resp.status_code == 200:
                    compliance = resp.json()
                    if compliance:
                        context_parts.append(f"Fleet compliance: {json.dumps(compliance, default=str)[:500]}")
            except Exception as e:
                logger.debug(f"Failed to fetch compliance for context: {e}")

    except Exception as e:
        logger.debug(f"Platform context enrichment failed: {e}")

    return "\n\n".join(context_parts) if context_parts else ""


# ============================================================================
# Main Entry Point
# ============================================================================

async def process_chat(
    request: ChatRequest,
    db: Session,
    auth_token: str = "",
    user_id: int = None,
) -> ChatResponse:
    """Process a chat query using the agentic MCP tool-call loop.

    The LLM decides whether to call tools (data queries) or respond
    directly (technical/conversational). Tools are executed via the
    MCP server's execute_tool() function.
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
                for msg in stored_messages[-MAX_HISTORY_MESSAGES:]:
                    history_messages.append(LLMMessage(role=msg["role"], content=msg["content"]))
        else:
            session_obj = _create_session(db, user_id, message)

    if not history_messages and request.conversation_history:
        for msg in (request.conversation_history or [])[-6:]:
            history_messages.append(LLMMessage(role=msg.role, content=msg.content))

    system_prompt = SYSTEM_PROMPT

    # Enrich with live platform context (devices, compliance)
    platform_context = await _fetch_platform_context()
    if platform_context:
        system_prompt += f"\n\n--- CURRENT PLATFORM STATE ---\n{platform_context}\n--- END PLATFORM STATE ---"

    if summary_text:
        system_prompt += f"\n\n[Earlier conversation summary: {summary_text}]"

    messages = list(history_messages)
    messages.append(LLMMessage(role="user", content=message))

    tools = _get_tool_definitions()

    # Run agentic loop
    logger.info(f"Processing chat: {message[:80]} (history: {len(history_messages)} msgs, tools: {len(tools)}, platform_ctx: {len(platform_context)} chars)")
    final_text, total_tokens, model, tools_used = await _run_agent_loop(
        system_prompt, messages, tools
    )

    # Save to session
    if session_obj:
        _save_messages(db, session_obj, message, final_text)
        await _maybe_summarize(db, session_obj)

    interaction_id = _log_interaction(db, message, final_text, model, total_tokens, tools_used)

    return ChatResponse(
        message=final_text,
        session_id=session_obj.id if session_obj else None,
        confidence=0.9 if tools_used else 0.8,
        interaction_id=interaction_id,
        query_executed=", ".join(tools_used) if tools_used else None,
    )


def _log_interaction(db, message, response_text, model, tokens, tools_used) -> Optional[int]:
    try:
        from shared.db_models import AIInteractionDB
        interaction = AIInteractionDB(
            interaction_type=InteractionType.CHAT_QUERY.value,
            input_prompt=message,
            ai_response={"content": response_text[:2000], "tools_used": tools_used},
            model_used=model,
            tokens_used=tokens,
        )
        db.add(interaction)
        db.commit()
        db.refresh(interaction)
        return interaction.id
    except Exception as e:
        logger.warning(f"Failed to log interaction: {e}")
        return None
