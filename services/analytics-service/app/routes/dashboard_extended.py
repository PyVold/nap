# ============================================================================
# routes/dashboard_extended.py - Enhanced Dashboard Stats API
# ============================================================================

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, case
from typing import Optional
from datetime import datetime, timedelta

from shared.database import get_db

router = APIRouter(prefix="/analytics/dashboard", tags=["Dashboard"])


@router.get("/extended")
async def get_extended_dashboard(db: Session = Depends(get_db)):
    """
    Enhanced dashboard stats aggregating data from multiple sources.
    Returns compliance overview, device stats, top failing rules, and recent trends.
    """
    from db_models import (
        DeviceDB, AuditResultDB, AuditRuleDB, HealthCheckDB,
        ConfigBackupDB, ConfigChangeEventDB
    )

    now = datetime.utcnow()
    last_24h = now - timedelta(hours=24)
    last_7d = now - timedelta(days=7)

    # Device stats
    total_devices = db.query(func.count(DeviceDB.id)).scalar() or 0
    devices_by_vendor = db.query(
        DeviceDB.vendor, func.count(DeviceDB.id)
    ).group_by(DeviceDB.vendor).all()

    # Audit result stats
    total_results = db.query(func.count(AuditResultDB.id)).scalar() or 0
    failed_results = db.query(func.count(AuditResultDB.id)).filter(
        AuditResultDB.status == 'fail'
    ).scalar() or 0

    # Recent audit results (last 24h)
    recent_audits = db.query(func.count(AuditResultDB.id)).filter(
        AuditResultDB.created_at >= last_24h
    ).scalar() or 0

    # Top failing rules
    top_failures = db.query(
        AuditResultDB.rule_id,
        AuditRuleDB.name,
        AuditRuleDB.severity,
        func.count(AuditResultDB.id).label('failure_count')
    ).join(
        AuditRuleDB, AuditResultDB.rule_id == AuditRuleDB.id
    ).filter(
        AuditResultDB.status == 'fail'
    ).group_by(
        AuditResultDB.rule_id, AuditRuleDB.name, AuditRuleDB.severity
    ).order_by(
        desc('failure_count')
    ).limit(5).all()

    # Config backup stats
    total_backups = db.query(func.count(ConfigBackupDB.id)).scalar() or 0
    recent_backups = db.query(func.count(ConfigBackupDB.id)).filter(
        ConfigBackupDB.created_at >= last_24h
    ).scalar() or 0

    # Change events in last 7 days
    recent_changes = db.query(func.count(ConfigChangeEventDB.id)).filter(
        ConfigChangeEventDB.detected_at >= last_7d
    ).scalar() or 0

    # Health check summary
    latest_health = db.query(
        HealthCheckDB.status, func.count(HealthCheckDB.id)
    ).filter(
        HealthCheckDB.id.in_(
            db.query(func.max(HealthCheckDB.id)).group_by(HealthCheckDB.device_id)
        )
    ).group_by(HealthCheckDB.status).all()

    health_summary = {status: count for status, count in latest_health}

    # Rules stats
    total_rules = db.query(func.count(AuditRuleDB.id)).scalar() or 0
    enabled_rules = db.query(func.count(AuditRuleDB.id)).filter(
        AuditRuleDB.enabled == True
    ).scalar() or 0

    # Compliance score
    compliance_pct = 0
    if total_results > 0:
        passed = total_results - failed_results
        compliance_pct = round((passed / total_results) * 100, 1)

    return {
        "compliance": {
            "score": compliance_pct,
            "total_checks": total_results,
            "passed": total_results - failed_results,
            "failed": failed_results,
        },
        "devices": {
            "total": total_devices,
            "by_vendor": {v: c for v, c in devices_by_vendor if v},
            "health": health_summary,
        },
        "top_failing_rules": [{
            "rule_id": r.rule_id,
            "name": r.name,
            "severity": r.severity,
            "failure_count": r.failure_count,
        } for r in top_failures],
        "activity": {
            "audits_last_24h": recent_audits,
            "backups_last_24h": recent_backups,
            "changes_last_7d": recent_changes,
            "total_backups": total_backups,
        },
        "rules": {
            "total": total_rules,
            "enabled": enabled_rules,
            "disabled": total_rules - enabled_rules,
        },
        "generated_at": now.isoformat(),
    }


@router.get("/quick-stats")
async def get_quick_stats(db: Session = Depends(get_db)):
    """
    Lightweight stats for periodic dashboard refresh.
    """
    from db_models import DeviceDB, AuditResultDB, ConfigChangeEventDB

    now = datetime.utcnow()
    last_1h = now - timedelta(hours=1)

    total_devices = db.query(func.count(DeviceDB.id)).scalar() or 0
    total_results = db.query(func.count(AuditResultDB.id)).scalar() or 0
    failed = db.query(func.count(AuditResultDB.id)).filter(
        AuditResultDB.status == 'fail'
    ).scalar() or 0

    recent_changes = db.query(func.count(ConfigChangeEventDB.id)).filter(
        ConfigChangeEventDB.detected_at >= last_1h
    ).scalar() or 0

    compliance = round(((total_results - failed) / total_results * 100), 1) if total_results > 0 else 0

    return {
        "devices": total_devices,
        "compliance": compliance,
        "failed_checks": failed,
        "recent_changes": recent_changes,
        "timestamp": now.isoformat(),
    }
