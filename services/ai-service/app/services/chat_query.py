"""
Natural Language Network Query Service
Translates user questions into NAP API calls and returns formatted results.
"""

import json
import os
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

SYSTEM_PROMPT = """You are an AI assistant for the Network Audit Platform (NAP). You help network engineers
query network state, compliance data, and device information using natural language.

You have access to these NAP API endpoints that you can call to answer user questions:

AVAILABLE FUNCTIONS:
1. get_devices() - List all devices. Returns: [{id, hostname, vendor, ip, status, compliance, last_audit}]
2. get_device(device_id) - Get specific device details
3. get_audit_results(device_id=null, latest_only=true) - Get audit results. Filter by device_id optionally
4. get_compliance() - Get overall compliance summary: {total_devices, compliant_devices, average_compliance, ...}
5. get_rules(enabled_only=true) - List audit rules
6. get_health_summary() - Get device health summary
7. get_config_changes(device_id=null, limit=20) - Get recent config changes
8. get_drift_summary() - Get configuration drift summary
9. get_device_groups() - List device groups and their members
10. get_backup_summary() - Get config backup summary per device

INSTRUCTIONS:
1. Analyze the user's question to determine which API calls are needed
2. Respond with a JSON object containing:
   - "functions": Array of function calls to make, e.g. [{"name": "get_devices", "args": {}}]
   - "response_template": A template string for formatting the response. Use {results[0]}, {results[1]}, etc. to reference function call results.

If the question is conversational or doesn't need data, respond with:
   - "functions": []
   - "direct_response": "Your direct answer here"

Respond with ONLY valid JSON, no markdown fences."""

# Map function names to actual API calls
FUNCTION_MAP = {
    "get_devices": {"url": f"{DEVICE_SERVICE_URL}/devices/", "method": "GET"},
    "get_device": {"url": f"{DEVICE_SERVICE_URL}/devices/{{device_id}}", "method": "GET"},
    "get_audit_results": {"url": f"{RULE_SERVICE_URL}/audit/results", "method": "GET"},
    "get_compliance": {"url": f"{RULE_SERVICE_URL}/audit/compliance", "method": "GET"},
    "get_rules": {"url": f"{RULE_SERVICE_URL}/rules/", "method": "GET"},
    "get_health_summary": {"url": f"{DEVICE_SERVICE_URL}/health/summary", "method": "GET"},
    "get_config_changes": {"url": f"{BACKUP_SERVICE_URL}/config-backups/device/{{device_id}}/changes", "method": "GET"},
    "get_drift_summary": {"url": f"{BACKUP_SERVICE_URL}/drift-detection/summary", "method": "GET"},
    "get_device_groups": {"url": f"{DEVICE_SERVICE_URL}/device-groups/", "method": "GET"},
    "get_backup_summary": {"url": f"{BACKUP_SERVICE_URL}/config-backups/devices/summary", "method": "GET"},
}


async def process_chat(
    request: ChatRequest,
    db: Session,
) -> ChatResponse:
    """Process a natural language query about network state"""

    # Build conversation context
    messages = ""
    for msg in (request.conversation_history or [])[-5:]:  # Last 5 messages for context
        messages += f"{msg.role}: {msg.content}\n"
    messages += f"user: {request.message}"

    llm_request = LLMRequest(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=messages,
        temperature=0.1,
        max_tokens=2048,
    )

    llm_response = await call_llm(llm_request)

    # Parse LLM plan
    try:
        content = llm_response.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            content = content.rsplit("```", 1)[0]
        plan = json.loads(content.strip())
    except json.JSONDecodeError:
        # If LLM didn't return valid JSON, treat as direct response
        return ChatResponse(
            message=llm_response.content,
            confidence=0.5,
        )

    # Handle direct responses
    if plan.get("direct_response"):
        return ChatResponse(
            message=plan["direct_response"],
            confidence=0.8,
        )

    # Execute the planned function calls
    functions = plan.get("functions", [])
    if not functions:
        return ChatResponse(
            message="I couldn't determine what data to look up. Could you rephrase your question?",
            confidence=0.3,
        )

    results = []
    queries_executed = []
    async with httpx.AsyncClient(timeout=30.0) as client:
        for func in functions:
            func_name = func.get("name")
            func_args = func.get("args", {})

            if func_name not in FUNCTION_MAP:
                results.append({"error": f"Unknown function: {func_name}"})
                continue

            func_config = FUNCTION_MAP[func_name]
            url = func_config["url"]

            # Substitute path parameters
            for key, value in func_args.items():
                url = url.replace(f"{{{key}}}", str(value))

            # Build query params from remaining args
            params = {k: v for k, v in func_args.items() if f"{{{k}}}" not in func_config["url"]}

            try:
                response = await client.request(
                    method=func_config["method"],
                    url=url,
                    params=params if params else None,
                )
                if response.status_code == 200:
                    results.append(response.json())
                else:
                    results.append({"error": f"API returned {response.status_code}"})
                queries_executed.append(f"{func_name}({func_args})")
            except Exception as e:
                logger.error(f"Error calling {func_name}: {e}")
                results.append({"error": str(e)})

    # Now ask LLM to format the results into a human-readable response
    format_prompt = f"""User asked: "{request.message}"

I retrieved the following data from the NAP API:

{json.dumps(results, indent=2, default=str)[:8000]}

Please provide a clear, concise answer to the user's question based on this data.
Use markdown formatting for readability (tables, lists, bold for important values).
If the data doesn't fully answer the question, say so and suggest what additional information might help."""

    format_request = LLMRequest(
        system_prompt="You are a helpful network operations assistant. Format API data into clear, readable responses for network engineers. Be concise but thorough.",
        user_prompt=format_prompt,
        temperature=0.2,
        max_tokens=4096,
    )

    format_response = await call_llm(format_request)

    # Log interaction
    try:
        from shared.db_models import AIInteractionDB
        interaction = AIInteractionDB(
            interaction_type=InteractionType.CHAT_QUERY.value,
            input_prompt=request.message,
            ai_response={"content": format_response.content[:2000], "queries": queries_executed},
            model_used=format_response.model,
            tokens_used=llm_response.tokens_used + format_response.tokens_used,
        )
        db.add(interaction)
        db.commit()
    except Exception as e:
        logger.warning(f"Failed to log interaction: {e}")

    return ChatResponse(
        message=format_response.content,
        data={"raw_results": results} if len(results) <= 3 else None,
        query_executed=", ".join(queries_executed),
        confidence=0.8,
    )
