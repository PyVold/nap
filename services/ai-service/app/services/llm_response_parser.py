"""
LLM Response Parser - Robust JSON extraction from LLM output.

Local/small models often return JSON with trailing text, markdown fences,
or minor formatting issues. This module handles all of those cases.
"""

import json
import re
from typing import Any


def extract_json(text: str) -> dict:
    """Extract a JSON object from LLM response text.

    Handles:
    - Clean JSON
    - JSON wrapped in ```json ... ``` markdown fences
    - JSON with leading/trailing prose text
    - Nested braces

    Raises ValueError if no valid JSON object is found.
    """
    content = text.strip()

    # Strip markdown code fences
    if content.startswith("```"):
        # Remove opening fence (with optional language tag)
        content = content.split("\n", 1)[1] if "\n" in content else content[3:]
        # Remove closing fence
        if "```" in content:
            content = content.rsplit("```", 1)[0]
        content = content.strip()

    # Try direct parse first (fast path)
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # Find the first { and last } to extract the outermost JSON object
    first_brace = content.find("{")
    last_brace = content.rfind("}")
    if first_brace != -1 and last_brace > first_brace:
        candidate = content[first_brace:last_brace + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    # Try to find a JSON array if no object found
    first_bracket = content.find("[")
    last_bracket = content.rfind("]")
    if first_bracket != -1 and last_bracket > first_bracket:
        candidate = content[first_bracket:last_bracket + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    raise ValueError("No valid JSON found in LLM response")


def safe_extract_json(text: str, fallback: dict = None) -> dict:
    """Extract JSON from LLM response, returning fallback on failure.

    Use this when you want graceful degradation instead of exceptions.
    """
    try:
        return extract_json(text)
    except (ValueError, json.JSONDecodeError):
        return fallback if fallback is not None else {}
