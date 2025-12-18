# ============================================================================
# services/scheduler.py
# Background Job Scheduler for ML Analytics
# ============================================================================

import logging
import asyncio
from datetime import datetime
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session
import httpx

from shared.database import SessionLocal
from services.ml_engine import ml_engine
from services.analytics_service import AnalyticsService

logger = logging.getLogger(__name__)


class AnalyticsScheduler:
    """
    Background scheduler for automated ML analytics tasks

    Schedules:
    - Compliance snapshots: Every 4 hours
    - ML forecasting: Daily at 2 AM
    - Anomaly detection: Every 2 hours
    - Risk scoring: Every 6 hours
    - Insight generation: Daily at 3 AM
    """

    DEVICE_SERVICE_URL = "http://device-service:3001"
    RULE_SERVICE_URL = "http://rule-service:3002"

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.is_running = False

    def start(self):
        """Start the background scheduler"""
        if self.is_running:
            logger.warning("Scheduler already running")
            return

        # Schedule compliance snapshot collection (every 4 hours)
        self.scheduler.add_job(
            self._run_compliance_snapshot,
            IntervalTrigger(hours=4),
            id="compliance_snapshot",
            name="Compliance Snapshot Collection",
            replace_existing=True,
            max_instances=1
        )

        # Schedule ML forecasting (daily at 2 AM)
        self.scheduler.add_job(
            self._run_forecasting,
            CronTrigger(hour=2, minute=0),
            id="ml_forecasting",
            name="ML Compliance Forecasting",
            replace_existing=True,
            max_instances=1
        )

        # Schedule anomaly detection (every 2 hours)
        self.scheduler.add_job(
            self._run_anomaly_detection,
            IntervalTrigger(hours=2),
            id="anomaly_detection",
            name="ML Anomaly Detection",
            replace_existing=True,
            max_instances=1
        )

        # Schedule device risk scoring (every 6 hours)
        self.scheduler.add_job(
            self._run_risk_scoring,
            IntervalTrigger(hours=6),
            id="risk_scoring",
            name="Device Risk Scoring",
            replace_existing=True,
            max_instances=1
        )

        # Schedule insight generation (daily at 3 AM)
        self.scheduler.add_job(
            self._run_insight_generation,
            CronTrigger(hour=3, minute=0),
            id="insight_generation",
            name="ML Insight Generation",
            replace_existing=True,
            max_instances=1
        )

        self.scheduler.start()
        self.is_running = True
        logger.info("Analytics scheduler started with 5 scheduled jobs")

    def stop(self):
        """Stop the background scheduler"""
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("Analytics scheduler stopped")

    def get_job_status(self) -> dict:
        """Get status of all scheduled jobs"""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "pending": job.pending
            })
        return {
            "scheduler_running": self.is_running,
            "jobs": jobs
        }

    async def run_job_now(self, job_id: str) -> dict:
        """Manually trigger a job to run immediately"""
        job_map = {
            "compliance_snapshot": self._run_compliance_snapshot,
            "ml_forecasting": self._run_forecasting,
            "anomaly_detection": self._run_anomaly_detection,
            "risk_scoring": self._run_risk_scoring,
            "insight_generation": self._run_insight_generation
        }

        if job_id not in job_map:
            raise ValueError(f"Unknown job ID: {job_id}")

        logger.info(f"Manually triggering job: {job_id}")
        result = await job_map[job_id]()
        return result

    # =========================================================================
    # Job Implementations
    # =========================================================================

    async def _run_compliance_snapshot(self) -> dict:
        """Create compliance snapshot from current audit data"""
        logger.info("Running scheduled compliance snapshot...")
        start_time = datetime.utcnow()

        db = SessionLocal()
        try:
            snapshot = await AnalyticsService.create_snapshot(db)

            result = {
                "job": "compliance_snapshot",
                "status": "success",
                "timestamp": start_time.isoformat(),
                "snapshot_id": snapshot.id if snapshot else None,
                "compliance": snapshot.overall_compliance if snapshot else None
            }
            logger.info(f"Compliance snapshot created: {snapshot.overall_compliance:.1f}%")

        except Exception as e:
            logger.error(f"Compliance snapshot failed: {e}")
            result = {
                "job": "compliance_snapshot",
                "status": "error",
                "timestamp": start_time.isoformat(),
                "error": str(e)
            }
        finally:
            db.close()

        return result

    async def _run_forecasting(self) -> dict:
        """Run ML compliance forecasting"""
        logger.info("Running scheduled ML forecasting...")
        start_time = datetime.utcnow()

        db = SessionLocal()
        try:
            forecasts = ml_engine.forecast_compliance(db, days_ahead=14)

            result = {
                "job": "ml_forecasting",
                "status": "success",
                "timestamp": start_time.isoformat(),
                "forecasts_generated": len(forecasts)
            }
            logger.info(f"Generated {len(forecasts)} forecasts")

        except Exception as e:
            logger.error(f"ML forecasting failed: {e}")
            result = {
                "job": "ml_forecasting",
                "status": "error",
                "timestamp": start_time.isoformat(),
                "error": str(e)
            }
        finally:
            db.close()

        return result

    async def _run_anomaly_detection(self) -> dict:
        """Run ML anomaly detection"""
        logger.info("Running scheduled anomaly detection...")
        start_time = datetime.utcnow()

        db = SessionLocal()
        try:
            anomalies = ml_engine.detect_anomalies(db)

            result = {
                "job": "anomaly_detection",
                "status": "success",
                "timestamp": start_time.isoformat(),
                "anomalies_detected": len(anomalies)
            }
            logger.info(f"Detected {len(anomalies)} anomalies")

        except Exception as e:
            logger.error(f"Anomaly detection failed: {e}")
            result = {
                "job": "anomaly_detection",
                "status": "error",
                "timestamp": start_time.isoformat(),
                "error": str(e)
            }
        finally:
            db.close()

        return result

    async def _run_risk_scoring(self) -> dict:
        """Calculate risk scores for all devices"""
        logger.info("Running scheduled risk scoring...")
        start_time = datetime.utcnow()

        db = SessionLocal()
        try:
            # Fetch device data from device service
            device_data = await self._fetch_device_data()

            if device_data:
                risk_scores = ml_engine.calculate_risk_scores(db, device_data)

                result = {
                    "job": "risk_scoring",
                    "status": "success",
                    "timestamp": start_time.isoformat(),
                    "devices_scored": len(risk_scores),
                    "high_risk_count": sum(1 for r in risk_scores if r['risk_level'] in ['high', 'critical'])
                }
                logger.info(f"Calculated risk scores for {len(risk_scores)} devices")
            else:
                result = {
                    "job": "risk_scoring",
                    "status": "success",
                    "timestamp": start_time.isoformat(),
                    "devices_scored": 0,
                    "message": "No device data available"
                }

        except Exception as e:
            logger.error(f"Risk scoring failed: {e}")
            result = {
                "job": "risk_scoring",
                "status": "error",
                "timestamp": start_time.isoformat(),
                "error": str(e)
            }
        finally:
            db.close()

        return result

    async def _run_insight_generation(self) -> dict:
        """Generate ML-powered insights"""
        logger.info("Running scheduled insight generation...")
        start_time = datetime.utcnow()

        db = SessionLocal()
        try:
            insights = ml_engine.generate_insights(db)

            result = {
                "job": "insight_generation",
                "status": "success",
                "timestamp": start_time.isoformat(),
                "insights_generated": len(insights),
                "actionable_count": sum(1 for i in insights if i.get('actionable', False))
            }
            logger.info(f"Generated {len(insights)} insights")

        except Exception as e:
            logger.error(f"Insight generation failed: {e}")
            result = {
                "job": "insight_generation",
                "status": "error",
                "timestamp": start_time.isoformat(),
                "error": str(e)
            }
        finally:
            db.close()

        return result

    # =========================================================================
    # Data Fetching
    # =========================================================================

    async def _fetch_device_data(self) -> list:
        """Fetch device data from device service with audit results"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Get devices
                response = await client.get(f"{self.DEVICE_SERVICE_URL}/devices")
                response.raise_for_status()
                devices = response.json()

                # Get audit results
                audit_response = await client.get(f"{self.RULE_SERVICE_URL}/audit/results")
                audit_response.raise_for_status()
                audit_results = audit_response.json()

                # Build device data with audit info
                audit_by_device = {}
                for result in audit_results:
                    device_id = result.get('device_id')
                    if device_id:
                        audit_by_device[device_id] = result

                device_data = []
                for device in devices:
                    device_id = device.get('id')
                    audit = audit_by_device.get(device_id, {})
                    findings = audit.get('findings', [])

                    device_data.append({
                        'id': device_id,
                        'compliance': audit.get('compliance', 100),
                        'health_check_failures': 1 if device.get('status') != 'active' else 0,
                        'config_changes': 0,  # Would need backup service integration
                        'days_since_audit': self._days_since(audit.get('timestamp')),
                        'critical_findings': sum(1 for f in findings if f.get('severity') == 'critical'),
                        'high_findings': sum(1 for f in findings if f.get('severity') == 'high'),
                        'vendor': device.get('vendor'),
                        'status': device.get('status')
                    })

                return device_data

        except Exception as e:
            logger.error(f"Failed to fetch device data: {e}")
            return []

    def _days_since(self, timestamp: Optional[str]) -> int:
        """Calculate days since a timestamp"""
        if not timestamp:
            return 30  # Default to 30 days if no audit
        try:
            audit_date = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            return (datetime.utcnow() - audit_date.replace(tzinfo=None)).days
        except:
            return 30


# Singleton instance
analytics_scheduler = AnalyticsScheduler()
