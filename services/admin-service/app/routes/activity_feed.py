# ============================================================================
# routes/activity_feed.py - Activity Feed API
# ============================================================================

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional
from datetime import datetime, timedelta

from shared.database import get_db
import db_models

router = APIRouter(prefix="/activity-feed", tags=["Activity Feed"])


@router.get("/")
async def get_activity_feed(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    resource_type: Optional[str] = None,
    action: Optional[str] = None,
    hours: int = Query(72, ge=1, le=720),
    db: Session = Depends(get_db)
):
    """
    Get recent platform activity (audit logs) for the activity feed.

    Returns recent actions like device discoveries, audit runs, rule changes,
    config backups, user logins, etc.
    """
    since = datetime.utcnow() - timedelta(hours=hours)

    query = db.query(db_models.AuditLogDB).filter(
        db_models.AuditLogDB.timestamp >= since
    )

    if resource_type:
        query = query.filter(db_models.AuditLogDB.resource_type == resource_type)
    if action:
        query = query.filter(db_models.AuditLogDB.action == action)

    total = query.count()

    logs = query.order_by(
        desc(db_models.AuditLogDB.timestamp)
    ).offset(offset).limit(limit).all()

    return {
        "total": total,
        "items": [{
            "id": log.id,
            "username": log.username,
            "timestamp": log.timestamp.isoformat() if log.timestamp else None,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "details": log.details,
            "ip_address": log.ip_address,
        } for log in logs]
    }


@router.get("/summary")
async def get_activity_summary(
    hours: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_db)
):
    """
    Get a summary of recent activity grouped by resource type and action.
    """
    from sqlalchemy import func

    since = datetime.utcnow() - timedelta(hours=hours)

    # Count by resource type
    by_resource = db.query(
        db_models.AuditLogDB.resource_type,
        func.count(db_models.AuditLogDB.id)
    ).filter(
        db_models.AuditLogDB.timestamp >= since
    ).group_by(
        db_models.AuditLogDB.resource_type
    ).all()

    # Count by action
    by_action = db.query(
        db_models.AuditLogDB.action,
        func.count(db_models.AuditLogDB.id)
    ).filter(
        db_models.AuditLogDB.timestamp >= since
    ).group_by(
        db_models.AuditLogDB.action
    ).order_by(
        desc(func.count(db_models.AuditLogDB.id))
    ).limit(10).all()

    # Active users
    active_users = db.query(
        db_models.AuditLogDB.username,
        func.count(db_models.AuditLogDB.id)
    ).filter(
        db_models.AuditLogDB.timestamp >= since,
        db_models.AuditLogDB.username.isnot(None)
    ).group_by(
        db_models.AuditLogDB.username
    ).all()

    total = db.query(func.count(db_models.AuditLogDB.id)).filter(
        db_models.AuditLogDB.timestamp >= since
    ).scalar()

    return {
        "period_hours": hours,
        "total_events": total or 0,
        "by_resource_type": {r: c for r, c in by_resource if r},
        "top_actions": {a: c for a, c in by_action if a},
        "active_users": {u: c for u, c in active_users if u},
    }
