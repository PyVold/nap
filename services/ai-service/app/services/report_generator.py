"""
Automated Compliance Report Generation Service
Generates AI-powered compliance reports with executive summaries.
"""

import json
import os
import httpx
from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy.orm import Session
from models.schemas import (
    ReportRequest, ReportResponse, ReportFormat, LLMRequest, InteractionType,
)
from services.llm_adapter import call_llm
from shared.logger import setup_logger

logger = setup_logger(__name__)

DEVICE_SERVICE_URL = os.getenv("DEVICE_SERVICE_URL", "http://device-service:3001")
RULE_SERVICE_URL = os.getenv("RULE_SERVICE_URL", "http://rule-service:3002")
BACKUP_SERVICE_URL = os.getenv("BACKUP_SERVICE_URL", "http://backup-service:3003")
ANALYTICS_SERVICE_URL = os.getenv("ANALYTICS_SERVICE_URL", "http://analytics-service:3006")


REPORT_SYSTEM_PROMPTS = {
    ReportFormat.EXECUTIVE: """You are a compliance reporting specialist. Generate an executive-level compliance report.

FORMAT:
- Title and date
- Executive Summary (2-3 paragraphs)
- Key Metrics (compliance score, device health, trend)
- Top Risks (top 5 critical findings)
- Recommendations (prioritized action items)
- Conclusion

STYLE: Professional, concise, suitable for C-level executives. Use percentages and counts.
Use markdown formatting with headers, bullet points, and bold for emphasis.""",

    ReportFormat.DETAILED: """You are a compliance reporting specialist. Generate a detailed technical compliance report.

FORMAT:
- Title and date
- Executive Summary
- Scope (devices, rules, time period)
- Compliance Overview (per device, per category, per severity)
- Detailed Findings (every failed audit with remediation guidance)
- Configuration Drift Analysis
- Health Status Summary
- Trend Analysis
- Recommendations (technical)
- Appendices

STYLE: Technical, thorough, suitable for network engineers and auditors.
Use markdown with tables, code blocks for configs, and detailed explanations.""",

    ReportFormat.FRAMEWORK: """You are a compliance framework specialist. Generate a framework-aligned compliance report.

FORMAT:
- Title with framework name and date
- Framework Overview & Applicability
- Control Assessment Summary (pass/fail per control)
- Detailed Control Analysis
- Gap Analysis
- Risk Matrix
- Remediation Roadmap
- Evidence References

Map NAP audit findings to framework controls. Use the specific framework's terminology and control IDs.
Use markdown with tables for control mappings.""",
}


async def generate_report(
    request: ReportRequest,
    db: Session,
) -> ReportResponse:
    """Generate an AI-powered compliance report"""

    # Gather all data needed for the report
    data = await _gather_report_data(request)

    # Build the prompt
    system_prompt = REPORT_SYSTEM_PROMPTS.get(request.report_type, REPORT_SYSTEM_PROMPTS[ReportFormat.EXECUTIVE])

    if request.framework:
        system_prompt += f"\n\nTarget compliance framework: {request.framework}"

    user_prompt = f"""Generate a compliance report based on this data:

REPORT PARAMETERS:
- Type: {request.report_type.value}
- Framework: {request.framework or 'General'}
- Time period: Last {request.date_range_days} days
- Date: {datetime.utcnow().strftime('%Y-%m-%d')}

COMPLIANCE DATA:
{json.dumps(data.get('compliance', {}), indent=2, default=str)[:3000]}

DEVICE SUMMARY:
{json.dumps(data.get('devices_summary', {}), indent=2, default=str)[:2000]}

AUDIT RESULTS:
{json.dumps(data.get('audit_results', [])[:20], indent=2, default=str)[:4000]}

HEALTH SUMMARY:
{json.dumps(data.get('health_summary', {}), indent=2, default=str)[:1000]}

DRIFT EVENTS:
{json.dumps(data.get('drift_summary', {}), indent=2, default=str)[:1000]}

{'TREND DATA:' + json.dumps(data.get('trends', {}), indent=2, default=str)[:2000] if request.include_trends else ''}

Generate the full report in markdown format."""

    llm_request = LLMRequest(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.3,
        max_tokens=8192,
    )

    llm_response = await call_llm(llm_request)

    # Extract key findings and recommendations using a quick follow-up
    extract_prompt = f"""From this compliance report, extract:
1. The executive summary (first 2-3 sentences)
2. Top 5 key findings (one line each)
3. Top 5 recommendations (one line each)

Report:
{llm_response.content[:6000]}

Respond with JSON:
{{"executive_summary": "...", "key_findings": ["..."], "recommendations": ["..."]}}"""

    extract_request = LLMRequest(
        system_prompt="Extract structured data from compliance reports. Return only valid JSON.",
        user_prompt=extract_prompt,
        temperature=0.1,
        max_tokens=2048,
    )

    extract_response = await call_llm(extract_request)

    try:
        content = extract_response.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            content = content.rsplit("```", 1)[0]
        extracted = json.loads(content.strip())
    except json.JSONDecodeError:
        extracted = {
            "executive_summary": "Report generated successfully. See full content for details.",
            "key_findings": [],
            "recommendations": [],
        }

    # Save report to database
    from shared.db_models import AIReportDB
    report_db = AIReportDB(
        title=f"Compliance Report - {request.report_type.value.title()} - {datetime.utcnow().strftime('%Y-%m-%d')}",
        report_type=request.report_type.value,
        framework=request.framework,
        content=llm_response.content,
        executive_summary=extracted.get("executive_summary", ""),
        key_findings=extracted.get("key_findings", []),
        recommendations=extracted.get("recommendations", []),
        data_sources={
            "devices": len(data.get("devices_summary", {}).get("devices", [])) if isinstance(data.get("devices_summary"), dict) else 0,
            "audit_results": len(data.get("audit_results", [])),
            "date_range_days": request.date_range_days,
        },
    )
    db.add(report_db)
    db.commit()
    db.refresh(report_db)

    # Log interaction
    interaction_id = None
    try:
        from shared.db_models import AIInteractionDB
        interaction = AIInteractionDB(
            interaction_type=InteractionType.REPORT.value,
            input_prompt=f"Report: {request.report_type.value}, framework: {request.framework}",
            ai_response={"report_id": report_db.id, "length": len(llm_response.content)},
            model_used=llm_response.model,
            tokens_used=llm_response.tokens_used + extract_response.tokens_used,
        )
        db.add(interaction)
        db.commit()
        db.refresh(interaction)
        interaction_id = interaction.id
    except Exception as e:
        logger.warning(f"Failed to log interaction: {e}")

    return ReportResponse(
        report_id=report_db.id,
        title=report_db.title,
        report_type=request.report_type,
        content=llm_response.content,
        executive_summary=extracted.get("executive_summary", ""),
        key_findings=extracted.get("key_findings", []),
        recommendations=extracted.get("recommendations", []),
        generated_at=datetime.utcnow().isoformat(),
        data_sources=report_db.data_sources,
        interaction_id=interaction_id,
    )


async def _gather_report_data(request: ReportRequest) -> dict:
    """Gather all necessary data for report generation"""
    data = {}
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Compliance data
        try:
            resp = await client.get(f"{RULE_SERVICE_URL}/audit/compliance")
            if resp.status_code == 200:
                data["compliance"] = resp.json()
        except Exception as e:
            logger.warning(f"Failed to get compliance data: {e}")

        # Devices
        try:
            resp = await client.get(f"{DEVICE_SERVICE_URL}/devices/")
            if resp.status_code == 200:
                devices = resp.json()
                if request.device_ids:
                    devices = [d for d in devices if d.get("id") in request.device_ids]
                data["devices_summary"] = {
                    "total": len(devices),
                    "devices": [{"hostname": d.get("hostname"), "vendor": d.get("vendor"),
                                 "compliance": d.get("compliance"), "status": d.get("status")} for d in devices[:50]]
                }
        except Exception as e:
            logger.warning(f"Failed to get devices: {e}")

        # Audit results
        try:
            resp = await client.get(f"{RULE_SERVICE_URL}/audit/results", params={"latest_only": "true"})
            if resp.status_code == 200:
                data["audit_results"] = resp.json()
        except Exception as e:
            logger.warning(f"Failed to get audit results: {e}")

        # Health summary
        try:
            resp = await client.get(f"{DEVICE_SERVICE_URL}/health/summary")
            if resp.status_code == 200:
                data["health_summary"] = resp.json()
        except Exception as e:
            logger.warning(f"Failed to get health summary: {e}")

        # Drift summary
        try:
            resp = await client.get(f"{BACKUP_SERVICE_URL}/drift-detection/summary")
            if resp.status_code == 200:
                data["drift_summary"] = resp.json()
        except Exception as e:
            logger.warning(f"Failed to get drift summary: {e}")

        # Trends
        if request.include_trends:
            try:
                resp = await client.get(f"{ANALYTICS_SERVICE_URL}/analytics/trends")
                if resp.status_code == 200:
                    data["trends"] = resp.json()
            except Exception as e:
                logger.warning(f"Failed to get trends: {e}")

    return data
