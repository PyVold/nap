"""
Analytics, Forecasting, and Anomaly Detection Models
Advanced analytics for compliance trends and anomaly detection
"""
from sqlalchemy import Column, Integer, String, Boolean, JSON, DateTime, Text, Float, Date
from sqlalchemy.sql import func
from database import Base


class ComplianceTrend(Base):
    __tablename__ = "compliance_trends"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, index=True)
    device_group_id = Column(Integer, index=True)

    # Snapshot date
    snapshot_date = Column(Date, nullable=False, index=True)

    # Compliance metrics
    overall_compliance = Column(Float, nullable=False)  # Percentage
    total_rules = Column(Integer, nullable=False)
    passed_rules = Column(Integer, nullable=False)
    failed_rules = Column(Integer, nullable=False)
    warning_rules = Column(Integer, nullable=False)

    # By severity
    critical_failures = Column(Integer, default=0)
    high_failures = Column(Integer, default=0)
    medium_failures = Column(Integer, default=0)
    low_failures = Column(Integer, default=0)

    # By category
    category_scores = Column(JSON)  # {category: compliance_percentage}

    # By framework
    framework_scores = Column(JSON)  # {framework: compliance_percentage}

    # Change tracking
    compliance_change = Column(Float)  # Change from previous period
    new_failures = Column(Integer, default=0)
    fixed_issues = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ComplianceForecast(Base):
    __tablename__ = "compliance_forecasts"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, index=True)
    device_group_id = Column(Integer, index=True)

    # Forecast details
    forecast_date = Column(Date, nullable=False)  # Date being forecasted
    forecast_horizon_days = Column(Integer, nullable=False)  # How far into future

    # Predicted values
    predicted_compliance = Column(Float, nullable=False)
    confidence_interval_lower = Column(Float)  # Lower bound of confidence
    confidence_interval_upper = Column(Float)  # Upper bound of confidence
    confidence_level = Column(Float, default=0.95)  # 95% confidence

    # Model details
    model_type = Column(String)  # linear_regression, arima, prophet, etc.
    model_accuracy = Column(Float)  # R² or similar metric
    training_data_points = Column(Integer)

    # Trend indicators
    trend_direction = Column(String)  # improving, declining, stable
    expected_change = Column(Float)  # Expected change from current

    # Risk assessment
    risk_level = Column(String)  # low, medium, high
    risk_factors = Column(JSON)  # Factors contributing to risk

    # Metadata
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    model_version = Column(String)


class AnomalyDetection(Base):
    __tablename__ = "anomaly_detections"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, nullable=False, index=True)

    # Anomaly details
    anomaly_type = Column(String, nullable=False)  # config_change, compliance_drop, behavior_change
    severity = Column(String, nullable=False)  # low, medium, high, critical

    # Detection
    metric = Column(String, nullable=False)  # What metric showed anomaly
    current_value = Column(Float, nullable=False)
    expected_value = Column(Float)
    deviation = Column(Float)  # How far from expected
    deviation_percentage = Column(Float)

    # Threshold-based
    threshold_value = Column(Float)
    threshold_type = Column(String)  # upper, lower, range

    # Statistical anomaly
    z_score = Column(Float)  # Standard deviations from mean
    is_statistical_anomaly = Column(Boolean, default=False)

    # Machine learning
    anomaly_score = Column(Float)  # ML model confidence (0-1)
    model_used = Column(String)  # isolation_forest, autoencoder, etc.

    # Context
    description = Column(Text)
    affected_rules = Column(JSON)  # Rules affected by this anomaly
    related_changes = Column(JSON)  # Recent changes that might explain

    # Resolution
    status = Column(String, default="new")  # new, investigating, resolved, false_positive
    is_acknowledged = Column(Boolean, default=False)
    acknowledged_by = Column(String)
    acknowledged_at = Column(DateTime(timezone=True))
    resolution_notes = Column(Text)
    resolved_at = Column(DateTime(timezone=True))

    # Alerting
    alert_sent = Column(Boolean, default=False)
    alert_sent_at = Column(DateTime(timezone=True))

    # Detection metadata
    detected_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    detection_method = Column(String)  # threshold, statistical, ml


class AnalyticsMetric(Base):
    __tablename__ = "analytics_metrics"

    id = Column(Integer, primary_key=True, index=True)

    # Metric identification
    metric_name = Column(String, nullable=False, index=True)
    metric_category = Column(String, index=True)  # compliance, performance, security
    device_id = Column(Integer, index=True)
    device_group_id = Column(Integer, index=True)

    # Metric value
    value = Column(Float, nullable=False)
    unit = Column(String)

    # Time series
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    aggregation_period = Column(String)  # hourly, daily, weekly, monthly

    # Additional dimensions
    tags = Column(JSON)  # Additional metadata for filtering/grouping

    # Statistical summary (for aggregated metrics)
    min_value = Column(Float)
    max_value = Column(Float)
    avg_value = Column(Float)
    std_dev = Column(Float)
    sample_count = Column(Integer)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DashboardWidget(Base):
    __tablename__ = "dashboard_widgets"

    id = Column(Integer, primary_key=True, index=True)

    # Widget details
    name = Column(String, nullable=False)
    widget_type = Column(String, nullable=False)  # chart, gauge, table, stat, map
    description = Column(Text)

    # Data source
    metric = Column(String)  # Metric to display
    data_source = Column(String)  # Table/view to query
    query = Column(JSON)  # Query parameters

    # Visualization
    chart_type = Column(String)  # line, bar, pie, area, scatter
    visualization_config = Column(JSON)  # Chart.js or similar config

    # Layout
    position_x = Column(Integer, default=0)
    position_y = Column(Integer, default=0)
    width = Column(Integer, default=4)
    height = Column(Integer, default=3)

    # Refresh
    refresh_interval_seconds = Column(Integer, default=300)  # 5 minutes
    last_refreshed = Column(DateTime(timezone=True))

    # Filters
    default_filters = Column(JSON)
    allowed_filters = Column(JSON)

    # Permissions
    is_public = Column(Boolean, default=True)
    created_by = Column(String)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
