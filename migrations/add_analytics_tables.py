"""
Migration: Add analytics tables (compliance_trends, compliance_forecasts, compliance_anomalies)
"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime


def upgrade():
    # Create compliance_trends table
    op.create_table(
        'compliance_trends',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('snapshot_date', sa.DateTime(), nullable=False),
        sa.Column('device_id', sa.Integer(), nullable=True),
        sa.Column('overall_compliance', sa.Float(), default=0.0),
        sa.Column('compliance_change', sa.Float(), default=0.0),
        sa.Column('total_devices', sa.Integer(), default=0),
        sa.Column('compliant_devices', sa.Integer(), default=0),
        sa.Column('failed_devices', sa.Integer(), default=0),
        sa.Column('total_checks', sa.Integer(), default=0),
        sa.Column('passed_checks', sa.Integer(), default=0),
        sa.Column('failed_checks', sa.Integer(), default=0),
        sa.Column('warning_checks', sa.Integer(), default=0),
        sa.Column('critical_failures', sa.Integer(), default=0),
        sa.Column('high_failures', sa.Integer(), default=0),
        sa.Column('medium_failures', sa.Integer(), default=0),
        sa.Column('low_failures', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(), default=datetime.utcnow),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ondelete='SET NULL'),
    )

    # Create indexes for compliance_trends
    op.create_index('ix_compliance_trends_id', 'compliance_trends', ['id'])
    op.create_index('ix_compliance_trends_snapshot_date', 'compliance_trends', ['snapshot_date'])
    op.create_index('ix_compliance_trends_device_id', 'compliance_trends', ['device_id'])

    # Create compliance_forecasts table
    op.create_table(
        'compliance_forecasts',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('forecast_date', sa.DateTime(), nullable=False),
        sa.Column('device_id', sa.Integer(), nullable=True),
        sa.Column('predicted_compliance', sa.Float(), default=0.0),
        sa.Column('confidence_score', sa.Float(), default=0.0),
        sa.Column('predicted_failures', sa.Integer(), default=0),
        sa.Column('model_version', sa.String(50), default='linear_regression_v1'),
        sa.Column('training_data_points', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(), default=datetime.utcnow),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ondelete='SET NULL'),
    )

    # Create indexes for compliance_forecasts
    op.create_index('ix_compliance_forecasts_id', 'compliance_forecasts', ['id'])
    op.create_index('ix_compliance_forecasts_date', 'compliance_forecasts', ['forecast_date'])
    op.create_index('ix_compliance_forecasts_device_id', 'compliance_forecasts', ['device_id'])

    # Create compliance_anomalies table
    op.create_table(
        'compliance_anomalies',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('device_id', sa.Integer(), nullable=True),
        sa.Column('detected_at', sa.DateTime(), default=datetime.utcnow),
        sa.Column('anomaly_type', sa.String(100), nullable=False),
        sa.Column('severity', sa.String(20), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('z_score', sa.Float(), nullable=True),
        sa.Column('expected_value', sa.Float(), nullable=True),
        sa.Column('actual_value', sa.Float(), nullable=True),
        sa.Column('acknowledged', sa.Boolean(), default=False),
        sa.Column('acknowledged_by', sa.String(100), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime(), nullable=True),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ondelete='CASCADE'),
    )

    # Create indexes for compliance_anomalies
    op.create_index('ix_compliance_anomalies_id', 'compliance_anomalies', ['id'])
    op.create_index('ix_compliance_anomalies_detected_at', 'compliance_anomalies', ['detected_at'])
    op.create_index('ix_compliance_anomalies_device_id', 'compliance_anomalies', ['device_id'])
    op.create_index('ix_compliance_anomalies_device_acknowledged', 'compliance_anomalies', ['device_id', 'acknowledged'])


def downgrade():
    op.drop_table('compliance_anomalies')
    op.drop_table('compliance_forecasts')
    op.drop_table('compliance_trends')
