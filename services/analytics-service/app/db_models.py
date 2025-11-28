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
    snapshot_date = Column(DateTime, default=datetime.utcnow, index=True)
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
    forecast_date = Column(DateTime, nullable=False, index=True)  # Date being forecasted
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
    detected_at = Column(DateTime, default=datetime.utcnow, index=True)
    
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
