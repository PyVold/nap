"""
LLM Adapter - Provider-agnostic LLM integration layer.
Supports Anthropic Claude, OpenAI GPT, local models (Ollama),
and any OpenAI-compatible API (vLLM, LocalAI, text-generation-webui, etc.).

Tool-use / function-calling is supported across providers:
- Anthropic: native tool_use blocks
- OpenAI: function calling via tools parameter
- Ollama: tool calling (Ollama 0.4+) or graceful degradation to no-tools
"""

import os
import json
import httpx
from typing import Optional, List
from models.schemas import (
    LLMRequest, LLMResponse, AIProvider, LLMMessage,
    LLMToolDef, LLMToolCall,
)
from shared.logger import setup_logger

logger = setup_logger(__name__)

# Provider configuration from environment
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
LOCAL_LLM_URL = os.getenv("LOCAL_LLM_URL", "http://ollama:11434")
LOCAL_LLM_API_FORMAT = os.getenv("LOCAL_LLM_API_FORMAT", "ollama")  # ollama or openai

# Default models per provider
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
LOCAL_MODEL = os.getenv("LOCAL_MODEL", "llama3")

# Default provider priority
DEFAULT_PROVIDER = os.getenv("AI_PROVIDER", "local")

# Timeouts
CLOUD_TIMEOUT = float(os.getenv("LLM_CLOUD_TIMEOUT", "120"))
LOCAL_TIMEOUT = float(os.getenv("LLM_LOCAL_TIMEOUT", "300"))


def get_available_providers() -> list:
    """Return list of configured providers"""
    providers = []
    if ANTHROPIC_API_KEY:
        providers.append(AIProvider.ANTHROPIC)
    if OPENAI_API_KEY:
        providers.append(AIProvider.OPENAI)
    providers.append(AIProvider.LOCAL)
    return providers


def get_default_provider() -> AIProvider:
    """Get the default provider based on config and available keys"""
    try:
        preferred = AIProvider(DEFAULT_PROVIDER)
        if preferred == AIProvider.ANTHROPIC and ANTHROPIC_API_KEY:
            return AIProvider.ANTHROPIC
        if preferred == AIProvider.OPENAI and OPENAI_API_KEY:
            return AIProvider.OPENAI
        if preferred == AIProvider.LOCAL:
            return AIProvider.LOCAL
    except ValueError:
        pass

    if DEFAULT_PROVIDER == "local":
        return AIProvider.LOCAL
    if ANTHROPIC_API_KEY:
        return AIProvider.ANTHROPIC
    if OPENAI_API_KEY:
        return AIProvider.OPENAI
    return AIProvider.LOCAL


async def check_local_llm_status() -> dict:
    """Check if local LLM is reachable and list available models"""
    result = {"reachable": False, "url": LOCAL_LLM_URL, "api_format": LOCAL_LLM_API_FORMAT, "models": [], "error": None}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            if LOCAL_LLM_API_FORMAT == "ollama":
                resp = await client.get(f"{LOCAL_LLM_URL}/api/tags")
                if resp.status_code == 200:
                    data = resp.json()
                    result["reachable"] = True
                    result["models"] = [m["name"] for m in data.get("models", [])]
            else:
                resp = await client.get(f"{LOCAL_LLM_URL}/v1/models")
                if resp.status_code == 200:
                    data = resp.json()
                    result["reachable"] = True
                    result["models"] = [m["id"] for m in data.get("data", [])]
    except httpx.ConnectError:
        result["error"] = f"Cannot connect to {LOCAL_LLM_URL}"
    except Exception as e:
        result["error"] = str(e)
    return result


async def call_llm(request: LLMRequest) -> LLMResponse:
    """Route LLM call to the appropriate provider"""
    provider = request.provider or get_default_provider()
    logger.info(f"LLM call using provider: {provider.value}, model: {_get_model_for_provider(provider)}, tools: {len(request.tools) if request.tools else 0}")

    if provider == AIProvider.ANTHROPIC:
        return await _call_anthropic(request)
    elif provider == AIProvider.OPENAI:
        return await _call_openai(request)
    elif provider == AIProvider.LOCAL:
        return await _call_local(request)
    else:
        raise ValueError(f"Unknown provider: {provider}")


def _get_model_for_provider(provider: AIProvider) -> str:
    if provider == AIProvider.ANTHROPIC:
        return ANTHROPIC_MODEL
    elif provider == AIProvider.OPENAI:
        return OPENAI_MODEL
    return LOCAL_MODEL


# ============================================================================
# Message Building
# ============================================================================

def _build_messages_anthropic(request: LLMRequest) -> list:
    """Build messages for Anthropic API format.
    Anthropic uses content blocks for tool results."""
    if not request.messages:
        return [{"role": "user", "content": request.user_prompt}]

    messages = []
    for m in request.messages:
        if m.role == "tool":
            # Tool result → Anthropic format
            messages.append({
                "role": "user",
                "content": [{
                    "type": "tool_result",
                    "tool_use_id": m.tool_call_id,
                    "content": m.content if isinstance(m.content, str) else json.dumps(m.content),
                }]
            })
        elif m.role == "assistant" and isinstance(m.content, list):
            # Raw content blocks (tool_use + text) from previous response
            messages.append({"role": "assistant", "content": m.content})
        else:
            messages.append({"role": m.role, "content": m.content})
    return messages


def _build_messages_openai(request: LLMRequest) -> list:
    """Build messages for OpenAI-compatible API format."""
    if not request.messages:
        return [{"role": "user", "content": request.user_prompt}]

    messages = []
    for m in request.messages:
        if m.role == "tool":
            messages.append({
                "role": "tool",
                "tool_call_id": m.tool_call_id,
                "content": m.content if isinstance(m.content, str) else json.dumps(m.content),
            })
        elif m.role == "assistant" and isinstance(m.content, list):
            # Reconstruct OpenAI assistant message with tool_calls
            text_parts = [b.get("text", "") for b in m.content if b.get("type") == "text"]
            tool_calls_raw = [b for b in m.content if b.get("type") == "tool_use"]
            msg = {"role": "assistant", "content": " ".join(text_parts) or None}
            if tool_calls_raw:
                msg["tool_calls"] = [{
                    "id": tc["id"],
                    "type": "function",
                    "function": {"name": tc["name"], "arguments": json.dumps(tc.get("input", {}))},
                } for tc in tool_calls_raw]
            messages.append(msg)
        else:
            messages.append({"role": m.role, "content": m.content})
    return messages


def _build_tools_anthropic(tools: List[LLMToolDef]) -> list:
    """Convert tools to Anthropic format."""
    return [{
        "name": t.name,
        "description": t.description,
        "input_schema": t.input_schema,
    } for t in tools]


def _build_tools_openai(tools: List[LLMToolDef]) -> list:
    """Convert tools to OpenAI function-calling format."""
    return [{
        "type": "function",
        "function": {
            "name": t.name,
            "description": t.description,
            "parameters": t.input_schema,
        },
    } for t in tools]


def _build_tools_ollama(tools: List[LLMToolDef]) -> list:
    """Convert tools to Ollama tool-calling format (same as OpenAI)."""
    return _build_tools_openai(tools)


# ============================================================================
# Provider Implementations
# ============================================================================

async def _call_anthropic(request: LLMRequest) -> LLMResponse:
    """Call Anthropic Claude API with tool-use support"""
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY not configured")

    payload = {
        "model": ANTHROPIC_MODEL,
        "max_tokens": request.max_tokens,
        "temperature": request.temperature,
        "system": request.system_prompt,
        "messages": _build_messages_anthropic(request),
    }
    if request.tools:
        payload["tools"] = _build_tools_anthropic(request.tools)

    async with httpx.AsyncClient(timeout=CLOUD_TIMEOUT) as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

        tokens = data.get("usage", {}).get("input_tokens", 0) + data.get("usage", {}).get("output_tokens", 0)
        content_blocks = data.get("content", [])

        # Extract text and tool_use blocks
        text_parts = []
        tool_calls = []
        for block in content_blocks:
            if block.get("type") == "text":
                text_parts.append(block["text"])
            elif block.get("type") == "tool_use":
                tool_calls.append(LLMToolCall(
                    id=block["id"],
                    name=block["name"],
                    arguments=block.get("input", {}),
                ))

        return LLMResponse(
            content="\n".join(text_parts),
            model=ANTHROPIC_MODEL,
            tokens_used=tokens,
            provider=AIProvider.ANTHROPIC,
            tool_calls=tool_calls if tool_calls else None,
            raw_content=content_blocks if tool_calls else None,
        )


async def _call_openai(request: LLMRequest) -> LLMResponse:
    """Call OpenAI API with function-calling support"""
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not configured")

    payload = {
        "model": OPENAI_MODEL,
        "max_tokens": request.max_tokens,
        "temperature": request.temperature,
        "messages": [
            {"role": "system", "content": request.system_prompt},
            *_build_messages_openai(request),
        ],
    }
    if request.tools:
        payload["tools"] = _build_tools_openai(request.tools)

    async with httpx.AsyncClient(timeout=CLOUD_TIMEOUT) as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

        choice = data["choices"][0]["message"] if data.get("choices") else {}
        content = choice.get("content") or ""
        tokens = data.get("usage", {}).get("total_tokens", 0)

        # Parse tool calls
        tool_calls = None
        raw_content = None
        if choice.get("tool_calls"):
            tool_calls = []
            # Build Anthropic-style raw_content for multi-turn
            raw_blocks = []
            if content:
                raw_blocks.append({"type": "text", "text": content})
            for tc in choice["tool_calls"]:
                func = tc.get("function", {})
                try:
                    args = json.loads(func.get("arguments", "{}"))
                except json.JSONDecodeError:
                    args = {}
                tool_calls.append(LLMToolCall(
                    id=tc["id"],
                    name=func.get("name", ""),
                    arguments=args,
                ))
                raw_blocks.append({
                    "type": "tool_use",
                    "id": tc["id"],
                    "name": func.get("name", ""),
                    "input": args,
                })
            raw_content = raw_blocks

        return LLMResponse(
            content=content,
            model=OPENAI_MODEL,
            tokens_used=tokens,
            provider=AIProvider.OPENAI,
            tool_calls=tool_calls,
            raw_content=raw_content,
        )


async def _call_local(request: LLMRequest) -> LLMResponse:
    """Call local LLM - supports Ollama native API and OpenAI-compatible APIs"""
    if LOCAL_LLM_API_FORMAT == "openai":
        return await _call_local_openai_compat(request)
    return await _call_local_ollama(request)


async def _call_local_ollama(request: LLMRequest) -> LLMResponse:
    """Call local LLM via Ollama native API (/api/chat) with tool support"""
    payload = {
        "model": LOCAL_MODEL,
        "messages": [
            {"role": "system", "content": request.system_prompt},
            *_build_messages_openai(request),  # Ollama uses OpenAI-style messages
        ],
        "stream": False,
        "options": {
            "temperature": request.temperature,
            "num_predict": request.max_tokens,
        },
    }
    if request.tools:
        payload["tools"] = _build_tools_ollama(request.tools)

    async with httpx.AsyncClient(timeout=LOCAL_TIMEOUT) as client:
        try:
            response = await client.post(f"{LOCAL_LLM_URL}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()

            msg = data.get("message", {})
            content = msg.get("content", "")
            tokens = data.get("eval_count", 0) + data.get("prompt_eval_count", 0)

            # Parse Ollama tool calls
            tool_calls = None
            raw_content = None
            ollama_tool_calls = msg.get("tool_calls", [])
            if ollama_tool_calls:
                tool_calls = []
                raw_blocks = []
                if content:
                    raw_blocks.append({"type": "text", "text": content})
                for i, tc in enumerate(ollama_tool_calls):
                    func = tc.get("function", {})
                    tc_id = f"ollama_{i}"
                    tool_calls.append(LLMToolCall(
                        id=tc_id,
                        name=func.get("name", ""),
                        arguments=func.get("arguments", {}),
                    ))
                    raw_blocks.append({
                        "type": "tool_use",
                        "id": tc_id,
                        "name": func.get("name", ""),
                        "input": func.get("arguments", {}),
                    })
                raw_content = raw_blocks

            return LLMResponse(
                content=content,
                model=LOCAL_MODEL,
                tokens_used=tokens,
                provider=AIProvider.LOCAL,
                tool_calls=tool_calls,
                raw_content=raw_content,
            )
        except httpx.ConnectError:
            raise ValueError(
                f"Cannot connect to local LLM at {LOCAL_LLM_URL}. "
                "Ensure Ollama is running. Start with: "
                "docker compose --profile local-llm up -d ollama && "
                f"docker exec nap-ollama-1 ollama pull {LOCAL_MODEL}"
            )


async def _call_local_openai_compat(request: LLMRequest) -> LLMResponse:
    """Call local LLM via OpenAI-compatible API (/v1/chat/completions)."""
    payload = {
        "model": LOCAL_MODEL,
        "max_tokens": request.max_tokens,
        "temperature": request.temperature,
        "messages": [
            {"role": "system", "content": request.system_prompt},
            *_build_messages_openai(request),
        ],
    }
    if request.tools:
        payload["tools"] = _build_tools_openai(request.tools)

    async with httpx.AsyncClient(timeout=LOCAL_TIMEOUT) as client:
        try:
            response = await client.post(
                f"{LOCAL_LLM_URL}/v1/chat/completions",
                headers={"Content-Type": "application/json"},
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

            choice = data["choices"][0]["message"] if data.get("choices") else {}
            content = choice.get("content") or ""
            tokens = data.get("usage", {}).get("total_tokens", 0)

            # Parse tool calls (same as OpenAI format)
            tool_calls = None
            raw_content = None
            if choice.get("tool_calls"):
                tool_calls = []
                raw_blocks = []
                if content:
                    raw_blocks.append({"type": "text", "text": content})
                for tc in choice["tool_calls"]:
                    func = tc.get("function", {})
                    try:
                        args = json.loads(func.get("arguments", "{}"))
                    except json.JSONDecodeError:
                        args = {}
                    tool_calls.append(LLMToolCall(
                        id=tc["id"],
                        name=func.get("name", ""),
                        arguments=args,
                    ))
                    raw_blocks.append({
                        "type": "tool_use",
                        "id": tc["id"],
                        "name": func.get("name", ""),
                        "input": args,
                    })
                raw_content = raw_blocks

            return LLMResponse(
                content=content,
                model=LOCAL_MODEL,
                tokens_used=tokens,
                provider=AIProvider.LOCAL,
                tool_calls=tool_calls,
                raw_content=raw_content,
            )
        except httpx.ConnectError:
            raise ValueError(
                f"Cannot connect to local LLM at {LOCAL_LLM_URL}. "
                "Ensure your OpenAI-compatible LLM server is running."
            )
