"""Initial database schema

Revision ID: 001_initial
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create devices table
    op.create_table(
        'devices',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('device_type', sa.Enum('HACKRF', 'RTLSDR', 'MOCK', name='devicetypeenum'), nullable=False),
        sa.Column('serial_number', sa.String(100), nullable=True),
        sa.Column('sample_rate', sa.Integer(), default=2400000),
        sa.Column('gain', sa.Integer(), default=20),
        sa.Column('calibration_offset', sa.Float(), default=0.0),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('serial_number')
    )

    # Create surveys table
    op.create_table(
        'surveys',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('survey_type', sa.Enum('FIXED', 'MULTI_LOCATION', 'MOBILE', name='surveytypeenum'), nullable=False),
        sa.Column('device_id', sa.Integer(), nullable=True),
        sa.Column('start_frequency', sa.Float(), nullable=False),
        sa.Column('stop_frequency', sa.Float(), nullable=False),
        sa.Column('step_size', sa.Float(), nullable=True),
        sa.Column('bandwidth', sa.Float(), default=200000),
        sa.Column('integration_time', sa.Float(), default=0.1),
        sa.Column('status', sa.Enum('PLANNED', 'RUNNING', 'PAUSED', 'COMPLETED', 'FAILED', name='surveystatusenum'), default='PLANNED'),
        sa.Column('progress', sa.Float(), default=0.0),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id']),
        sa.PrimaryKeyConstraint('id')
    )

    # Create locations table
    op.create_table(
        'locations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('survey_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(200), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('altitude', sa.Float(), nullable=True),
        sa.Column('accuracy', sa.Float(), nullable=True),
        sa.Column('location_type', sa.Enum('MANUAL', 'GPS', 'MOBILE', name='locationtypeenum'), default='MANUAL'),
        sa.Column('sequence_order', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['survey_id'], ['surveys.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create measurements table
    op.create_table(
        'measurements',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('survey_id', sa.Integer(), nullable=False),
        sa.Column('location_id', sa.Integer(), nullable=True),
        sa.Column('device_id', sa.Integer(), nullable=True),
        sa.Column('frequency', sa.Float(), nullable=False),
        sa.Column('bandwidth', sa.Float(), nullable=False),
        sa.Column('power_dbm', sa.Float(), nullable=False),
        sa.Column('noise_floor_dbm', sa.Float(), nullable=True),
        sa.Column('snr_db', sa.Float(), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('altitude', sa.Float(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id']),
        sa.ForeignKeyConstraint(['location_id'], ['locations.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['survey_id'], ['surveys.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for measurements
    op.create_index('idx_measurements_survey', 'measurements', ['survey_id'])
    op.create_index('idx_measurements_frequency', 'measurements', ['frequency'])
    op.create_index('idx_measurements_timestamp', 'measurements', ['timestamp'])
    op.create_index('idx_measurements_location', 'measurements', ['latitude', 'longitude'])
    op.create_index('idx_measurements_survey_freq', 'measurements', ['survey_id', 'frequency'])
    op.create_index('idx_measurements_survey_time', 'measurements', ['survey_id', 'timestamp'])

    # Create signals_of_interest table
    op.create_table(
        'signals_of_interest',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('survey_id', sa.Integer(), nullable=True),
        sa.Column('center_frequency', sa.Float(), nullable=False),
        sa.Column('bandwidth', sa.Float(), nullable=True),
        sa.Column('modulation', sa.String(50), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('tags', sa.Text(), nullable=True),
        sa.Column('first_detected', sa.DateTime(), nullable=True),
        sa.Column('last_detected', sa.DateTime(), nullable=True),
        sa.Column('detection_count', sa.Integer(), default=1),
        sa.Column('average_power_dbm', sa.Float(), nullable=True),
        sa.Column('min_power_dbm', sa.Float(), nullable=True),
        sa.Column('max_power_dbm', sa.Float(), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['survey_id'], ['surveys.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create export_jobs table
    op.create_table(
        'export_jobs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('survey_id', sa.Integer(), nullable=True),
        sa.Column('export_type', sa.Enum('CSV', 'GEOPACKAGE', 'JSON', name='exporttypeenum'), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', name='exportstatusenum'), default='PENDING'),
        sa.Column('file_name', sa.String(255), nullable=True),
        sa.Column('file_path', sa.Text(), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('parameters', sa.Text(), nullable=True),
        sa.Column('progress', sa.Float(), default=0.0),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['survey_id'], ['surveys.id']),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('export_jobs')
    op.drop_table('signals_of_interest')
    op.drop_index('idx_measurements_survey_time', 'measurements')
    op.drop_index('idx_measurements_survey_freq', 'measurements')
    op.drop_index('idx_measurements_location', 'measurements')
    op.drop_index('idx_measurements_timestamp', 'measurements')
    op.drop_index('idx_measurements_frequency', 'measurements')
    op.drop_index('idx_measurements_survey', 'measurements')
    op.drop_table('measurements')
    op.drop_table('locations')
    op.drop_table('surveys')
    op.drop_table('devices')
