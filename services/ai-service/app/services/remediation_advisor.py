"""
Intelligent Remediation Advisor Service
Generates AI-powered remediation plans based on audit findings.
"""

import json
import os
import httpx
from typing import Optional
from sqlalchemy.orm import Session
from models.schemas import (
    RemediationRequest, RemediationResponse, RemediationPlan,
    RemediationStep, LLMRequest, InteractionType,
)
from services.llm_adapter import call_llm
from shared.logger import setup_logger

logger = setup_logger(__name__)

DEVICE_SERVICE_URL = os.getenv("DEVICE_SERVICE_URL", "http://device-service:3001")
RULE_SERVICE_URL = os.getenv("RULE_SERVICE_URL", "http://rule-service:3002")
BACKUP_SERVICE_URL = os.getenv("BACKUP_SERVICE_URL", "http://backup-service:3003")

SYSTEM_PROMPT = """You are an expert network remediation engineer for the Network Audit Platform.
Your job is to generate safe, step-by-step remediation plans for audit failures on network devices.

SUPPORTED VENDORS:
- cisco_xr: Cisco IOS-XR (NETCONF, CLI)
- nokia_sros: Nokia SR OS (pysros, SSH CLI)

CRITICAL SAFETY RULES:
1. NEVER generate commands that could cause a service outage without explicit warnings
2. ALWAYS include rollback commands for each step
3. ALWAYS include verification commands
4. Mark risk level for each step (low, medium, high)
5. Include prerequisites (maintenance window, change approval, etc.)
6. Generate vendor-specific commands based on device type
7. Consider BGP peer impact, IGP adjacency changes, and MPLS LSP effects

Respond with ONLY valid JSON in this format:
{
  "finding_summary": "Brief description of what was found",
  "steps": [
    {
      "step_number": 1,
      "description": "What this step does",
      "command": "actual CLI/NETCONF command",
      "command_type": "cli",
      "risk_level": "low",
      "rollback_command": "command to undo this step",
      "verification": "command to verify the step worked"
    }
  ],
  "risk_assessment": "Overall risk description",
  "estimated_impact": "What services/traffic might be affected",
  "rollback_plan": "Complete rollback procedure",
  "prerequisites": ["List of prerequisites"],
  "warnings": ["Important warnings"]
}"""


async def generate_remediation(
    request: RemediationRequest,
    db: Session,
) -> RemediationResponse:
    """Generate an AI-powered remediation plan"""

    # Gather device context
    device_info = await _get_device_info(request.device_id)
    if not device_info:
        raise ValueError(f"Device {request.device_id} not found")

    # Gather audit finding context
    finding_context = ""
    if request.audit_result_id:
        finding_context = await _get_finding_context(
            request.device_id, request.audit_result_id, request.finding_index
        )

    # Gather recent config for context
    config_context = await _get_recent_config(request.device_id)

    # Build the prompt
    user_prompt = f"""Generate a remediation plan for this audit failure:

DEVICE INFORMATION:
- Hostname: {device_info.get('hostname', 'Unknown')}
- Vendor: {device_info.get('vendor', 'Unknown')}
- IP: {device_info.get('ip', 'Unknown')}
- Current compliance: {device_info.get('compliance', 'Unknown')}%

AUDIT FINDING:
{finding_context or request.description or 'No specific finding provided'}

CURRENT CONFIGURATION CONTEXT (last 2000 chars):
{config_context[:2000] if config_context else 'Not available'}

Generate a safe, step-by-step remediation plan. Return ONLY the JSON object."""

    llm_request = LLMRequest(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        temperature=0.2,
        max_tokens=4096,
    )

    llm_response = await call_llm(llm_request)

    # Parse response
    try:
        content = llm_response.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            content = content.rsplit("```", 1)[0]
        parsed = json.loads(content.strip())
    except json.JSONDecodeError:
        raise ValueError("AI generated invalid remediation plan. Please try again.")

    # Build the plan
    steps = []
    for step_data in parsed.get("steps", []):
        steps.append(RemediationStep(
            step_number=step_data.get("step_number", len(steps) + 1),
            description=step_data.get("description", ""),
            command=step_data.get("command"),
            command_type=step_data.get("command_type", "cli"),
            risk_level=step_data.get("risk_level", "medium"),
            rollback_command=step_data.get("rollback_command"),
            verification=step_data.get("verification"),
        ))

    plan = RemediationPlan(
        device_id=request.device_id,
        device_name=device_info.get("hostname", "Unknown"),
        finding_summary=parsed.get("finding_summary", ""),
        steps=steps,
        risk_assessment=parsed.get("risk_assessment", "Review required"),
        estimated_impact=parsed.get("estimated_impact", "Unknown"),
        rollback_plan=parsed.get("rollback_plan", "Rollback steps included per step"),
        prerequisites=parsed.get("prerequisites", []),
        warnings=parsed.get("warnings", []),
    )

    # Save as draft for approval
    from shared.db_models import AIRemediationDraftDB
    draft = AIRemediationDraftDB(
        device_id=request.device_id,
        audit_result_id=request.audit_result_id,
        generated_plan=plan.model_dump(),
        confidence_score=_compute_confidence(plan),
        status="pending_approval",
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)

    # Log interaction
    interaction_id = None
    try:
        from shared.db_models import AIInteractionDB
        interaction = AIInteractionDB(
            interaction_type=InteractionType.REMEDIATION.value,
            input_prompt=user_prompt[:2000],
            ai_response={"plan_summary": plan.finding_summary, "steps_count": len(steps)},
            model_used=llm_response.model,
            tokens_used=llm_response.tokens_used,
        )
        db.add(interaction)
        db.commit()
        db.refresh(interaction)
        interaction_id = interaction.id
    except Exception as e:
        logger.warning(f"Failed to log interaction: {e}")

    return RemediationResponse(
        plan=plan,
        confidence_score=_compute_confidence(plan),
        requires_approval=True,
        draft_id=draft.id,
        interaction_id=interaction_id,
    )


async def _get_device_info(device_id: int) -> Optional[dict]:
    """Fetch device info from device service"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{DEVICE_SERVICE_URL}/devices/{device_id}")
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        logger.error(f"Error fetching device {device_id}: {e}")
    return None


async def _get_finding_context(device_id: int, audit_result_id: int, finding_index: Optional[int]) -> str:
    """Fetch audit finding details"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{RULE_SERVICE_URL}/audit/results",
                params={"device_id": device_id, "latest_only": "false"}
            )
            if response.status_code == 200:
                results = response.json()
                for result in results:
                    if result.get("id") == audit_result_id:
                        findings = result.get("findings", [])
                        if finding_index is not None and finding_index < len(findings):
                            return json.dumps(findings[finding_index], indent=2)
                        return json.dumps(findings[:3], indent=2)  # First 3 findings
    except Exception as e:
        logger.error(f"Error fetching audit findings: {e}")
    return ""


async def _get_recent_config(device_id: int) -> str:
    """Fetch most recent config backup"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{BACKUP_SERVICE_URL}/config-backups/device/{device_id}/history",
                params={"limit": 1}
            )
            if response.status_code == 200:
                backups = response.json()
                if backups:
                    return backups[0].get("config_data", "")
    except Exception as e:
        logger.error(f"Error fetching config for device {device_id}: {e}")
    return ""


def _compute_confidence(plan: RemediationPlan) -> float:
    """Compute confidence for the remediation plan"""
    score = 0.4

    if plan.steps:
        score += 0.15

    # Steps have rollback commands
    rollback_count = sum(1 for s in plan.steps if s.rollback_command)
    if plan.steps and rollback_count == len(plan.steps):
        score += 0.15
    elif plan.steps and rollback_count > 0:
        score += 0.08

    # Steps have verification
    verify_count = sum(1 for s in plan.steps if s.verification)
    if plan.steps and verify_count == len(plan.steps):
        score += 0.1

    if plan.prerequisites:
        score += 0.05

    if plan.warnings:
        score += 0.05

    return min(score, 0.9)
