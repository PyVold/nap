"""
Adaptive Monitoring Service (MCP Sampling)
AI-driven monitoring that dynamically adjusts check frequency based on conditions.
"""

import json
import os
import httpx
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from models.schemas import LLMRequest
from services.llm_adapter import call_llm
from shared.logger import setup_logger

logger = setup_logger(__name__)

DEVICE_SERVICE_URL = os.getenv("DEVICE_SERVICE_URL", "http://device-service:3001")
RULE_SERVICE_URL = os.getenv("RULE_SERVICE_URL", "http://rule-service:3002")
BACKUP_SERVICE_URL = os.getenv("BACKUP_SERVICE_URL", "http://backup-service:3003")

# Default monitoring intervals (minutes)
DEFAULT_INTERVALS = {
    "health_check": 5,
    "config_backup": 360,
    "compliance_audit": 1440,  # 24 hours
}

# Adaptive thresholds
ESCALATION_TRIGGERS = {
    "compliance_drop": 10.0,       # Compliance dropped by >10%
    "health_failures": 2,          # Consecutive health failures
    "drift_events": 3,             # Drift events in 1 hour
    "anomaly_score": 0.7,          # High anomaly score
}


async def evaluate_and_adapt(db: Session) -> dict:
    """Evaluate current network state and adapt monitoring intervals"""

    # Gather current state
    state = await _gather_network_state()

    # Evaluate conditions
    adaptations = []

    # Check for compliance drops
    compliance_changes = _check_compliance_changes(state)
    for change in compliance_changes:
        if change["drop"] >= ESCALATION_TRIGGERS["compliance_drop"]:
            adaptations.append({
                "trigger": "compliance_drop",
                "device_id": change["device_id"],
                "device_name": change.get("hostname", "Unknown"),
                "detail": f"Compliance dropped {change['drop']:.1f}% to {change['current']:.1f}%",
                "action": "increase_audit_frequency",
                "new_interval_minutes": 60,  # Audit every hour instead of daily
                "severity": "high",
            })

    # Check for health failures
    health_issues = _check_health_issues(state)
    for issue in health_issues:
        adaptations.append({
            "trigger": "health_degradation",
            "device_id": issue["device_id"],
            "device_name": issue.get("hostname", "Unknown"),
            "detail": issue["detail"],
            "action": "increase_health_check_frequency",
            "new_interval_minutes": 1,  # Check every minute
            "severity": issue.get("severity", "medium"),
        })

    # Check for drift patterns
    drift_issues = _check_drift_patterns(state)
    for issue in drift_issues:
        adaptations.append({
            "trigger": "config_drift_spike",
            "device_id": issue.get("device_id"),
            "device_name": issue.get("hostname", "Unknown"),
            "detail": issue["detail"],
            "action": "increase_backup_frequency",
            "new_interval_minutes": 30,  # Backup every 30 min
            "severity": "high",
        })

    # If there are adaptations, use AI to assess and prioritize
    ai_assessment = None
    if adaptations:
        ai_assessment = await _ai_assess_adaptations(adaptations, state)

    # Save adaptive monitoring decisions
    try:
        from shared.db_models import AIInteractionDB
        interaction = AIInteractionDB(
            interaction_type="adaptive_monitoring",
            input_prompt="Periodic adaptive monitoring evaluation",
            ai_response={
                "adaptations_count": len(adaptations),
                "triggers": list(set(a["trigger"] for a in adaptations)),
                "ai_assessment_available": ai_assessment is not None,
            },
            model_used="adaptive_monitor",
            tokens_used=0,
        )
        db.add(interaction)
        db.commit()
    except Exception as e:
        logger.warning(f"Failed to log: {e}")

    return {
        "evaluated_at": datetime.utcnow().isoformat(),
        "adaptations": adaptations,
        "ai_assessment": ai_assessment,
        "current_state_summary": {
            "devices_monitored": state.get("device_count", 0),
            "health_issues": len(health_issues),
            "compliance_drops": len(compliance_changes),
            "drift_spikes": len(drift_issues),
        },
        "default_intervals": DEFAULT_INTERVALS,
    }


async def get_monitoring_recommendations(db: Session) -> dict:
    """Get AI recommendations for monitoring configuration"""

    state = await _gather_network_state()

    prompt = f"""Based on this network state, recommend optimal monitoring intervals and thresholds:

NETWORK STATE:
- Total devices: {state.get('device_count', 0)}
- Devices with health issues: {len(_check_health_issues(state))}
- Recent compliance changes: {len(_check_compliance_changes(state))}
- Overall compliance: {state.get('compliance', {}).get('average_compliance', 'N/A')}%
- Recent drift events: {state.get('drift_count', 0)}

CURRENT INTERVALS:
{json.dumps(DEFAULT_INTERVALS, indent=2)}

ESCALATION THRESHOLDS:
{json.dumps(ESCALATION_TRIGGERS, indent=2)}

Recommend:
1. Optimal health check interval per device category
2. Optimal audit frequency
3. Config backup frequency
4. Alert thresholds that minimize false positives
5. Devices that need special attention

Return JSON:
{{
  "recommendations": [
    {{
      "category": "health_checks",
      "current_interval": 5,
      "recommended_interval": 3,
      "reason": "Multiple devices showing intermittent connectivity",
      "applies_to": "all" or ["specific-devices"]
    }}
  ],
  "attention_devices": [{{"hostname": "...", "reason": "..."}}],
  "overall_assessment": "Network monitoring health assessment"
}}"""

    llm_request = LLMRequest(
        system_prompt="You are a network monitoring optimization expert. Recommend monitoring intervals that balance coverage with resource usage.",
        user_prompt=prompt,
        temperature=0.2,
        max_tokens=2048,
    )

    response = await call_llm(llm_request)

    try:
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            content = content.rsplit("```", 1)[0]
        return json.loads(content.strip())
    except json.JSONDecodeError:
        return {"overall_assessment": response.content}


async def create_self_healing_plan(
    trigger_event: dict,
    db: Session,
) -> dict:
    """Create a self-healing workflow plan (requires human approval)"""

    prompt = f"""A monitoring trigger has fired. Create a self-healing workflow plan.

TRIGGER EVENT:
{json.dumps(trigger_event, indent=2, default=str)}

Create a step-by-step self-healing plan that:
1. Diagnoses the root cause
2. Proposes corrective actions
3. Includes verification steps
4. Has rollback procedures

IMPORTANT: This plan REQUIRES HUMAN APPROVAL before execution.

Return JSON:
{{
  "diagnosis": "What likely caused this",
  "severity": "low|medium|high|critical",
  "auto_healable": true,
  "steps": [
    {{
      "step": 1,
      "action": "Description of action",
      "type": "diagnostic|corrective|verification|rollback",
      "command": "CLI command if applicable",
      "requires_approval": true,
      "risk": "low|medium|high"
    }}
  ],
  "estimated_recovery_minutes": 15,
  "rollback_plan": "How to undo all changes"
}}"""

    llm_request = LLMRequest(
        system_prompt="You are a network self-healing automation expert. Create safe, approval-gated recovery plans.",
        user_prompt=prompt,
        temperature=0.2,
        max_tokens=4096,
    )

    response = await call_llm(llm_request)

    try:
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            content = content.rsplit("```", 1)[0]
        plan = json.loads(content.strip())
    except json.JSONDecodeError:
        plan = {"diagnosis": response.content, "steps": [], "auto_healable": False}

    # Save as draft requiring approval
    try:
        from shared.db_models import AIRemediationDraftDB
        draft = AIRemediationDraftDB(
            device_id=trigger_event.get("device_id", 0),
            generated_plan=plan,
            confidence_score=0.6,
            status="pending_approval",
        )
        db.add(draft)
        db.commit()
        db.refresh(draft)
        plan["draft_id"] = draft.id
    except Exception as e:
        logger.warning(f"Failed to save self-healing draft: {e}")

    plan["requires_human_approval"] = True
    return plan


# ============================================================================
# Internal helpers
# ============================================================================

async def _gather_network_state() -> dict:
    """Gather current network state for evaluation"""
    state = {}
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.get(f"{DEVICE_SERVICE_URL}/devices/")
            if resp.status_code == 200:
                devices = resp.json()
                state["devices"] = devices
                state["device_count"] = len(devices)
        except Exception:
            state["devices"] = []

        try:
            resp = await client.get(f"{RULE_SERVICE_URL}/audit/compliance")
            if resp.status_code == 200:
                state["compliance"] = resp.json()
        except Exception:
            pass

        try:
            resp = await client.get(f"{DEVICE_SERVICE_URL}/health/summary")
            if resp.status_code == 200:
                state["health"] = resp.json()
        except Exception:
            pass

        try:
            resp = await client.get(f"{BACKUP_SERVICE_URL}/drift-detection/summary")
            if resp.status_code == 200:
                drift = resp.json()
                state["drift"] = drift
                state["drift_count"] = drift.get("total_events", 0) if isinstance(drift, dict) else 0
        except Exception:
            pass

    return state


def _check_compliance_changes(state: dict) -> list:
    """Check for significant compliance drops"""
    changes = []
    devices = state.get("devices", [])
    for device in devices:
        compliance = device.get("compliance")
        if compliance is not None and compliance < 80:
            changes.append({
                "device_id": device.get("id"),
                "hostname": device.get("hostname"),
                "current": compliance,
                "drop": 100 - compliance,  # Simplified — ideally compare with previous
            })
    return changes


def _check_health_issues(state: dict) -> list:
    """Check for health issues"""
    issues = []
    health = state.get("health", {})

    if isinstance(health, dict):
        unhealthy = health.get("unhealthy_devices", health.get("degraded", []))
        if isinstance(unhealthy, list):
            for device in unhealthy:
                if isinstance(device, dict):
                    issues.append({
                        "device_id": device.get("device_id") or device.get("id"),
                        "hostname": device.get("hostname"),
                        "detail": f"Health status: {device.get('status', 'unhealthy')}",
                        "severity": "high",
                    })
        elif isinstance(unhealthy, int) and unhealthy > 0:
            issues.append({
                "device_id": None,
                "detail": f"{unhealthy} devices with health issues",
                "severity": "medium",
            })

    devices = state.get("devices", [])
    for device in devices:
        status = device.get("status", "").lower()
        if status in ("offline", "unreachable", "error"):
            issues.append({
                "device_id": device.get("id"),
                "hostname": device.get("hostname"),
                "detail": f"Device status: {status}",
                "severity": "high",
            })

    return issues


def _check_drift_patterns(state: dict) -> list:
    """Check for unusual drift patterns"""
    issues = []
    drift = state.get("drift", {})

    if isinstance(drift, dict):
        total_events = drift.get("total_events", 0)
        if total_events > 10:
            issues.append({
                "detail": f"{total_events} drift events detected — unusually high",
                "severity": "high",
            })

    return issues


async def _ai_assess_adaptations(adaptations: list, state: dict) -> Optional[str]:
    """Use AI to assess and prioritize monitoring adaptations"""
    try:
        prompt = f"""Assess these monitoring adaptations and provide prioritized recommendations:

ADAPTATIONS TRIGGERED:
{json.dumps(adaptations, indent=2, default=str)[:4000]}

NETWORK STATE SUMMARY:
- Devices: {state.get('device_count', 0)}
- Compliance: {state.get('compliance', {}).get('average_compliance', 'N/A')}%

Provide a brief assessment: which adaptations are most critical and why.
Any false positives? Any additional actions recommended?"""

        llm_request = LLMRequest(
            system_prompt="You are a network monitoring intelligence advisor. Be concise.",
            user_prompt=prompt,
            temperature=0.2,
            max_tokens=1024,
        )

        response = await call_llm(llm_request)
        return response.content
    except Exception as e:
        logger.warning(f"AI assessment failed: {e}")
        return None
