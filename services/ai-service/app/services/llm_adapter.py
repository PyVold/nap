"""
LLM Adapter - Provider-agnostic LLM integration layer.
Supports Anthropic Claude, OpenAI GPT, and local models.
"""

import os
import json
import httpx
from typing import Optional
from models.schemas import LLMRequest, LLMResponse, AIProvider
from shared.logger import setup_logger

logger = setup_logger(__name__)

# Provider configuration from environment
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
LOCAL_LLM_URL = os.getenv("LOCAL_LLM_URL", "http://localhost:11434")

# Default models per provider
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
LOCAL_MODEL = os.getenv("LOCAL_MODEL", "llama3")

# Default provider priority
DEFAULT_PROVIDER = os.getenv("AI_PROVIDER", "anthropic")


def get_available_providers() -> list:
    """Return list of configured providers"""
    providers = []
    if ANTHROPIC_API_KEY:
        providers.append(AIProvider.ANTHROPIC)
    if OPENAI_API_KEY:
        providers.append(AIProvider.OPENAI)
    # Local is always potentially available
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

    # Fallback order
    if ANTHROPIC_API_KEY:
        return AIProvider.ANTHROPIC
    if OPENAI_API_KEY:
        return AIProvider.OPENAI
    return AIProvider.LOCAL


async def call_llm(request: LLMRequest) -> LLMResponse:
    """Route LLM call to the appropriate provider"""
    provider = request.provider or get_default_provider()

    if provider == AIProvider.ANTHROPIC:
        return await _call_anthropic(request)
    elif provider == AIProvider.OPENAI:
        return await _call_openai(request)
    elif provider == AIProvider.LOCAL:
        return await _call_local(request)
    else:
        raise ValueError(f"Unknown provider: {provider}")


async def _call_anthropic(request: LLMRequest) -> LLMResponse:
    """Call Anthropic Claude API"""
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY not configured")

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": ANTHROPIC_MODEL,
                "max_tokens": request.max_tokens,
                "temperature": request.temperature,
                "system": request.system_prompt,
                "messages": [
                    {"role": "user", "content": request.user_prompt}
                ],
            },
        )
        response.raise_for_status()
        data = response.json()

        content = data["content"][0]["text"] if data.get("content") else ""
        tokens = data.get("usage", {}).get("input_tokens", 0) + data.get("usage", {}).get("output_tokens", 0)

        return LLMResponse(
            content=content,
            model=ANTHROPIC_MODEL,
            tokens_used=tokens,
            provider=AIProvider.ANTHROPIC,
        )


async def _call_openai(request: LLMRequest) -> LLMResponse:
    """Call OpenAI API"""
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not configured")

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": OPENAI_MODEL,
                "max_tokens": request.max_tokens,
                "temperature": request.temperature,
                "messages": [
                    {"role": "system", "content": request.system_prompt},
                    {"role": "user", "content": request.user_prompt},
                ],
            },
        )
        response.raise_for_status()
        data = response.json()

        content = data["choices"][0]["message"]["content"] if data.get("choices") else ""
        tokens = data.get("usage", {}).get("total_tokens", 0)

        return LLMResponse(
            content=content,
            model=OPENAI_MODEL,
            tokens_used=tokens,
            provider=AIProvider.OPENAI,
        )


async def _call_local(request: LLMRequest) -> LLMResponse:
    """Call local LLM (Ollama-compatible API)"""
    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            response = await client.post(
                f"{LOCAL_LLM_URL}/api/chat",
                json={
                    "model": LOCAL_MODEL,
                    "messages": [
                        {"role": "system", "content": request.system_prompt},
                        {"role": "user", "content": request.user_prompt},
                    ],
                    "stream": False,
                    "options": {
                        "temperature": request.temperature,
                        "num_predict": request.max_tokens,
                    },
                },
            )
            response.raise_for_status()
            data = response.json()

            content = data.get("message", {}).get("content", "")
            tokens = data.get("eval_count", 0) + data.get("prompt_eval_count", 0)

            return LLMResponse(
                content=content,
                model=LOCAL_MODEL,
                tokens_used=tokens,
                provider=AIProvider.LOCAL,
            )
        except httpx.ConnectError:
            raise ValueError(f"Cannot connect to local LLM at {LOCAL_LLM_URL}. Ensure Ollama or compatible server is running.")
