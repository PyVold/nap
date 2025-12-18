from sqlalchemy import Column, Integer, String, Boolean, Float, JSON, DateTime, Text, Enum as SQLEnum, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from shared.database import Base
from models.enums import SeverityLevel

# ============================================================================
# Analytics & Compliance Intelligence
# ============================================================================

class ComplianceTrendDB(Base):
    """Tracks compliance trends over time"""
    __tablename__ = "compliance_trends"
    __table_args__ = (
        Index('ix_compliance_trends_snapshot_date', 'snapshot_date'),
    )

    id = Column(Integer, primary_key=True, index=True)
    snapshot_date = Column(DateTime, default=datetime.utcnow)
    device_id = Column(Integer, nullable=True)  # Foreign key removed - cross-service reference
    
    # Compliance metrics
    overall_compliance = Column(Float, default=0.0)
    compliance_change = Column(Float, default=0.0)  # Change from previous snapshot
    total_devices = Column(Integer, default=0)
    compliant_devices = Column(Integer, default=0)
    failed_devices = Column(Integer, default=0)
    
    # Detailed metrics
    total_checks = Column(Integer, default=0)
    passed_checks = Column(Integer, default=0)
    failed_checks = Column(Integer, default=0)
    warning_checks = Column(Integer, default=0)
    
    # Severity breakdown
    critical_failures = Column(Integer, default=0)
    high_failures = Column(Integer, default=0)
    medium_failures = Column(Integer, default=0)
    low_failures = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class ComplianceForecastDB(Base):
    """Predictive compliance forecasts"""
    __tablename__ = "compliance_forecasts"
    __table_args__ = (
        Index('ix_compliance_forecasts_date', 'forecast_date'),
    )

    id = Column(Integer, primary_key=True, index=True)
    forecast_date = Column(DateTime, nullable=False)  # Date being forecasted
    device_id = Column(Integer, nullable=True)  # Foreign key removed - cross-service reference
    
    # Predictions
    predicted_compliance = Column(Float, default=0.0)
    confidence_score = Column(Float, default=0.0)  # 0.0-1.0
    predicted_failures = Column(Integer, default=0)
    
    # Model metadata
    model_version = Column(String(50), default="linear_regression_v1")
    training_data_points = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class ComplianceAnomalyDB(Base):
    """Detected compliance anomalies"""
    __tablename__ = "compliance_anomalies"
    __table_args__ = (
        Index('ix_compliance_anomalies_detected_at', 'detected_at'),
        Index('ix_compliance_anomalies_device_acknowledged', 'device_id', 'acknowledged'),
    )

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, nullable=True)  # Foreign key removed - cross-service reference
    detected_at = Column(DateTime, default=datetime.utcnow)
    
    # Anomaly details
    anomaly_type = Column(String(100), nullable=False)  # compliance_drop, unusual_pattern, spike_failures
    severity = Column(SQLEnum(SeverityLevel), default=SeverityLevel.MEDIUM)
    description = Column(Text, nullable=True)
    
    # Statistical metrics
    z_score = Column(Float, nullable=True)  # Standard deviations from mean
    expected_value = Column(Float, nullable=True)
    actual_value = Column(Float, nullable=True)
    
    # Response tracking
    acknowledged = Column(Boolean, default=False)
    acknowledged_by = Column(String(100), nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    resolution_notes = Column(Text, nullable=True)


# ============================================================================
# ML-Powered Analytics Models
# ============================================================================

class DeviceRiskScoreDB(Base):
    """ML-generated device risk scores"""
    __tablename__ = "device_risk_scores"
    __table_args__ = (
        Index('ix_device_risk_scores_device', 'device_id'),
        Index('ix_device_risk_scores_calculated', 'calculated_at'),
    )

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, nullable=False)
    calculated_at = Column(DateTime, default=datetime.utcnow)

    # Risk metrics (0.0 - 1.0 scale)
    overall_risk_score = Column(Float, default=0.0)
    compliance_risk = Column(Float, default=0.0)      # Based on audit failures
    health_risk = Column(Float, default=0.0)          # Based on connectivity issues
    drift_risk = Column(Float, default=0.0)           # Based on config changes
    age_risk = Column(Float, default=0.0)             # Based on time since last audit

    # Risk classification
    risk_level = Column(String(20), default="low")    # low, medium, high, critical

    # Contributing factors (JSON list of factor objects)
    risk_factors = Column(JSON, default=list)

    # Model metadata
    model_version = Column(String(50), default="gradient_boosting_v1")
    feature_importance = Column(JSON, nullable=True)  # Feature weights

    # Recommendations
    recommendations = Column(JSON, default=list)      # List of suggested actions


class MLInsightDB(Base):
    """AI-generated insights and recommendations"""
    __tablename__ = "ml_insights"
    __table_args__ = (
        Index('ix_ml_insights_generated', 'generated_at'),
        Index('ix_ml_insights_type', 'insight_type'),
    )

    id = Column(Integer, primary_key=True, index=True)
    generated_at = Column(DateTime, default=datetime.utcnow)

    # Insight categorization
    insight_type = Column(String(50), nullable=False)  # trend, anomaly, prediction, recommendation
    category = Column(String(50), nullable=True)       # compliance, health, security, performance

    # Content
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(SQLEnum(SeverityLevel), default=SeverityLevel.LOW)

    # Associated data
    device_id = Column(Integer, nullable=True)
    related_metrics = Column(JSON, default=dict)      # Supporting data/metrics

    # ML confidence
    confidence_score = Column(Float, default=0.0)     # 0.0-1.0
    model_version = Column(String(50), nullable=True)

    # Action tracking
    is_actionable = Column(Boolean, default=False)
    action_taken = Column(Boolean, default=False)
    dismissed = Column(Boolean, default=False)
    dismissed_by = Column(String(100), nullable=True)


class MLModelMetadataDB(Base):
    """Metadata about trained ML models"""
    __tablename__ = "ml_model_metadata"
    __table_args__ = (
        Index('ix_ml_models_name_version', 'model_name', 'version'),
    )

    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String(100), nullable=False)  # e.g., "compliance_forecaster", "risk_scorer"
    version = Column(String(50), nullable=False)

    # Training info
    trained_at = Column(DateTime, default=datetime.utcnow)
    training_samples = Column(Integer, default=0)
    training_duration_seconds = Column(Float, default=0.0)

    # Performance metrics
    accuracy = Column(Float, nullable=True)
    precision = Column(Float, nullable=True)
    recall = Column(Float, nullable=True)
    f1_score = Column(Float, nullable=True)
    mse = Column(Float, nullable=True)              # For regression models
    mae = Column(Float, nullable=True)              # Mean absolute error

    # Model configuration
    hyperparameters = Column(JSON, default=dict)
    feature_names = Column(JSON, default=list)

    # Status
    is_active = Column(Boolean, default=True)       # Currently in use
    model_path = Column(String(255), nullable=True) # Path to serialized model
