"""
Migration: Add hardware_inventory table
"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime


def upgrade():
    # Create hardware_inventory table
    op.create_table(
        'hardware_inventory',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('device_id', sa.Integer(), nullable=False),
        sa.Column('component_type', sa.String(50), nullable=False),
        sa.Column('component_name', sa.String(255), nullable=False),
        sa.Column('slot_number', sa.String(50), nullable=True),
        sa.Column('parent_id', sa.Integer(), nullable=True),
        sa.Column('part_number', sa.String(100), nullable=True),
        sa.Column('serial_number', sa.String(100), nullable=True),
        sa.Column('hardware_revision', sa.String(50), nullable=True),
        sa.Column('firmware_version', sa.String(100), nullable=True),
        sa.Column('model_name', sa.String(255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('operational_state', sa.String(50), nullable=True),
        sa.Column('admin_state', sa.String(50), nullable=True),
        sa.Column('manufacturing_date', sa.String(50), nullable=True),
        sa.Column('clei_code', sa.String(50), nullable=True),
        sa.Column('is_fru', sa.Boolean(), default=False),
        sa.Column('last_discovered', sa.DateTime(), default=datetime.utcnow),
        sa.Column('created_at', sa.DateTime(), default=datetime.utcnow),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_id'], ['hardware_inventory.id'], ondelete='CASCADE'),
    )

    # Create indexes
    op.create_index('ix_hardware_inventory_id', 'hardware_inventory', ['id'])
    op.create_index('ix_hardware_inventory_device_id', 'hardware_inventory', ['device_id'])
    op.create_index('ix_hardware_inventory_component_type', 'hardware_inventory', ['component_type'])
    op.create_index('ix_hardware_device_type', 'hardware_inventory', ['device_id', 'component_type'])
    op.create_index('ix_hardware_device_slot', 'hardware_inventory', ['device_id', 'slot_number'])


def downgrade():
    op.drop_table('hardware_inventory')
