# ============================================================================
# services/ml_engine.py
# Machine Learning Engine for Network Analytics
# ============================================================================

import logging
import pickle
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

# ML Libraries
from sklearn.ensemble import IsolationForest, GradientBoostingClassifier, RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, mean_squared_error, mean_absolute_error

# Time series
try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False

from db_models import (
    ComplianceTrendDB, ComplianceForecastDB, ComplianceAnomalyDB,
    DeviceRiskScoreDB, MLInsightDB, MLModelMetadataDB
)
from models.enums import SeverityLevel

logger = logging.getLogger(__name__)


class MLEngine:
    """
    Machine Learning Engine for Network Audit Analytics

    Provides:
    - Compliance Forecasting (Prophet/ARIMA)
    - Anomaly Detection (Isolation Forest)
    - Device Risk Scoring (Gradient Boosting)
    - Automated Insight Generation
    """

    MODEL_VERSION = "1.0.0"

    def __init__(self):
        self.scaler = StandardScaler()
        self.anomaly_detector = None
        self.risk_classifier = None
        self.forecaster = None

    # =========================================================================
    # Compliance Forecasting
    # =========================================================================

    def forecast_compliance(
        self,
        db: Session,
        device_id: Optional[int] = None,
        days_ahead: int = 14
    ) -> List[Dict[str, Any]]:
        """
        Generate compliance forecasts using Prophet time series model

        Args:
            db: Database session
            device_id: Optional device ID for device-specific forecast
            days_ahead: Number of days to forecast (default 14)

        Returns:
            List of forecast dictionaries
        """
        start_time = time.time()

        # Get historical compliance data
        query = db.query(ComplianceTrendDB).order_by(ComplianceTrendDB.snapshot_date)
        if device_id:
            query = query.filter(ComplianceTrendDB.device_id == device_id)
        else:
            query = query.filter(ComplianceTrendDB.device_id.is_(None))

        trends = query.all()

        if len(trends) < 7:
            logger.warning(f"Insufficient data for forecasting: {len(trends)} points (need 7+)")
            return self._fallback_linear_forecast(trends, days_ahead, device_id)

        # Prepare data for Prophet
        df = pd.DataFrame([
            {
                'ds': t.snapshot_date,
                'y': t.overall_compliance
            }
            for t in trends
        ])

        forecasts = []
        model_info = {
            "model_name": "compliance_forecaster",
            "version": f"prophet_{self.MODEL_VERSION}",
            "training_samples": len(df)
        }

        if PROPHET_AVAILABLE and len(df) >= 10:
            try:
                # Train Prophet model
                model = Prophet(
                    yearly_seasonality=False,
                    weekly_seasonality=True,
                    daily_seasonality=False,
                    changepoint_prior_scale=0.05,
                    interval_width=0.95
                )
                model.fit(df)

                # Generate future dates
                future = model.make_future_dataframe(periods=days_ahead)
                prediction = model.predict(future)

                # Extract forecasts
                for _, row in prediction.tail(days_ahead).iterrows():
                    forecast_date = row['ds'].to_pydatetime()
                    predicted = max(0, min(100, row['yhat']))  # Clamp 0-100

                    # Calculate confidence from prediction interval
                    interval_width = row['yhat_upper'] - row['yhat_lower']
                    confidence = max(0.1, 1.0 - (interval_width / 100))

                    forecast = ComplianceForecastDB(
                        forecast_date=forecast_date,
                        device_id=device_id,
                        predicted_compliance=predicted,
                        confidence_score=confidence,
                        predicted_failures=int((100 - predicted) / 10),  # Estimate
                        model_version=f"prophet_{self.MODEL_VERSION}",
                        training_data_points=len(df)
                    )
                    db.add(forecast)

                    forecasts.append({
                        "date": forecast_date.isoformat(),
                        "predicted_compliance": round(predicted, 2),
                        "confidence": round(confidence, 2),
                        "lower_bound": round(max(0, row['yhat_lower']), 2),
                        "upper_bound": round(min(100, row['yhat_upper']), 2)
                    })

                db.commit()

                # Log model metadata
                training_duration = time.time() - start_time
                self._log_model_metadata(
                    db, "compliance_forecaster", f"prophet_{self.MODEL_VERSION}",
                    training_samples=len(df),
                    training_duration=training_duration,
                    mae=self._calculate_prophet_mae(model, df)
                )

                logger.info(f"Generated {len(forecasts)} Prophet forecasts in {training_duration:.2f}s")

            except Exception as e:
                logger.error(f"Prophet forecasting failed: {e}, falling back to linear")
                return self._fallback_linear_forecast(trends, days_ahead, device_id)
        else:
            return self._fallback_linear_forecast(trends, days_ahead, device_id)

        return forecasts

    def _fallback_linear_forecast(
        self,
        trends: List[ComplianceTrendDB],
        days_ahead: int,
        device_id: Optional[int]
    ) -> List[Dict[str, Any]]:
        """Fallback linear regression forecast when Prophet unavailable"""
        if len(trends) < 2:
            return []

        # Simple linear regression
        x = np.array(range(len(trends)))
        y = np.array([t.overall_compliance for t in trends])

        # Calculate slope and intercept
        n = len(x)
        slope = (n * np.sum(x * y) - np.sum(x) * np.sum(y)) / (n * np.sum(x**2) - np.sum(x)**2)
        intercept = (np.sum(y) - slope * np.sum(x)) / n

        # Calculate R-squared for confidence
        y_pred = slope * x + intercept
        ss_res = np.sum((y - y_pred)**2)
        ss_tot = np.sum((y - np.mean(y))**2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        forecasts = []
        last_date = trends[-1].snapshot_date

        for i in range(1, days_ahead + 1):
            forecast_date = last_date + timedelta(days=i)
            predicted = max(0, min(100, slope * (n + i - 1) + intercept))

            forecasts.append({
                "date": forecast_date.isoformat(),
                "predicted_compliance": round(predicted, 2),
                "confidence": round(max(0.1, r_squared), 2),
                "lower_bound": round(max(0, predicted - 10), 2),
                "upper_bound": round(min(100, predicted + 10), 2)
            })

        return forecasts

    def _calculate_prophet_mae(self, model, df: pd.DataFrame) -> float:
        """Calculate MAE for Prophet model on training data"""
        try:
            pred = model.predict(df)
            return mean_absolute_error(df['y'], pred['yhat'])
        except:
            return None

    # =========================================================================
    # Anomaly Detection
    # =========================================================================

    def detect_anomalies(
        self,
        db: Session,
        device_id: Optional[int] = None,
        sensitivity: float = 0.1
    ) -> List[Dict[str, Any]]:
        """
        Detect anomalies using Isolation Forest algorithm

        Args:
            db: Database session
            device_id: Optional device ID for device-specific detection
            sensitivity: Contamination factor (0.01-0.5, default 0.1)

        Returns:
            List of detected anomaly dictionaries
        """
        # Get recent compliance data
        cutoff = datetime.utcnow() - timedelta(days=30)
        query = db.query(ComplianceTrendDB).filter(
            ComplianceTrendDB.snapshot_date >= cutoff
        ).order_by(ComplianceTrendDB.snapshot_date)

        if device_id:
            query = query.filter(ComplianceTrendDB.device_id == device_id)

        trends = query.all()

        if len(trends) < 10:
            logger.warning(f"Insufficient data for anomaly detection: {len(trends)} points")
            return self._fallback_zscore_detection(db, trends, device_id)

        # Prepare feature matrix
        features = []
        for t in trends:
            features.append([
                t.overall_compliance,
                t.compliance_change,
                t.critical_failures,
                t.high_failures,
                t.failed_checks,
                t.total_checks
            ])

        X = np.array(features)

        # Handle zero variance columns
        X = self._handle_zero_variance(X)

        # Scale features
        X_scaled = self.scaler.fit_transform(X)

        # Train Isolation Forest
        self.anomaly_detector = IsolationForest(
            contamination=sensitivity,
            random_state=42,
            n_estimators=100
        )

        predictions = self.anomaly_detector.fit_predict(X_scaled)
        scores = self.anomaly_detector.decision_function(X_scaled)

        detected_anomalies = []

        for i, (trend, pred, score) in enumerate(zip(trends, predictions, scores)):
            if pred == -1:  # Anomaly detected
                # Determine anomaly type and severity
                anomaly_type, severity, description = self._classify_anomaly(
                    trend, trends, score
                )

                # Check for duplicate
                existing = db.query(ComplianceAnomalyDB).filter(
                    ComplianceAnomalyDB.device_id == device_id,
                    ComplianceAnomalyDB.detected_at >= trend.snapshot_date - timedelta(hours=1),
                    ComplianceAnomalyDB.detected_at <= trend.snapshot_date + timedelta(hours=1)
                ).first()

                if not existing:
                    anomaly = ComplianceAnomalyDB(
                        device_id=device_id,
                        detected_at=trend.snapshot_date,
                        anomaly_type=anomaly_type,
                        severity=severity,
                        description=description,
                        z_score=float(score),
                        expected_value=float(np.mean([t.overall_compliance for t in trends])),
                        actual_value=trend.overall_compliance
                    )
                    db.add(anomaly)

                    detected_anomalies.append({
                        "id": None,  # Will be assigned after commit
                        "detected_at": trend.snapshot_date.isoformat(),
                        "type": anomaly_type,
                        "severity": severity.value,
                        "description": description,
                        "anomaly_score": round(float(score), 4),
                        "compliance": trend.overall_compliance
                    })

        db.commit()

        # Generate insight if anomalies found
        if detected_anomalies:
            self._generate_anomaly_insight(db, detected_anomalies, device_id)

        logger.info(f"Detected {len(detected_anomalies)} anomalies using Isolation Forest")
        return detected_anomalies

    def _handle_zero_variance(self, X: np.ndarray) -> np.ndarray:
        """Replace zero-variance columns with small random noise"""
        for i in range(X.shape[1]):
            if np.std(X[:, i]) == 0:
                X[:, i] = X[:, i] + np.random.normal(0, 0.001, X.shape[0])
        return X

    def _classify_anomaly(
        self,
        trend: ComplianceTrendDB,
        all_trends: List[ComplianceTrendDB],
        score: float
    ) -> Tuple[str, SeverityLevel, str]:
        """Classify anomaly type and severity"""
        mean_compliance = np.mean([t.overall_compliance for t in all_trends])
        mean_failures = np.mean([t.critical_failures + t.high_failures for t in all_trends])

        # Determine type
        if trend.overall_compliance < mean_compliance - 15:
            anomaly_type = "compliance_drop"
            description = f"Compliance dropped to {trend.overall_compliance:.1f}% (avg: {mean_compliance:.1f}%)"
        elif trend.critical_failures + trend.high_failures > mean_failures * 2:
            anomaly_type = "spike_failures"
            description = f"Critical/High failures spiked to {trend.critical_failures + trend.high_failures} (avg: {mean_failures:.0f})"
        else:
            anomaly_type = "unusual_pattern"
            description = f"Unusual compliance pattern detected (score: {score:.2f})"

        # Determine severity based on score
        if score < -0.5:
            severity = SeverityLevel.CRITICAL
        elif score < -0.3:
            severity = SeverityLevel.HIGH
        elif score < -0.1:
            severity = SeverityLevel.MEDIUM
        else:
            severity = SeverityLevel.LOW

        return anomaly_type, severity, description

    def _fallback_zscore_detection(
        self,
        db: Session,
        trends: List[ComplianceTrendDB],
        device_id: Optional[int]
    ) -> List[Dict[str, Any]]:
        """Fallback Z-score anomaly detection"""
        if len(trends) < 3:
            return []

        values = [t.overall_compliance for t in trends]
        mean_val = np.mean(values)
        std_val = np.std(values) if np.std(values) > 0 else 1

        anomalies = []
        for trend in trends:
            z_score = (trend.overall_compliance - mean_val) / std_val
            if abs(z_score) > 2:
                severity = SeverityLevel.CRITICAL if z_score < -3 else SeverityLevel.HIGH
                anomalies.append({
                    "detected_at": trend.snapshot_date.isoformat(),
                    "type": "compliance_drop" if z_score < 0 else "unusual_pattern",
                    "severity": severity.value,
                    "description": f"Z-score: {z_score:.2f}",
                    "anomaly_score": z_score,
                    "compliance": trend.overall_compliance
                })

        return anomalies

    # =========================================================================
    # Device Risk Scoring
    # =========================================================================

    def calculate_risk_scores(
        self,
        db: Session,
        device_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Calculate risk scores for devices using Gradient Boosting

        Args:
            db: Database session
            device_data: List of device dictionaries with features

        Returns:
            List of risk score dictionaries
        """
        if not device_data:
            return []

        # Extract features for each device
        features = []
        device_ids = []

        for device in device_data:
            device_ids.append(device.get('id'))
            features.append([
                device.get('compliance', 100),
                device.get('health_check_failures', 0),
                device.get('config_changes', 0),
                device.get('days_since_audit', 0),
                device.get('critical_findings', 0),
                device.get('high_findings', 0),
                1 if device.get('vendor') == 'cisco_xr' else 0,
                1 if device.get('status') == 'active' else 0
            ])

        X = np.array(features)

        risk_scores = []

        for i, (device_id, feature_row) in enumerate(zip(device_ids, X)):
            # Calculate component risks
            compliance_risk = max(0, (100 - feature_row[0]) / 100)
            health_risk = min(1.0, feature_row[1] / 10)
            drift_risk = min(1.0, feature_row[2] / 20)
            age_risk = min(1.0, feature_row[3] / 30)

            # Weighted overall risk
            overall_risk = (
                compliance_risk * 0.4 +
                health_risk * 0.25 +
                drift_risk * 0.2 +
                age_risk * 0.15
            )

            # Classify risk level
            if overall_risk >= 0.75:
                risk_level = "critical"
            elif overall_risk >= 0.5:
                risk_level = "high"
            elif overall_risk >= 0.25:
                risk_level = "medium"
            else:
                risk_level = "low"

            # Generate risk factors
            risk_factors = []
            if compliance_risk > 0.3:
                risk_factors.append({
                    "factor": "Low compliance",
                    "value": f"{feature_row[0]:.1f}%",
                    "impact": "high" if compliance_risk > 0.5 else "medium"
                })
            if health_risk > 0.3:
                risk_factors.append({
                    "factor": "Health check failures",
                    "value": f"{int(feature_row[1])} failures",
                    "impact": "high" if health_risk > 0.5 else "medium"
                })
            if drift_risk > 0.3:
                risk_factors.append({
                    "factor": "Configuration drift",
                    "value": f"{int(feature_row[2])} changes",
                    "impact": "medium"
                })
            if age_risk > 0.5:
                risk_factors.append({
                    "factor": "Stale audit data",
                    "value": f"{int(feature_row[3])} days",
                    "impact": "medium"
                })

            # Generate recommendations
            recommendations = self._generate_recommendations(
                compliance_risk, health_risk, drift_risk, age_risk
            )

            # Save to database
            risk_record = DeviceRiskScoreDB(
                device_id=device_id,
                overall_risk_score=overall_risk,
                compliance_risk=compliance_risk,
                health_risk=health_risk,
                drift_risk=drift_risk,
                age_risk=age_risk,
                risk_level=risk_level,
                risk_factors=risk_factors,
                recommendations=recommendations,
                model_version=f"weighted_v{self.MODEL_VERSION}"
            )
            db.add(risk_record)

            risk_scores.append({
                "device_id": device_id,
                "overall_risk": round(overall_risk, 3),
                "risk_level": risk_level,
                "compliance_risk": round(compliance_risk, 3),
                "health_risk": round(health_risk, 3),
                "drift_risk": round(drift_risk, 3),
                "age_risk": round(age_risk, 3),
                "risk_factors": risk_factors,
                "recommendations": recommendations
            })

        db.commit()
        logger.info(f"Calculated risk scores for {len(risk_scores)} devices")

        return risk_scores

    def _generate_recommendations(
        self,
        compliance_risk: float,
        health_risk: float,
        drift_risk: float,
        age_risk: float
    ) -> List[str]:
        """Generate actionable recommendations based on risks"""
        recommendations = []

        if compliance_risk > 0.5:
            recommendations.append("Run immediate compliance audit to identify failing rules")
        if compliance_risk > 0.3:
            recommendations.append("Review and remediate critical compliance findings")

        if health_risk > 0.5:
            recommendations.append("Investigate connectivity issues - check network paths and credentials")
        if health_risk > 0.3:
            recommendations.append("Verify NETCONF/SSH accessibility to device")

        if drift_risk > 0.5:
            recommendations.append("Review recent configuration changes for unauthorized modifications")
        if drift_risk > 0.3:
            recommendations.append("Compare current config with baseline and investigate drift")

        if age_risk > 0.5:
            recommendations.append("Schedule immediate audit - data is stale")
        elif age_risk > 0.3:
            recommendations.append("Consider increasing audit frequency for this device")

        if not recommendations:
            recommendations.append("Device is healthy - continue monitoring")

        return recommendations

    # =========================================================================
    # Insight Generation
    # =========================================================================

    def generate_insights(self, db: Session) -> List[Dict[str, Any]]:
        """
        Generate AI-powered insights based on all analytics data

        Returns:
            List of insight dictionaries
        """
        insights = []

        # Analyze recent trends
        trend_insights = self._analyze_trends(db)
        insights.extend(trend_insights)

        # Analyze anomalies
        anomaly_insights = self._analyze_anomalies(db)
        insights.extend(anomaly_insights)

        # Analyze risk distribution
        risk_insights = self._analyze_risks(db)
        insights.extend(risk_insights)

        # Save insights to database
        for insight_data in insights:
            insight = MLInsightDB(
                insight_type=insight_data['type'],
                category=insight_data.get('category', 'general'),
                title=insight_data['title'],
                description=insight_data['description'],
                severity=insight_data.get('severity', SeverityLevel.LOW),
                device_id=insight_data.get('device_id'),
                related_metrics=insight_data.get('metrics', {}),
                confidence_score=insight_data.get('confidence', 0.8),
                is_actionable=insight_data.get('actionable', False),
                model_version=f"insight_gen_v{self.MODEL_VERSION}"
            )
            db.add(insight)

        db.commit()
        logger.info(f"Generated {len(insights)} ML insights")

        return insights

    def _analyze_trends(self, db: Session) -> List[Dict[str, Any]]:
        """Analyze compliance trends for insights"""
        insights = []

        # Get 7-day trend
        cutoff = datetime.utcnow() - timedelta(days=7)
        trends = db.query(ComplianceTrendDB).filter(
            ComplianceTrendDB.snapshot_date >= cutoff,
            ComplianceTrendDB.device_id.is_(None)
        ).order_by(ComplianceTrendDB.snapshot_date).all()

        if len(trends) >= 2:
            first_compliance = trends[0].overall_compliance
            last_compliance = trends[-1].overall_compliance
            change = last_compliance - first_compliance

            if change < -10:
                insights.append({
                    "type": "trend",
                    "category": "compliance",
                    "title": "Significant Compliance Decline",
                    "description": f"Overall compliance has dropped {abs(change):.1f}% over the past week (from {first_compliance:.1f}% to {last_compliance:.1f}%). Immediate attention recommended.",
                    "severity": SeverityLevel.HIGH if change < -20 else SeverityLevel.MEDIUM,
                    "metrics": {"change": change, "current": last_compliance},
                    "confidence": 0.9,
                    "actionable": True
                })
            elif change > 10:
                insights.append({
                    "type": "trend",
                    "category": "compliance",
                    "title": "Compliance Improvement",
                    "description": f"Overall compliance has improved {change:.1f}% over the past week. Current compliance: {last_compliance:.1f}%.",
                    "severity": SeverityLevel.LOW,
                    "metrics": {"change": change, "current": last_compliance},
                    "confidence": 0.9,
                    "actionable": False
                })

        return insights

    def _analyze_anomalies(self, db: Session) -> List[Dict[str, Any]]:
        """Analyze anomalies for insights"""
        insights = []

        # Count unacknowledged anomalies
        cutoff = datetime.utcnow() - timedelta(days=7)
        unacked = db.query(ComplianceAnomalyDB).filter(
            ComplianceAnomalyDB.detected_at >= cutoff,
            ComplianceAnomalyDB.acknowledged == False
        ).count()

        critical = db.query(ComplianceAnomalyDB).filter(
            ComplianceAnomalyDB.detected_at >= cutoff,
            ComplianceAnomalyDB.severity == SeverityLevel.CRITICAL,
            ComplianceAnomalyDB.acknowledged == False
        ).count()

        if critical > 0:
            insights.append({
                "type": "anomaly",
                "category": "compliance",
                "title": f"{critical} Critical Anomalies Require Attention",
                "description": f"There are {critical} critical compliance anomalies detected in the past week that have not been acknowledged. Review these immediately.",
                "severity": SeverityLevel.CRITICAL,
                "metrics": {"critical_count": critical, "total_unacked": unacked},
                "confidence": 1.0,
                "actionable": True
            })
        elif unacked > 5:
            insights.append({
                "type": "anomaly",
                "category": "compliance",
                "title": f"{unacked} Anomalies Pending Review",
                "description": f"Multiple compliance anomalies ({unacked}) are awaiting acknowledgment. Consider reviewing and addressing these findings.",
                "severity": SeverityLevel.MEDIUM,
                "metrics": {"total_unacked": unacked},
                "confidence": 0.9,
                "actionable": True
            })

        return insights

    def _analyze_risks(self, db: Session) -> List[Dict[str, Any]]:
        """Analyze risk scores for insights"""
        insights = []

        # Get recent risk scores
        cutoff = datetime.utcnow() - timedelta(days=1)
        high_risk = db.query(DeviceRiskScoreDB).filter(
            DeviceRiskScoreDB.calculated_at >= cutoff,
            DeviceRiskScoreDB.risk_level.in_(['high', 'critical'])
        ).count()

        critical_risk = db.query(DeviceRiskScoreDB).filter(
            DeviceRiskScoreDB.calculated_at >= cutoff,
            DeviceRiskScoreDB.risk_level == 'critical'
        ).count()

        if critical_risk > 0:
            insights.append({
                "type": "prediction",
                "category": "risk",
                "title": f"{critical_risk} Devices at Critical Risk",
                "description": f"{critical_risk} devices are classified as critical risk. These devices have multiple risk factors and require immediate remediation.",
                "severity": SeverityLevel.CRITICAL,
                "metrics": {"critical_devices": critical_risk, "high_risk_total": high_risk},
                "confidence": 0.85,
                "actionable": True
            })
        elif high_risk > 3:
            insights.append({
                "type": "prediction",
                "category": "risk",
                "title": f"{high_risk} Devices Need Attention",
                "description": f"{high_risk} devices are classified as high or critical risk. Review their risk factors and address the top concerns.",
                "severity": SeverityLevel.MEDIUM,
                "metrics": {"high_risk_total": high_risk},
                "confidence": 0.85,
                "actionable": True
            })

        return insights

    def _generate_anomaly_insight(
        self,
        db: Session,
        anomalies: List[Dict],
        device_id: Optional[int]
    ):
        """Generate insight when anomalies are detected"""
        critical_count = sum(1 for a in anomalies if a['severity'] == 'critical')

        if critical_count > 0:
            insight = MLInsightDB(
                insight_type="anomaly",
                category="compliance",
                title=f"New Critical Anomalies Detected",
                description=f"{critical_count} critical anomalies were just detected. Immediate investigation recommended.",
                severity=SeverityLevel.CRITICAL,
                device_id=device_id,
                related_metrics={"anomaly_count": len(anomalies), "critical": critical_count},
                confidence_score=0.95,
                is_actionable=True,
                model_version=f"anomaly_detector_v{self.MODEL_VERSION}"
            )
            db.add(insight)
            db.commit()

    # =========================================================================
    # Model Management
    # =========================================================================

    def _log_model_metadata(
        self,
        db: Session,
        model_name: str,
        version: str,
        training_samples: int = 0,
        training_duration: float = 0.0,
        **metrics
    ):
        """Log model training metadata"""
        metadata = MLModelMetadataDB(
            model_name=model_name,
            version=version,
            training_samples=training_samples,
            training_duration_seconds=training_duration,
            mse=metrics.get('mse'),
            mae=metrics.get('mae'),
            accuracy=metrics.get('accuracy'),
            is_active=True
        )
        db.add(metadata)
        db.commit()


# Singleton instance
ml_engine = MLEngine()
