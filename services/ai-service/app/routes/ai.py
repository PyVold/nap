"""
AI Service API Routes
Handles all AI-powered features: rule builder, chat, remediation, reports, anomaly detection.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from shared.database import get_db
from shared.deps import get_current_user, require_admin_or_operator
from shared.license_middleware import require_license_module
from shared.logger import setup_logger
from models.schemas import (
    RuleBuilderRequest, RuleBuilderResponse, RuleDraftApproval,
    ChatRequest, ChatResponse,
    RemediationRequest, RemediationResponse, RemediationApproval,
    ReportRequest, ReportResponse,
    AnomalyDetectionRequest, AnomalyDetectionResponse,
    ImpactAnalysisRequest, ImpactAnalysisResponse,
    AIFeedback,
)

logger = setup_logger(__name__)
router = APIRouter(prefix="/ai")


# ============================================================================
# Natural Language Rule Builder
# ============================================================================

@router.post("/rules/generate", response_model=RuleBuilderResponse)
async def generate_rule(
    request: RuleBuilderRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin_or_operator),
):
    """Generate an audit rule from natural language description"""
    try:
        from services.rule_builder import generate_rule as gen_rule
        return await gen_rule(request, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Rule generation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate rule. Please try again.")


@router.post("/rules/drafts/{draft_id}/action")
async def action_rule_draft(
    draft_id: int,
    approval: RuleDraftApproval,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin_or_operator),
):
    """Approve, reject, or modify a generated rule draft"""
    from shared.db_models import AIRuleDraftDB, AuditRuleDB

    draft = db.query(AIRuleDraftDB).filter(AIRuleDraftDB.id == draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    if approval.action == "approve":
        # Create actual audit rule from draft
        rule_data = draft.generated_rule
        if approval.modifications:
            rule_data.update(approval.modifications)

        new_rule = AuditRuleDB(
            name=rule_data["name"],
            description=rule_data.get("description", ""),
            severity=rule_data.get("severity", "medium"),
            category=rule_data.get("category", "General"),
            vendors=rule_data.get("vendors", []),
            checks=rule_data.get("checks", []),
            enabled=True,
        )
        db.add(new_rule)
        draft.status = "approved"
        draft.approved_by = current_user.get("username")
        db.commit()
        db.refresh(new_rule)

        return {"status": "approved", "rule_id": new_rule.id, "message": "Rule created successfully"}

    elif approval.action == "reject":
        draft.status = "rejected"
        db.commit()
        return {"status": "rejected", "message": "Draft rejected"}

    elif approval.action == "modify":
        if not approval.modifications:
            raise HTTPException(status_code=400, detail="Modifications required for 'modify' action")
        draft.generated_rule.update(approval.modifications)
        draft.status = "modified"
        db.commit()
        return {"status": "modified", "message": "Draft updated"}

    raise HTTPException(status_code=400, detail=f"Invalid action: {approval.action}")


@router.get("/rules/drafts")
async def list_rule_drafts(
    status_filter: str = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List all AI-generated rule drafts"""
    from shared.db_models import AIRuleDraftDB

    query = db.query(AIRuleDraftDB)
    if status_filter:
        query = query.filter(AIRuleDraftDB.status == status_filter)

    drafts = query.order_by(AIRuleDraftDB.created_at.desc()).limit(50).all()
    return [
        {
            "id": d.id,
            "source_prompt": d.source_prompt,
            "generated_rule": d.generated_rule,
            "confidence_score": d.confidence_score,
            "status": d.status,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in drafts
    ]


# ============================================================================
# Natural Language Network Query (AI Chat)
# ============================================================================

@router.post("/chat", response_model=ChatResponse)
async def chat_query(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Ask questions about network state in natural language"""
    try:
        from services.chat_query import process_chat
        return await process_chat(request, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Chat query failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to process query. Please try again.")


# ============================================================================
# Remediation Advisor
# ============================================================================

@router.post("/remediation/generate", response_model=RemediationResponse)
async def generate_remediation(
    request: RemediationRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin_or_operator),
):
    """Generate an AI-powered remediation plan for audit failures"""
    try:
        from services.remediation_advisor import generate_remediation as gen_remediation
        return await gen_remediation(request, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Remediation generation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate remediation plan.")


@router.post("/remediation/drafts/{draft_id}/action")
async def action_remediation_draft(
    draft_id: int,
    approval: RemediationApproval,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin_or_operator),
):
    """Approve, reject, or modify a remediation plan"""
    from shared.db_models import AIRemediationDraftDB

    draft = db.query(AIRemediationDraftDB).filter(AIRemediationDraftDB.id == draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Remediation draft not found")

    if approval.action == "approve":
        draft.status = "approved"
        draft.approved_by = current_user.get("username")
        db.commit()
        return {"status": "approved", "message": "Remediation plan approved. Execute via workflow engine."}

    elif approval.action == "reject":
        draft.status = "rejected"
        db.commit()
        return {"status": "rejected", "message": "Remediation plan rejected"}

    raise HTTPException(status_code=400, detail=f"Invalid action: {approval.action}")


@router.get("/remediation/drafts")
async def list_remediation_drafts(
    status_filter: str = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List all AI-generated remediation drafts"""
    from shared.db_models import AIRemediationDraftDB

    query = db.query(AIRemediationDraftDB)
    if status_filter:
        query = query.filter(AIRemediationDraftDB.status == status_filter)

    drafts = query.order_by(AIRemediationDraftDB.created_at.desc()).limit(50).all()
    return [
        {
            "id": d.id,
            "device_id": d.device_id,
            "generated_plan": d.generated_plan,
            "confidence_score": d.confidence_score,
            "status": d.status,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in drafts
    ]


# ============================================================================
# Compliance Report Generation
# ============================================================================

@router.post("/reports/generate", response_model=ReportResponse)
async def generate_report(
    request: ReportRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Generate an AI-powered compliance report"""
    try:
        from services.report_generator import generate_report as gen_report
        return await gen_report(request, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate report.")


@router.get("/reports")
async def list_reports(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List all generated reports"""
    from shared.db_models import AIReportDB

    reports = db.query(AIReportDB).order_by(AIReportDB.created_at.desc()).limit(50).all()
    return [
        {
            "id": r.id,
            "title": r.title,
            "report_type": r.report_type,
            "framework": r.framework,
            "executive_summary": r.executive_summary,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in reports
    ]


@router.get("/reports/{report_id}")
async def get_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get a specific generated report"""
    from shared.db_models import AIReportDB

    report = db.query(AIReportDB).filter(AIReportDB.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    return {
        "id": report.id,
        "title": report.title,
        "report_type": report.report_type,
        "framework": report.framework,
        "content": report.content,
        "executive_summary": report.executive_summary,
        "key_findings": report.key_findings,
        "recommendations": report.recommendations,
        "data_sources": report.data_sources,
        "created_at": report.created_at.isoformat() if report.created_at else None,
    }


# ============================================================================
# Anomaly Detection
# ============================================================================

@router.post("/anomalies/detect", response_model=AnomalyDetectionResponse)
async def detect_anomalies(
    request: AnomalyDetectionRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Detect anomalies in recent configuration changes"""
    try:
        from services.anomaly_detector import detect_anomalies as detect
        return await detect(request, db)
    except Exception as e:
        logger.error(f"Anomaly detection failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to run anomaly detection.")


# ============================================================================
# AI Feedback
# ============================================================================

@router.post("/feedback")
async def submit_feedback(
    feedback: AIFeedback,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Submit feedback on AI-generated content"""
    from shared.db_models import AIInteractionDB

    interaction = db.query(AIInteractionDB).filter(AIInteractionDB.id == feedback.interaction_id).first()
    if not interaction:
        raise HTTPException(status_code=404, detail="Interaction not found")

    interaction.feedback = feedback.rating
    if feedback.comment:
        existing = interaction.ai_response or {}
        existing["user_feedback"] = feedback.comment
        interaction.ai_response = existing

    db.commit()
    return {"status": "ok", "message": "Feedback recorded"}


# ============================================================================
# AI Service Status
# ============================================================================

@router.get("/status")
async def ai_status():
    """Get AI service status and available providers"""
    from services.llm_adapter import get_available_providers, get_default_provider
    providers = get_available_providers()
    default = get_default_provider()

    return {
        "status": "online",
        "available_providers": [p.value for p in providers],
        "default_provider": default.value,
        "features": [
            "rule_builder",
            "chat_query",
            "remediation_advisor",
            "report_generator",
            "anomaly_detection",
            "mcp_server",
            "mcp_hub",
        ],
    }
