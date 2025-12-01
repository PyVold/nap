# ============================================================================
# api/routes/notifications.py
# ============================================================================

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, HttpUrl

from api.deps import get_db
from db_models import NotificationWebhookDB, NotificationHistoryDB
from services.notification_service import NotificationService
from shared.license_middleware import require_license_module

router = APIRouter(prefix="/notifications", tags=["notifications"])


# ============================================================================
# Pydantic Models
# ============================================================================

class WebhookCreate(BaseModel):
    name: str
    webhook_url: str
    webhook_type: str  # slack, teams, discord, generic
    events: Dict[str, Any]  # {"audit_failure": {"threshold": 80}, "compliance_drop": {"threshold": 10}}
    is_active: bool = True


class WebhookUpdate(BaseModel):
    name: Optional[str] = None
    webhook_url: Optional[str] = None
    webhook_type: Optional[str] = None
    events: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class WebhookResponse(BaseModel):
    id: int
    name: str
    webhook_url: str
    webhook_type: str
    events: Dict[str, Any]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationHistoryResponse(BaseModel):
    id: int
    webhook_id: int
    event_type: str
    sent_at: datetime
    status: str
    error_message: Optional[str]

    class Config:
        from_attributes = True


class TestWebhookRequest(BaseModel):
    event_type: str = "test"
    data: Dict[str, Any] = {}


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/webhooks", response_model=WebhookResponse)
async def create_webhook(
    webhook: WebhookCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_license_module("webhooks"))
):
    """Create a new notification webhook"""
    try:
        db_webhook = NotificationWebhookDB(
            name=webhook.name,
            webhook_url=webhook.webhook_url,
            webhook_type=webhook.webhook_type,
            events=webhook.events,
            is_active=webhook.is_active
        )

        db.add(db_webhook)
        db.commit()
        db.refresh(db_webhook)

        return db_webhook

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/webhooks", response_model=List[WebhookResponse])
async def list_webhooks(
    active_only: bool = Query(False),
    db: Session = Depends(get_db),
    _: None = Depends(require_license_module("webhooks"))
):
    """List all notification webhooks"""
    query = db.query(NotificationWebhookDB)

    if active_only:
        query = query.filter(NotificationWebhookDB.is_active == True)

    webhooks = query.all()
    return webhooks


@router.get("/webhooks/{webhook_id}", response_model=WebhookResponse)
async def get_webhook(
    webhook_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_license_module("webhooks"))
):
    """Get a specific webhook by ID"""
    webhook = db.query(NotificationWebhookDB).filter(
        NotificationWebhookDB.id == webhook_id
    ).first()

    if not webhook:
        raise HTTPException(status_code=404, detail=f"Webhook {webhook_id} not found")

    return webhook


@router.patch("/webhooks/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(
    webhook_id: int,
    webhook_update: WebhookUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(require_license_module("webhooks"))
):
    """Update a webhook"""
    webhook = db.query(NotificationWebhookDB).filter(
        NotificationWebhookDB.id == webhook_id
    ).first()

    if not webhook:
        raise HTTPException(status_code=404, detail=f"Webhook {webhook_id} not found")

    # Update fields
    if webhook_update.name is not None:
        webhook.name = webhook_update.name
    if webhook_update.webhook_url is not None:
        webhook.webhook_url = webhook_update.webhook_url
    if webhook_update.webhook_type is not None:
        webhook.webhook_type = webhook_update.webhook_type
    if webhook_update.events is not None:
        webhook.events = webhook_update.events
    if webhook_update.is_active is not None:
        webhook.is_active = webhook_update.is_active

    try:
        db.commit()
        db.refresh(webhook)
        return webhook
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/webhooks/{webhook_id}")
async def delete_webhook(
    webhook_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_license_module("webhooks"))
):
    """Delete a webhook"""
    webhook = db.query(NotificationWebhookDB).filter(
        NotificationWebhookDB.id == webhook_id
    ).first()

    if not webhook:
        raise HTTPException(status_code=404, detail=f"Webhook {webhook_id} not found")

    try:
        db.delete(webhook)
        db.commit()
        return {"message": f"Webhook {webhook_id} deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhooks/{webhook_id}/test")
async def test_webhook(
    webhook_id: int,
    test_request: TestWebhookRequest,
    db: Session = Depends(get_db),
    _: None = Depends(require_license_module("webhooks"))
):
    """Test a webhook by sending a test notification"""
    webhook = db.query(NotificationWebhookDB).filter(
        NotificationWebhookDB.id == webhook_id
    ).first()

    if not webhook:
        raise HTTPException(status_code=404, detail=f"Webhook {webhook_id} not found")

    # Send test webhook
    test_data = {
        "message": "This is a test notification from Network Audit Platform",
        "timestamp": datetime.utcnow().isoformat(),
        **test_request.data
    }

    success = await NotificationService.send_webhook(
        webhook.webhook_url,
        webhook.webhook_type,
        test_request.event_type,
        test_data
    )

    if success:
        return {"message": "Test webhook sent successfully", "success": True}
    else:
        raise HTTPException(status_code=500, detail="Failed to send test webhook")


@router.get("/history", response_model=List[NotificationHistoryResponse])
async def get_notification_history(
    webhook_id: Optional[int] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: None = Depends(require_license_module("webhooks"))
):
    """Get notification history"""
    query = db.query(NotificationHistoryDB)

    if webhook_id:
        query = query.filter(NotificationHistoryDB.webhook_id == webhook_id)

    history = query.order_by(NotificationHistoryDB.sent_at.desc()).limit(limit).all()
    return history


@router.get("/stats")
async def get_notification_stats(
    db: Session = Depends(get_db),
    _: None = Depends(require_license_module("webhooks"))
):
    """Get notification statistics"""
    total_webhooks = db.query(NotificationWebhookDB).count()
    active_webhooks = db.query(NotificationWebhookDB).filter(
        NotificationWebhookDB.enabled == True
    ).count()

    total_sent = db.query(NotificationHistoryDB).count()
    total_failed = db.query(NotificationHistoryDB).filter(
        NotificationHistoryDB.success == False
    ).count()

    return {
        "total_webhooks": total_webhooks,
        "active_webhooks": active_webhooks,
        "total_notifications_sent": total_sent,
        "total_failures": total_failed,
        "success_rate": round((total_sent - total_failed) / total_sent * 100, 2) if total_sent > 0 else 100
    }
