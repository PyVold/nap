# ============================================================================
# services/analytics_service.py - Analytics & Intelligence Service
# ============================================================================

from datetime import datetime, timedelta
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc
import statistics
import math

from db_models import (
    ComplianceTrendDB, ComplianceForecastDB, ComplianceAnomalyDB,
    AuditResultDB, DeviceDB
)
from models.enums import SeverityLevel


class AnalyticsService:
    """Service for analytics, forecasting, and anomaly detection"""

    @staticmethod
    async def create_snapshot(db: Session, device_id: Optional[int] = None) -> ComplianceTrendDB:
        """
        Create a compliance snapshot for trend analysis
        
        Args:
            db: Database session
            device_id: Specific device ID or None for overall snapshot
            
        Returns:
            Created trend snapshot
        """
        # Get the most recent audit results
        query = db.query(AuditResultDB)
        
        if device_id:
            query = query.filter(AuditResultDB.device_id == device_id)
            
        # Get latest result per device
        latest_results = query.order_by(
            AuditResultDB.device_id,
            desc(AuditResultDB.timestamp)
        ).all()
        
        # Group by device to get only the latest for each
        device_results = {}
        for result in latest_results:
            if result.device_id not in device_results:
                device_results[result.device_id] = result
        
        results = list(device_results.values())
        
        if not results:
            # Create empty snapshot if no data
            snapshot = ComplianceTrendDB(
                snapshot_date=datetime.utcnow(),
                device_id=device_id,
                overall_compliance=0.0,
                compliance_change=0.0,
                total_devices=0,
                compliant_devices=0,
                failed_devices=0,
                total_checks=0,
                passed_checks=0,
                failed_checks=0,
                warning_checks=0,
                critical_failures=0,
                high_failures=0,
                medium_failures=0,
                low_failures=0
            )
            db.add(snapshot)
            db.commit()
            db.refresh(snapshot)
            return snapshot
        
        # Calculate metrics
        total_devices = len(results)
        total_compliance = sum(r.compliance for r in results)
        overall_compliance = total_compliance / total_devices if total_devices > 0 else 0.0
        
        compliant_devices = sum(1 for r in results if r.compliance >= 90)
        failed_devices = sum(1 for r in results if r.compliance < 70)
        
        # Aggregate findings
        total_checks = 0
        passed_checks = 0
        failed_checks = 0
        warning_checks = 0
        critical_failures = 0
        high_failures = 0
        medium_failures = 0
        low_failures = 0
        
        for result in results:
            if result.findings:
                for finding in result.findings:
                    total_checks += 1
                    status = finding.get('status', 'unknown')
                    severity = finding.get('severity', 'medium')
                    
                    if status == 'pass':
                        passed_checks += 1
                    elif status == 'fail':
                        failed_checks += 1
                        if severity == 'critical':
                            critical_failures += 1
                        elif severity == 'high':
                            high_failures += 1
                        elif severity == 'medium':
                            medium_failures += 1
                        elif severity == 'low':
                            low_failures += 1
                    elif status == 'warning':
                        warning_checks += 1
        
        # Get previous snapshot for comparison
        prev_query = db.query(ComplianceTrendDB)
        if device_id:
            prev_query = prev_query.filter(ComplianceTrendDB.device_id == device_id)
        else:
            prev_query = prev_query.filter(ComplianceTrendDB.device_id.is_(None))
            
        prev_snapshot = prev_query.order_by(desc(ComplianceTrendDB.snapshot_date)).first()
        
        compliance_change = 0.0
        if prev_snapshot:
            compliance_change = overall_compliance - prev_snapshot.overall_compliance
        
        # Create snapshot
        snapshot = ComplianceTrendDB(
            snapshot_date=datetime.utcnow(),
            device_id=device_id,
            overall_compliance=overall_compliance,
            compliance_change=compliance_change,
            total_devices=total_devices,
            compliant_devices=compliant_devices,
            failed_devices=failed_devices,
            total_checks=total_checks,
            passed_checks=passed_checks,
            failed_checks=failed_checks,
            warning_checks=warning_checks,
            critical_failures=critical_failures,
            high_failures=high_failures,
            medium_failures=medium_failures,
            low_failures=low_failures
        )
        
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)
        
        return snapshot

    @staticmethod
    async def get_trends(
        db: Session,
        device_id: Optional[int] = None,
        days: int = 7
    ) -> List[ComplianceTrendDB]:
        """
        Get compliance trends
        
        Args:
            db: Database session
            device_id: Filter by device ID
            days: Number of days to look back
            
        Returns:
            List of trend snapshots
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        query = db.query(ComplianceTrendDB).filter(
            ComplianceTrendDB.snapshot_date >= cutoff
        )
        
        if device_id:
            query = query.filter(ComplianceTrendDB.device_id == device_id)
        else:
            query = query.filter(ComplianceTrendDB.device_id.is_(None))
            
        return query.order_by(ComplianceTrendDB.snapshot_date).all()

    @staticmethod
    async def generate_forecast(
        db: Session,
        device_id: Optional[int] = None,
        days_ahead: int = 7
    ) -> List[ComplianceForecastDB]:
        """
        Generate compliance forecast using simple linear regression
        
        Args:
            db: Database session
            device_id: Device to forecast (None for overall)
            days_ahead: Days to forecast into the future
            
        Returns:
            List of forecast records
        """
        # Get historical trends (last 30 days minimum)
        cutoff = datetime.utcnow() - timedelta(days=30)
        query = db.query(ComplianceTrendDB).filter(
            ComplianceTrendDB.snapshot_date >= cutoff
        )
        
        if device_id:
            query = query.filter(ComplianceTrendDB.device_id == device_id)
        else:
            query = query.filter(ComplianceTrendDB.device_id.is_(None))
            
        trends = query.order_by(ComplianceTrendDB.snapshot_date).all()
        
        if len(trends) < 2:
            # Not enough data for forecasting
            return []
        
        # Prepare data for linear regression
        x_values = []
        y_values = []
        base_date = trends[0].snapshot_date
        
        for trend in trends:
            days_diff = (trend.snapshot_date - base_date).days
            x_values.append(days_diff)
            y_values.append(trend.overall_compliance)
        
        # Calculate linear regression: y = mx + b
        n = len(x_values)
        sum_x = sum(x_values)
        sum_y = sum(y_values)
        sum_xy = sum(x * y for x, y in zip(x_values, y_values))
        sum_xx = sum(x * x for x in x_values)
        
        # Calculate slope (m) and intercept (b)
        if n * sum_xx - sum_x * sum_x == 0:
            # Avoid division by zero
            m = 0
        else:
            m = (n * sum_xy - sum_x * sum_y) / (n * sum_xx - sum_x * sum_x)
        b = (sum_y - m * sum_x) / n
        
        # Calculate R-squared for confidence
        y_mean = sum_y / n
        ss_tot = sum((y - y_mean) ** 2 for y in y_values)
        ss_res = sum((y - (m * x + b)) ** 2 for x, y in zip(x_values, y_values))
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        confidence = max(0.0, min(1.0, r_squared))  # Clamp between 0 and 1
        
        # Generate forecasts
        forecasts = []
        current_date = datetime.utcnow()
        
        for day in range(1, days_ahead + 1):
            forecast_date = current_date + timedelta(days=day)
            days_from_base = (forecast_date - base_date).days
            predicted_compliance = m * days_from_base + b
            
            # Clamp prediction between 0 and 100
            predicted_compliance = max(0.0, min(100.0, predicted_compliance))
            
            # Estimate predicted failures based on compliance
            predicted_failures = int((100 - predicted_compliance) / 10) if predicted_compliance < 100 else 0
            
            forecast = ComplianceForecastDB(
                forecast_date=forecast_date,
                device_id=device_id,
                predicted_compliance=predicted_compliance,
                confidence_score=confidence,
                predicted_failures=predicted_failures,
                training_data_points=n
            )
            
            db.add(forecast)
            forecasts.append(forecast)
        
        db.commit()
        
        return forecasts

    @staticmethod
    async def get_forecasts(
        db: Session,
        device_id: Optional[int] = None
    ) -> List[ComplianceForecastDB]:
        """Get existing forecasts"""
        query = db.query(ComplianceForecastDB)
        
        if device_id:
            query = query.filter(ComplianceForecastDB.device_id == device_id)
        else:
            query = query.filter(ComplianceForecastDB.device_id.is_(None))
            
        # Only return future forecasts
        query = query.filter(ComplianceForecastDB.forecast_date >= datetime.utcnow())
        
        return query.order_by(ComplianceForecastDB.forecast_date).all()

    @staticmethod
    async def detect_anomalies(db: Session, device_id: Optional[int] = None) -> List[ComplianceAnomalyDB]:
        """
        Detect anomalies using statistical analysis (Z-score method)
        
        Args:
            db: Database session
            device_id: Device to analyze (None for all devices)
            
        Returns:
            List of detected anomalies
        """
        # Get historical trends (last 30 days)
        cutoff = datetime.utcnow() - timedelta(days=30)
        query = db.query(ComplianceTrendDB).filter(
            ComplianceTrendDB.snapshot_date >= cutoff
        )
        
        if device_id:
            query = query.filter(ComplianceTrendDB.device_id == device_id)
        else:
            query = query.filter(ComplianceTrendDB.device_id.is_(None))
            
        trends = query.order_by(ComplianceTrendDB.snapshot_date).all()
        
        if len(trends) < 5:
            # Not enough data for anomaly detection
            return []
        
        # Calculate statistics
        compliance_values = [t.overall_compliance for t in trends]
        mean = statistics.mean(compliance_values)
        stdev = statistics.stdev(compliance_values) if len(compliance_values) > 1 else 0
        
        anomalies = []
        
        # Check last few snapshots for anomalies
        for trend in trends[-3:]:  # Check last 3 snapshots
            z_score = 0
            if stdev > 0:
                z_score = (trend.overall_compliance - mean) / stdev
            
            # Detect significant drops (z-score < -2)
            if z_score < -2:
                severity = SeverityLevel.CRITICAL if z_score < -3 else SeverityLevel.HIGH
                
                # Check if anomaly already exists
                existing = db.query(ComplianceAnomalyDB).filter(
                    ComplianceAnomalyDB.device_id == device_id,
                    ComplianceAnomalyDB.detected_at >= trend.snapshot_date - timedelta(hours=1),
                    ComplianceAnomalyDB.detected_at <= trend.snapshot_date + timedelta(hours=1)
                ).first()
                
                if not existing:
                    anomaly = ComplianceAnomalyDB(
                        device_id=device_id,
                        detected_at=trend.snapshot_date,
                        anomaly_type="compliance_drop",
                        severity=severity,
                        description=f"Compliance dropped to {trend.overall_compliance:.1f}%, significantly below the {mean:.1f}% average (Z-score: {z_score:.2f})",
                        z_score=z_score,
                        expected_value=mean,
                        actual_value=trend.overall_compliance
                    )
                    db.add(anomaly)
                    anomalies.append(anomaly)
            
            # Detect sudden spikes in failures
            if trend.critical_failures > 0 or trend.high_failures > 5:
                failure_count = trend.critical_failures + trend.high_failures
                avg_failures = sum(t.critical_failures + t.high_failures for t in trends) / len(trends)
                
                if failure_count > avg_failures * 2:  # More than 2x average
                    existing = db.query(ComplianceAnomalyDB).filter(
                        ComplianceAnomalyDB.device_id == device_id,
                        ComplianceAnomalyDB.anomaly_type == "spike_failures",
                        ComplianceAnomalyDB.detected_at >= trend.snapshot_date - timedelta(hours=1)
                    ).first()
                    
                    if not existing:
                        anomaly = ComplianceAnomalyDB(
                            device_id=device_id,
                            detected_at=trend.snapshot_date,
                            anomaly_type="spike_failures",
                            severity=SeverityLevel.HIGH,
                            description=f"Unusual spike in failures: {failure_count} high-severity failures detected (avg: {avg_failures:.1f})",
                            expected_value=avg_failures,
                            actual_value=float(failure_count)
                        )
                        db.add(anomaly)
                        anomalies.append(anomaly)
        
        db.commit()
        return anomalies

    @staticmethod
    async def get_anomalies(
        db: Session,
        device_id: Optional[int] = None,
        acknowledged: Optional[bool] = None
    ) -> List[ComplianceAnomalyDB]:
        """Get detected anomalies"""
        query = db.query(ComplianceAnomalyDB)
        
        if device_id:
            query = query.filter(ComplianceAnomalyDB.device_id == device_id)
        
        if acknowledged is not None:
            query = query.filter(ComplianceAnomalyDB.acknowledged == acknowledged)
        
        return query.order_by(desc(ComplianceAnomalyDB.detected_at)).all()

    @staticmethod
    async def acknowledge_anomaly(
        db: Session,
        anomaly_id: int,
        acknowledged_by: str,
        notes: Optional[str] = None
    ) -> ComplianceAnomalyDB:
        """Acknowledge an anomaly"""
        anomaly = db.query(ComplianceAnomalyDB).filter(
            ComplianceAnomalyDB.id == anomaly_id
        ).first()
        
        if not anomaly:
            raise ValueError(f"Anomaly {anomaly_id} not found")
        
        anomaly.acknowledged = True
        anomaly.acknowledged_by = acknowledged_by
        anomaly.acknowledged_at = datetime.utcnow()
        if notes:
            anomaly.resolution_notes = notes
        
        db.commit()
        db.refresh(anomaly)
        
        return anomaly

    @staticmethod
    async def get_dashboard_summary(db: Session) -> Dict:
        """Get analytics dashboard summary"""
        # Recent anomalies (last 7 days)
        recent_cutoff = datetime.utcnow() - timedelta(days=7)
        recent_anomalies = db.query(func.count(ComplianceAnomalyDB.id)).filter(
            ComplianceAnomalyDB.detected_at >= recent_cutoff,
            ComplianceAnomalyDB.acknowledged == False
        ).scalar() or 0
        
        # Average compliance (last 7 days)
        week_cutoff = datetime.utcnow() - timedelta(days=7)
        avg_compliance_result = db.query(
            func.avg(ComplianceTrendDB.overall_compliance)
        ).filter(
            ComplianceTrendDB.snapshot_date >= week_cutoff,
            ComplianceTrendDB.device_id.is_(None)  # Overall trends only
        ).scalar()
        
        average_compliance_7d = float(avg_compliance_result) if avg_compliance_result else 0.0
        
        # Devices at risk (compliance < 70%)
        latest_results = db.query(AuditResultDB).order_by(
            AuditResultDB.device_id,
            desc(AuditResultDB.timestamp)
        ).all()
        
        device_results = {}
        for result in latest_results:
            if result.device_id not in device_results:
                device_results[result.device_id] = result
        
        devices_at_risk = sum(1 for r in device_results.values() if r.compliance < 70)
        
        # Total trends
        total_trends = db.query(func.count(ComplianceTrendDB.id)).scalar() or 0
        
        return {
            "recent_anomalies": recent_anomalies,
            "average_compliance_7d": average_compliance_7d,
            "devices_at_risk": devices_at_risk,
            "total_trends": total_trends
        }
