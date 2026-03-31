"""
AI Config Optimization Service
Identifies redundant, unused, and suboptimal configurations.
"""

import json
import os
import httpx
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from models.schemas import LLMRequest, InteractionType
from services.llm_adapter import call_llm
from shared.logger import setup_logger

logger = setup_logger(__name__)

DEVICE_SERVICE_URL = os.getenv("DEVICE_SERVICE_URL", "http://device-service:3001")
BACKUP_SERVICE_URL = os.getenv("BACKUP_SERVICE_URL", "http://backup-service:3003")
RULE_SERVICE_URL = os.getenv("RULE_SERVICE_URL", "http://rule-service:3002")

SYSTEM_PROMPT = """You are a network configuration optimization expert for Cisco IOS-XR and Nokia SR OS.
Analyze device configurations and identify optimization opportunities.

LOOK FOR:
1. UNUSED CONFIG: ACLs never referenced, route-maps not applied, unused interfaces with config
2. REDUNDANT CONFIG: Duplicate entries, overlapping prefix-lists, redundant policies
3. STALE CONFIG: Old peer configs for decommissioned devices, deprecated features
4. SECURITY GAPS: Default credentials, missing encryption, weak algorithms
5. BEST PRACTICE VIOLATIONS: Missing descriptions, no logging, improper buffer sizes
6. SIMPLIFICATION OPPORTUNITIES: Complex policies that could be simplified

For each finding, provide:
- category: unused, redundant, stale, security, best_practice, simplification
- severity: low, medium, high
- description: what was found
- location: where in the config
- recommendation: what to do
- safe_to_remove: boolean (true only if 100% safe)
- estimated_lines_saved: approximate lines that could be cleaned up

Respond with JSON array of findings."""


async def analyze_config(
    device_id: int,
    db: Session,
) -> dict:
    """Analyze a device config for optimization opportunities"""

    # Get device info
    device_info = await _get_device(device_id)
    if not device_info:
        raise ValueError(f"Device {device_id} not found")

    # Get current config
    config = await _get_config(device_id)
    if not config:
        raise ValueError(f"No config backup available for device {device_id}")

    # Get audit results for context
    audit_info = await _get_audit_info(device_id)

    # Analyze config size/complexity metrics
    metrics = _compute_config_metrics(config)

    prompt = f"""Analyze this network device configuration for optimization opportunities:

DEVICE:
- Hostname: {device_info.get('hostname')}
- Vendor: {device_info.get('vendor')}
- Compliance: {device_info.get('compliance')}%

CONFIG METRICS:
{json.dumps(metrics, indent=2)}

CONFIGURATION:
{config[:12000]}

{f'RECENT AUDIT FINDINGS: {json.dumps(audit_info, indent=2, default=str)[:2000]}' if audit_info else ''}

Find ALL optimization opportunities. Return a JSON array of findings.
Each finding must have: category, severity, description, location, recommendation, safe_to_remove, estimated_lines_saved"""

    llm_request = LLMRequest(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=prompt,
        temperature=0.2,
        max_tokens=8192,
    )

    llm_response = await call_llm(llm_request)

    try:
        content = llm_response.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            content = content.rsplit("```", 1)[0]
        findings = json.loads(content.strip())
        if isinstance(findings, dict):
            findings = findings.get("findings", [findings])
    except json.JSONDecodeError:
        findings = []

    # Compute summary
    total_lines_saveable = sum(f.get("estimated_lines_saved", 0) for f in findings)
    by_category = {}
    for f in findings:
        cat = f.get("category", "other")
        by_category[cat] = by_category.get(cat, 0) + 1

    result = {
        "device_id": device_id,
        "device_name": device_info.get("hostname"),
        "vendor": device_info.get("vendor"),
        "config_metrics": metrics,
        "findings": findings,
        "summary": {
            "total_findings": len(findings),
            "by_category": by_category,
            "safe_removals": sum(1 for f in findings if f.get("safe_to_remove")),
            "estimated_lines_saveable": total_lines_saveable,
            "config_reduction_percent": round(total_lines_saveable / max(metrics.get("total_lines", 1), 1) * 100, 1),
        },
    }

    # Log interaction
    try:
        from shared.db_models import AIInteractionDB
        interaction = AIInteractionDB(
            interaction_type="config_optimization",
            input_prompt=f"Config optimization for device {device_id} ({device_info.get('hostname')})",
            ai_response={"findings_count": len(findings), "lines_saveable": total_lines_saveable},
            model_used=llm_response.model,
            tokens_used=llm_response.tokens_used,
        )
        db.add(interaction)
        db.commit()
    except Exception as e:
        logger.warning(f"Failed to log interaction: {e}")

    return result


async def compare_group_configs(
    device_group_id: int,
    db: Session,
) -> dict:
    """Compare configs across a device group to find inconsistencies and redundancies"""

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Get group members
        resp = await client.get(f"{DEVICE_SERVICE_URL}/device-groups/{device_group_id}")
        if resp.status_code != 200:
            raise ValueError(f"Device group {device_group_id} not found")

        group = resp.json()
        members = group.get("members", group.get("devices", []))
        member_ids = []
        for m in members:
            if isinstance(m, dict):
                member_ids.append(m.get("device_id") or m.get("id"))
            elif isinstance(m, int):
                member_ids.append(m)

        if not member_ids:
            return {"error": "No devices in this group"}

        # Get configs for all members
        configs = {}
        for did in member_ids[:20]:  # Limit to 20 devices
            config = await _get_config(did)
            device = await _get_device(did)
            if config and device:
                configs[device.get("hostname", f"device-{did}")] = {
                    "vendor": device.get("vendor"),
                    "lines": len(config.split("\n")),
                    "snippet": config[:2000],
                }

    if len(configs) < 2:
        return {"error": "Need at least 2 devices with configs for comparison"}

    prompt = f"""Compare these device configurations from the same group and find:
1. Inconsistencies (settings that should be the same but differ)
2. Outliers (one device configured very differently)
3. Common redundancies across all devices
4. Missing configurations on some devices

DEVICE CONFIGS:
{json.dumps(configs, indent=2)[:10000]}

Return JSON:
{{
  "inconsistencies": [{{"setting": "...", "devices_differ": ["host1", "host2"], "description": "..."}}],
  "outliers": [{{"device": "host1", "description": "Significantly different..."}}],
  "common_redundancies": ["Redundancy found across all devices"],
  "missing_configs": [{{"device": "host1", "missing": "Config X present on others but not here"}}],
  "recommendation": "Overall group config health assessment"
}}"""

    llm_request = LLMRequest(
        system_prompt="You are a network configuration consistency expert. Compare configs across device groups to find deviations.",
        user_prompt=prompt,
        temperature=0.2,
        max_tokens=4096,
    )

    llm_response = await call_llm(llm_request)

    try:
        content = llm_response.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            content = content.rsplit("```", 1)[0]
        return json.loads(content.strip())
    except json.JSONDecodeError:
        return {"analysis": llm_response.content}


def _compute_config_metrics(config: str) -> dict:
    """Compute basic config complexity metrics"""
    lines = config.split("\n")
    non_empty = [l for l in lines if l.strip()]
    comment_lines = [l for l in non_empty if l.strip().startswith("!") or l.strip().startswith("#")]

    # Count sections
    sections = {}
    current_section = "global"
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith(("!", "#", "end")):
            # Detect section headers (no leading spaces = top-level)
            if not line.startswith((" ", "\t")) and stripped:
                current_section = stripped.split()[0] if stripped.split() else "unknown"
            sections[current_section] = sections.get(current_section, 0) + 1

    # Top sections by line count
    top_sections = sorted(sections.items(), key=lambda x: x[1], reverse=True)[:10]

    return {
        "total_lines": len(lines),
        "non_empty_lines": len(non_empty),
        "comment_lines": len(comment_lines),
        "config_density": round(len(non_empty) / max(len(lines), 1) * 100, 1),
        "top_sections": dict(top_sections),
        "unique_sections": len(sections),
    }


async def _get_device(device_id: int) -> Optional[dict]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{DEVICE_SERVICE_URL}/devices/{device_id}")
            return resp.json() if resp.status_code == 200 else None
    except Exception:
        return None


async def _get_config(device_id: int) -> Optional[str]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{BACKUP_SERVICE_URL}/config-backups/device/{device_id}/history",
                params={"limit": 1},
            )
            if resp.status_code == 200:
                backups = resp.json()
                return backups[0].get("config_data", "") if backups else None
    except Exception:
        return None


async def _get_audit_info(device_id: int) -> Optional[list]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{RULE_SERVICE_URL}/audit/results/{device_id}")
            if resp.status_code == 200:
                results = resp.json()
                if isinstance(results, list) and results:
                    return [f for f in results[0].get("findings", []) if f.get("status") == "fail"][:10]
    except Exception:
        return None
    return None
