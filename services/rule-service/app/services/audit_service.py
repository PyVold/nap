
# ============================================================================
# services/audit_service.py
# ============================================================================

import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from models.device import Device
from models.rule import AuditRule
from models.audit import AuditResult, AuditFinding
from models.enums import AuditStatus, DeviceStatus
from db_models import AuditResultDB, DeviceDB
from engine.audit_engine import AuditEngine
from services.notification_service import NotificationService
from utils.logger import setup_logger

logger = setup_logger(__name__)

class AuditService:
    """Service for audit execution and result management with database persistence"""

    def __init__(self, audit_engine: AuditEngine):
        self.audit_engine = audit_engine

    async def execute_audit(
        self,
        db: Session,
        devices: List[Device],
        rules: Optional[List[AuditRule]] = None
    ) -> List[AuditResult]:
        """Execute audit on multiple devices"""
        logger.info(f"Starting audit on {len(devices)} device(s)")

        # Run audits concurrently, passing db session for automatic backups
        tasks = [
            self.audit_engine.audit_device(device, rules, db)
            for device in devices
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Store successful results in database
        successful_results = []
        for result in results:
            if isinstance(result, AuditResult):
                # Store in database
                db_result = AuditResultDB(
                    device_id=result.device_id,
                    device_name=result.device_name,
                    timestamp=datetime.fromisoformat(result.timestamp) if isinstance(result.timestamp, str) else result.timestamp,
                    findings=[f.dict() for f in result.findings],
                    compliance=result.compliance,
                    status="completed"
                )
                db.add(db_result)

                # Update device last_audit and compliance
                device_db = db.query(DeviceDB).filter(DeviceDB.id == result.device_id).first()
                if device_db:
                    device_db.last_audit = datetime.utcnow()
                    device_db.compliance = result.compliance

                successful_results.append(result)
            else:
                logger.error(f"Audit failed with exception: {result}")

        db.commit()

        # Send notifications for audit results
        notification_tasks = []
        for result in successful_results:
            notification_tasks.append(
                NotificationService.notify_audit_result(db, result)
            )

        if notification_tasks:
            await asyncio.gather(*notification_tasks, return_exceptions=True)

        logger.info(f"Audit completed: {len(successful_results)}/{len(devices)} successful")
        return successful_results

    def get_all_results(self, db: Session) -> List[AuditResult]:
        """Get all audit results"""
        db_results = db.query(AuditResultDB).order_by(AuditResultDB.timestamp.desc()).all()
        return [self._to_pydantic(r) for r in db_results]

    def get_latest_result_by_device(self, db: Session, device_id: int) -> Optional[AuditResult]:
        """Get latest audit result for a device"""
        db_result = db.query(AuditResultDB)\
            .filter(AuditResultDB.device_id == device_id)\
            .order_by(AuditResultDB.timestamp.desc())\
            .first()
        return self._to_pydantic(db_result) if db_result else None

    def get_latest_results_per_device(self, db: Session) -> List[AuditResult]:
        """Get latest audit result for each device (scalable for many devices)"""
        from sqlalchemy import func

        # Subquery to get the latest timestamp per device
        latest_timestamps = db.query(
            AuditResultDB.device_id,
            func.max(AuditResultDB.timestamp).label('max_timestamp')
        ).group_by(AuditResultDB.device_id).subquery()

        # Join to get the full audit results for the latest timestamp per device
        latest_results = db.query(AuditResultDB).join(
            latest_timestamps,
            (AuditResultDB.device_id == latest_timestamps.c.device_id) &
            (AuditResultDB.timestamp == latest_timestamps.c.max_timestamp)
        ).order_by(AuditResultDB.timestamp.desc()).all()

        return [self._to_pydantic(r) for r in latest_results]

    def get_results_by_device(self, db: Session, device_id: int) -> List[AuditResult]:
        """Get all audit results for a device"""
        db_results = db.query(AuditResultDB)\
            .filter(AuditResultDB.device_id == device_id)\
            .order_by(AuditResultDB.timestamp.desc())\
            .all()
        return [self._to_pydantic(r) for r in db_results]

    def get_compliance_summary(self, db: Session) -> Dict[str, Any]:
        """Get overall compliance summary"""
        # Get latest result per device using subquery
        from sqlalchemy import func
        from sqlalchemy.sql import exists

        # Get all devices with their latest audit results
        latest_results_subquery = db.query(
            AuditResultDB.device_id,
            func.max(AuditResultDB.timestamp).label('max_timestamp')
        ).group_by(AuditResultDB.device_id).subquery()

        latest_results = db.query(AuditResultDB).join(
            latest_results_subquery,
            (AuditResultDB.device_id == latest_results_subquery.c.device_id) &
            (AuditResultDB.timestamp == latest_results_subquery.c.max_timestamp)
        ).all()

        if not latest_results:
            return {
                "overall_compliance": 0,
                "total_devices": db.query(DeviceDB).count(),
                "audited_devices": 0,
                "critical_issues": 0,
                "by_category": {},
                "by_severity": {}
            }

        # Calculate overall compliance
        overall_compliance = (
            int(sum(r.compliance for r in latest_results) / len(latest_results))
            if latest_results else 0
        )

        # Count critical issues
        critical_issues = 0
        for result in latest_results:
            for finding in result.findings:
                if finding.get('status') == 'fail' and finding.get('severity') == 'critical':
                    critical_issues += 1

        # Group by severity
        by_severity = {
            "critical": {"total": 0, "failed": 0},
            "high": {"total": 0, "failed": 0},
            "medium": {"total": 0, "failed": 0},
            "low": {"total": 0, "failed": 0}
        }

        for result in latest_results:
            for finding in result.findings:
                severity = finding.get('severity', 'medium')
                status = finding.get('status', 'unknown')
                if severity in by_severity:
                    by_severity[severity]["total"] += 1
                    if status == 'fail':
                        by_severity[severity]["failed"] += 1

        return {
            "overall_compliance": overall_compliance,
            "total_devices": db.query(DeviceDB).count(),
            "audited_devices": len(latest_results),
            "critical_issues": critical_issues,
            "by_category": {},
            "by_severity": by_severity
        }

    def clear_old_results(self, db: Session, days: int = 30) -> int:
        """Clear audit results older than specified days"""
        cutoff = datetime.utcnow() - timedelta(days=days)

        deleted = db.query(AuditResultDB)\
            .filter(AuditResultDB.timestamp < cutoff)\
            .delete()

        db.commit()

        logger.info(f"Cleared {deleted} old audit results")
        return deleted

    def _to_pydantic(self, db_result: AuditResultDB) -> AuditResult:
        """Convert SQLAlchemy model to Pydantic model"""
        # Convert findings from dict to AuditFinding objects
        findings = [AuditFinding(**f) for f in db_result.findings]

        # Get device IP from the device relationship
        device_ip = db_result.device.ip if db_result.device else None

        return AuditResult(
            device_id=db_result.device_id,
            device_name=db_result.device_name,
            device_ip=device_ip,
            timestamp=db_result.timestamp.isoformat() if db_result.timestamp else datetime.utcnow().isoformat(),
            findings=findings,
            compliance=int(db_result.compliance)
        )
