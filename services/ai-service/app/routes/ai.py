"""
AI Service API Routes
Handles all AI-powered features: rule builder, chat, remediation, reports, anomaly detection.
"""

from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from shared.database import get_db
from shared.deps import get_current_user, require_admin_or_operator
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
    raw_request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Ask questions about network state in natural language"""
    try:
        from services.chat_query import process_chat
        auth_header = raw_request.headers.get("authorization", "")
        user_id = current_user.get("id") or current_user.get("user_id")
        return await process_chat(request, db, auth_token=auth_header, user_id=user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Chat query failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to process query. Please try again.")


# ============================================================================
# Chat Sessions (Persistent Memory)
# ============================================================================

@router.get("/chat/sessions")
async def list_chat_sessions(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List all chat sessions for the current user"""
    from shared.db_models import ChatSessionDB

    user_id = current_user.get("id") or current_user.get("user_id")
    sessions = (
        db.query(ChatSessionDB)
        .filter(ChatSessionDB.user_id == user_id, ChatSessionDB.is_active == True)
        .order_by(ChatSessionDB.updated_at.desc())
        .limit(50)
        .all()
    )
    return [
        {
            "id": s.id,
            "title": s.title,
            "message_count": len(s.messages or []),
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "updated_at": s.updated_at.isoformat() if s.updated_at else None,
        }
        for s in sessions
    ]


@router.post("/chat/sessions")
async def create_chat_session(
    title: str = "New Chat",
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Create a new chat session"""
    from shared.db_models import ChatSessionDB

    user_id = current_user.get("id") or current_user.get("user_id")
    session = ChatSessionDB(user_id=user_id, title=title, messages=[])
    db.add(session)
    db.commit()
    db.refresh(session)
    return {"id": session.id, "title": session.title}


@router.get("/chat/sessions/{session_id}")
async def get_chat_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get a chat session with full message history"""
    from shared.db_models import ChatSessionDB

    user_id = current_user.get("id") or current_user.get("user_id")
    session = (
        db.query(ChatSessionDB)
        .filter(ChatSessionDB.id == session_id, ChatSessionDB.user_id == user_id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "id": session.id,
        "title": session.title,
        "messages": session.messages or [],
        "summary": session.summary,
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "updated_at": session.updated_at.isoformat() if session.updated_at else None,
    }


@router.delete("/chat/sessions/{session_id}")
async def delete_chat_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Delete (soft) a chat session"""
    from shared.db_models import ChatSessionDB

    user_id = current_user.get("id") or current_user.get("user_id")
    session = (
        db.query(ChatSessionDB)
        .filter(ChatSessionDB.id == session_id, ChatSessionDB.user_id == user_id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.is_active = False
    db.commit()
    return {"status": "deleted", "session_id": session_id}


@router.put("/chat/sessions/{session_id}/title")
async def rename_chat_session(
    session_id: int,
    title: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Rename a chat session"""
    from shared.db_models import ChatSessionDB

    user_id = current_user.get("id") or current_user.get("user_id")
    session = (
        db.query(ChatSessionDB)
        .filter(ChatSessionDB.id == session_id, ChatSessionDB.user_id == user_id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.title = title
    db.commit()
    return {"status": "renamed", "session_id": session_id, "title": title}


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


class DirectFeedbackRequest(BaseModel):
    feature_type: str
    rating: str
    comment: Optional[str] = None
    response_summary: Optional[str] = None


@router.post("/feedback/direct")
async def submit_direct_feedback(
    feedback: DirectFeedbackRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Submit feedback on AI-generated content without requiring interaction_id"""
    from shared.db_models import AIInteractionDB

    # Create a feedback-specific interaction record
    interaction = AIInteractionDB(
        interaction_type=feedback.feature_type,
        input_prompt=feedback.comment or f"Feedback for {feedback.feature_type}",
        ai_response={"response_summary": (feedback.response_summary or "")[:500]},
        model_used="feedback",
        tokens_used=0,
        feedback=feedback.rating,
    )
    db.add(interaction)
    db.commit()

    return {"status": "ok", "message": "Feedback recorded", "interaction_id": interaction.id}


@router.get("/interactions")
async def list_interactions(
    feature_type: str = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List AI interaction history with optional filtering"""
    from shared.db_models import AIInteractionDB

    query = db.query(AIInteractionDB)
    if feature_type:
        query = query.filter(AIInteractionDB.interaction_type == feature_type)

    total = query.count()
    interactions = query.order_by(AIInteractionDB.created_at.desc()).offset(offset).limit(limit).all()

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "interactions": [
            {
                "id": i.id,
                "interaction_type": i.interaction_type,
                "input_prompt": i.input_prompt[:200] if i.input_prompt else None,
                "ai_response": i.ai_response,
                "model_used": i.model_used,
                "tokens_used": i.tokens_used,
                "feedback": i.feedback,
                "created_at": i.created_at.isoformat() if i.created_at else None,
            }
            for i in interactions
        ],
    }


@router.get("/feedback/stats")
async def feedback_stats(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get aggregate feedback statistics"""
    from shared.db_models import AIInteractionDB

    # Total interactions
    total = db.query(func.count(AIInteractionDB.id)).scalar()

    # By feature type
    by_type = db.query(
        AIInteractionDB.interaction_type,
        func.count(AIInteractionDB.id),
    ).group_by(AIInteractionDB.interaction_type).all()

    # Feedback breakdown
    with_feedback = db.query(
        AIInteractionDB.feedback,
        func.count(AIInteractionDB.id),
    ).filter(AIInteractionDB.feedback.isnot(None)).group_by(AIInteractionDB.feedback).all()

    # Tokens used
    total_tokens = db.query(func.sum(AIInteractionDB.tokens_used)).scalar() or 0

    return {
        "total_interactions": total,
        "by_feature_type": {t: c for t, c in by_type},
        "feedback_breakdown": {f: c for f, c in with_feedback},
        "total_tokens_used": total_tokens,
        "feedback_rate": round(
            sum(c for _, c in with_feedback) / max(total, 1) * 100, 1
        ),
    }


# ============================================================================
# Config Change Impact Analysis (Phase 3)
# ============================================================================

@router.post("/impact/analyze", response_model=ImpactAnalysisResponse)
async def analyze_impact(
    request: ImpactAnalysisRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Analyze the potential impact of a proposed configuration change"""
    try:
        from services.impact_analyzer import analyze_impact as do_analyze
        return await do_analyze(request, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Impact analysis failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to analyze impact.")


# ============================================================================
# Compliance Posture Prediction (Phase 3)
# ============================================================================

@router.post("/compliance/predict")
async def predict_compliance(
    device_id: int = None,
    device_group_id: int = None,
    forecast_days: int = 30,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Predict future compliance posture based on historical trends"""
    try:
        from services.compliance_predictor import predict_compliance as predict
        return await predict(db, device_id, device_group_id, forecast_days)
    except Exception as e:
        logger.error(f"Compliance prediction failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to predict compliance.")


@router.post("/compliance/what-if")
async def what_if_analysis(
    scenario: str,
    device_ids: list = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Run a what-if compliance scenario analysis"""
    try:
        from services.compliance_predictor import what_if_analysis as what_if
        return await what_if(db, scenario, device_ids)
    except Exception as e:
        logger.error(f"What-if analysis failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to run what-if analysis.")


# ============================================================================
# Config Optimization (Phase 3)
# ============================================================================

@router.post("/config/optimize/{device_id}")
async def optimize_config(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Analyze device config for optimization opportunities"""
    try:
        from services.config_optimizer import analyze_config
        return await analyze_config(device_id, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Config optimization failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to analyze config.")


@router.post("/config/compare-group/{group_id}")
async def compare_group_configs(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Compare configs across a device group for inconsistencies"""
    try:
        from services.config_optimizer import compare_group_configs as compare
        return await compare(group_id, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Group config comparison failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to compare group configs.")


# ============================================================================
# Embedding-Based Config Search (Phase 3)
# ============================================================================

@router.post("/config/search")
async def search_configs(
    query: str,
    max_results: int = 10,
    vendor: str = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Semantic search across device configurations"""
    try:
        from services.config_search import semantic_search
        return await semantic_search(query, db, max_results, vendor)
    except Exception as e:
        logger.error(f"Config search failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to search configs.")


@router.post("/config/similar/{device_id}")
async def find_similar(
    device_id: int,
    section: str = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Find devices with similar configurations"""
    try:
        from services.config_search import find_similar_configs
        return await find_similar_configs(device_id, db, section)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Similarity search failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to find similar configs.")


# ============================================================================
# Multi-Agent Operations (Phase 4)
# ============================================================================

@router.post("/agents/orchestrate")
async def orchestrate_operation(
    request: str,
    context: dict = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin_or_operator),
):
    """Orchestrate a complex multi-agent network operation"""
    try:
        from services.multi_agent import orchestrate
        return await orchestrate(request, db, context)
    except Exception as e:
        logger.error(f"Multi-agent orchestration failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to orchestrate operation.")


# ============================================================================
# Adaptive Monitoring (Phase 4)
# ============================================================================

@router.post("/monitoring/evaluate")
async def evaluate_monitoring(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin_or_operator),
):
    """Evaluate network state and adapt monitoring intervals"""
    try:
        from services.adaptive_monitor import evaluate_and_adapt
        return await evaluate_and_adapt(db)
    except Exception as e:
        logger.error(f"Adaptive monitoring evaluation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to evaluate monitoring.")


@router.get("/monitoring/recommendations")
async def monitoring_recommendations(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get AI recommendations for monitoring configuration"""
    try:
        from services.adaptive_monitor import get_monitoring_recommendations
        return await get_monitoring_recommendations(db)
    except Exception as e:
        logger.error(f"Monitoring recommendations failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to get recommendations.")


# ============================================================================
# Self-Healing Workflows (Phase 4)
# ============================================================================

@router.post("/self-heal")
async def create_self_healing_plan(
    trigger_event: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin_or_operator),
):
    """Create a self-healing workflow plan (requires human approval)"""
    try:
        from services.adaptive_monitor import create_self_healing_plan
        return await create_self_healing_plan(trigger_event, db)
    except Exception as e:
        logger.error(f"Self-healing plan creation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to create self-healing plan.")


# ============================================================================
# Knowledge Base / RAG (Phase 4)
# ============================================================================

@router.get("/knowledge-base")
async def list_knowledge_entries(
    category: str = None,
    vendor: str = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List knowledge base entries for RAG"""
    try:
        from services.knowledge_base import list_entries
        return await list_entries(db, category, vendor, limit)
    except Exception as e:
        logger.error(f"Knowledge base list failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to list knowledge base entries.")


@router.post("/knowledge-base")
async def add_knowledge_entry(
    title: str,
    content: str,
    category: str = "general",
    vendor: str = None,
    tags: str = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin_or_operator),
):
    """Add a new knowledge base entry"""
    try:
        from services.knowledge_base import add_entry
        tag_list = [t.strip() for t in tags.split(",")] if tags else []
        return await add_entry(db, title, content, category, vendor, tag_list, current_user.get("username"))
    except Exception as e:
        logger.error(f"Knowledge base add failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to add knowledge base entry.")


@router.post("/knowledge-base/upload")
async def upload_knowledge_document(
    file: UploadFile = File(...),
    category: str = Form("general"),
    vendor: str = Form(None),
    tags: str = Form(""),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin_or_operator),
):
    """Upload a document (PDF, DOCX, TXT, MD) to the knowledge base.
    Text is extracted and stored as searchable knowledge base entries."""
    from services.document_parser import extract_text_from_upload

    try:
        # Read file content
        content_bytes = await file.read()
        filename = file.filename or "unknown"

        # Extract text
        text, doc_metadata = await extract_text_from_upload(content_bytes, filename)

        if not text or not text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from the uploaded file.")

        # Split into chunks if the document is large (> 4000 chars)
        chunks = _split_text_into_chunks(text, max_chars=4000)
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        tag_list.append(f"source:{filename}")
        username = current_user.get("username")

        from services.knowledge_base import add_entry
        entries_created = []
        for i, chunk in enumerate(chunks):
            title = f"{filename}" if len(chunks) == 1 else f"{filename} (part {i + 1}/{len(chunks)})"
            result = await add_entry(
                db, title, chunk, category,
                vendor if vendor else None,
                tag_list, username
            )
            entries_created.append(result)

        return {
            "status": "uploaded",
            "filename": filename,
            "file_size": len(content_bytes),
            "text_length": len(text),
            "chunks_created": len(entries_created),
            "metadata": doc_metadata,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Knowledge base upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process upload: {str(e)}")


def _split_text_into_chunks(text: str, max_chars: int = 4000) -> list:
    """Split text into chunks, preferring paragraph boundaries."""
    if len(text) <= max_chars:
        return [text]

    chunks = []
    paragraphs = text.split("\n\n")
    current_chunk = ""

    for para in paragraphs:
        if len(current_chunk) + len(para) + 2 > max_chars:
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = ""
            # If a single paragraph is too long, split by sentences
            if len(para) > max_chars:
                sentences = para.replace(". ", ".\n").split("\n")
                for sent in sentences:
                    if len(current_chunk) + len(sent) + 1 > max_chars:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                        current_chunk = sent
                    else:
                        current_chunk += " " + sent if current_chunk else sent
            else:
                current_chunk = para
        else:
            current_chunk += "\n\n" + para if current_chunk else para

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks


@router.delete("/knowledge-base/{entry_id}")
async def delete_knowledge_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin_or_operator),
):
    """Delete a knowledge base entry"""
    try:
        from services.knowledge_base import delete_entry
        return await delete_entry(db, entry_id)
    except Exception as e:
        logger.error(f"Knowledge base delete failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete knowledge base entry.")


@router.post("/knowledge-base/query")
async def query_knowledge_base(
    query: str,
    category: str = None,
    vendor: str = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Query the knowledge base using semantic search (RAG)"""
    try:
        from services.knowledge_base import query_knowledge
        return await query_knowledge(db, query, category, vendor)
    except Exception as e:
        logger.error(f"Knowledge base query failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to query knowledge base.")


# ============================================================================
# AI Service Status
# ============================================================================

@router.get("/status")
async def ai_status():
    """Get AI service status and available providers"""
    from services.llm_adapter import (
        get_available_providers, get_default_provider, check_local_llm_status,
        LOCAL_LLM_URL, LOCAL_LLM_API_FORMAT, LOCAL_MODEL,
        ANTHROPIC_MODEL, OPENAI_MODEL,
    )
    providers = get_available_providers()
    default = get_default_provider()
    local_status = await check_local_llm_status()

    return {
        "status": "online",
        "available_providers": [p.value for p in providers],
        "default_provider": default.value,
        "provider_config": {
            "anthropic": {"model": ANTHROPIC_MODEL},
            "openai": {"model": OPENAI_MODEL},
            "local": {
                "url": LOCAL_LLM_URL,
                "model": LOCAL_MODEL,
                "api_format": LOCAL_LLM_API_FORMAT,
                "reachable": local_status["reachable"],
                "available_models": local_status.get("models", []),
                "error": local_status.get("error"),
            },
        },
        "features": {
            "phase_1": ["rule_builder", "chat_query", "mcp_server", "llm_adapter"],
            "phase_2": ["remediation_advisor", "report_generator", "anomaly_detection", "mcp_hub"],
            "phase_3": ["impact_analysis", "compliance_prediction", "config_optimization", "config_search", "feedback_loop"],
            "phase_4": ["multi_agent_ops", "adaptive_monitoring", "self_healing_workflows"],
        },
    }
