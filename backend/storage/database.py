"""
Database Models and Connection Management

This module defines the SQLAlchemy ORM models for the RF Spectrum Monitor
and provides database connection management.
"""

from datetime import datetime
from typing import Optional, List
from enum import Enum as PyEnum

from sqlalchemy import (
    create_engine, Column, Integer, String, Float, DateTime,
    ForeignKey, Text, Boolean, Index, Enum, event
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker, Session
from sqlalchemy.pool import StaticPool

from ..core.config import settings


# Create declarative base
Base = declarative_base()


# Enums
class DeviceTypeEnum(PyEnum):
    """SDR device types"""
    HACKRF = "hackrf"
    RTLSDR = "rtlsdr"
    MOCK = "mock"


class SurveyTypeEnum(PyEnum):
    """Survey types"""
    FIXED = "fixed"
    MULTI_LOCATION = "multi_location"
    MOBILE = "mobile"


class SurveyStatusEnum(PyEnum):
    """Survey status"""
    PLANNED = "planned"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class LocationTypeEnum(PyEnum):
    """Location input types"""
    MANUAL = "manual"
    GPS = "gps"
    MOBILE = "mobile"


class ExportTypeEnum(PyEnum):
    """Export format types"""
    CSV = "csv"
    GEOPACKAGE = "geopackage"
    JSON = "json"


class ExportStatusEnum(PyEnum):
    """Export job status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# Models
class Device(Base):
    """SDR device configuration"""
    __tablename__ = 'devices'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    device_type = Column(Enum(DeviceTypeEnum), nullable=False)
    serial_number = Column(String(100), unique=True, nullable=True)
    sample_rate = Column(Integer, default=2400000)  # Hz
    gain = Column(Integer, default=20)  # dB
    calibration_offset = Column(Float, default=0.0)  # PPM
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    surveys = relationship("Survey", back_populates="device")
    measurements = relationship("Measurement", back_populates="device")

    def __repr__(self):
        return f"<Device(id={self.id}, name='{self.name}', type={self.device_type.value})>"


class Survey(Base):
    """Survey configuration and metadata"""
    __tablename__ = 'surveys'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    survey_type = Column(Enum(SurveyTypeEnum), nullable=False)
    device_id = Column(Integer, ForeignKey('devices.id'), nullable=True)

    # Frequency configuration
    start_frequency = Column(Float, nullable=False)  # Hz
    stop_frequency = Column(Float, nullable=False)   # Hz
    step_size = Column(Float, nullable=True)         # Hz
    bandwidth = Column(Float, default=200000)        # Hz (RBW)
    integration_time = Column(Float, default=0.1)    # seconds

    # Status tracking
    status = Column(Enum(SurveyStatusEnum), default=SurveyStatusEnum.PLANNED)
    progress = Column(Float, default=0.0)  # 0-100 percentage
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    device = relationship("Device", back_populates="surveys")
    locations = relationship("Location", back_populates="survey", cascade="all, delete-orphan")
    measurements = relationship("Measurement", back_populates="survey", cascade="all, delete-orphan")
    signals = relationship("SignalOfInterest", back_populates="survey", cascade="all, delete-orphan")
    export_jobs = relationship("ExportJob", back_populates="survey")

    def __repr__(self):
        return f"<Survey(id={self.id}, name='{self.name}', status={self.status.value})>"

    @property
    def frequency_range_mhz(self) -> str:
        """Human-readable frequency range"""
        return f"{self.start_frequency/1e6:.2f} - {self.stop_frequency/1e6:.2f} MHz"

    @property
    def duration_seconds(self) -> Optional[float]:
        """Survey duration in seconds"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


class Location(Base):
    """Survey measurement locations"""
    __tablename__ = 'locations'

    id = Column(Integer, primary_key=True, autoincrement=True)
    survey_id = Column(Integer, ForeignKey('surveys.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)

    # Coordinates (WGS84)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    altitude = Column(Float, nullable=True)  # meters
    accuracy = Column(Float, nullable=True)  # meters (GPS accuracy)

    location_type = Column(Enum(LocationTypeEnum), default=LocationTypeEnum.MANUAL)
    sequence_order = Column(Integer, default=0)  # Order in multi-location survey

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    survey = relationship("Survey", back_populates="locations")
    measurements = relationship("Measurement", back_populates="location")

    def __repr__(self):
        return f"<Location(id={self.id}, lat={self.latitude:.4f}, lon={self.longitude:.4f})>"


class Measurement(Base):
    """Spectrum measurement data"""
    __tablename__ = 'measurements'

    id = Column(Integer, primary_key=True, autoincrement=True)
    survey_id = Column(Integer, ForeignKey('surveys.id', ondelete='CASCADE'), nullable=False)
    location_id = Column(Integer, ForeignKey('locations.id', ondelete='SET NULL'), nullable=True)
    device_id = Column(Integer, ForeignKey('devices.id'), nullable=True)

    # Measurement data
    frequency = Column(Float, nullable=False)     # Hz (center frequency)
    bandwidth = Column(Float, nullable=False)     # Hz (measurement bandwidth)
    power_dbm = Column(Float, nullable=False)     # dBm (signal strength)
    noise_floor_dbm = Column(Float, nullable=True)  # dBm (estimated noise floor)
    snr_db = Column(Float, nullable=True)         # dB (signal-to-noise ratio)

    # Location (can be denormalized for mobile surveys)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    altitude = Column(Float, nullable=True)

    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    survey = relationship("Survey", back_populates="measurements")
    location = relationship("Location", back_populates="measurements")
    device = relationship("Device", back_populates="measurements")

    def __repr__(self):
        return f"<Measurement(freq={self.frequency/1e6:.2f}MHz, power={self.power_dbm:.1f}dBm)>"


# Indexes for Measurement table (performance optimization)
Index('idx_measurements_survey', Measurement.survey_id)
Index('idx_measurements_frequency', Measurement.frequency)
Index('idx_measurements_timestamp', Measurement.timestamp)
Index('idx_measurements_location', Measurement.latitude, Measurement.longitude)
Index('idx_measurements_survey_freq', Measurement.survey_id, Measurement.frequency)
Index('idx_measurements_survey_time', Measurement.survey_id, Measurement.timestamp)


class SignalOfInterest(Base):
    """Detected or manually tagged signals"""
    __tablename__ = 'signals_of_interest'

    id = Column(Integer, primary_key=True, autoincrement=True)
    survey_id = Column(Integer, ForeignKey('surveys.id', ondelete='SET NULL'), nullable=True)

    # Signal characteristics
    center_frequency = Column(Float, nullable=False)  # Hz
    bandwidth = Column(Float, nullable=True)          # Hz
    modulation = Column(String(50), nullable=True)    # FM, AM, digital, unknown
    description = Column(Text, nullable=True)
    tags = Column(Text, nullable=True)  # JSON array of tags

    # Statistics
    first_detected = Column(DateTime, nullable=True)
    last_detected = Column(DateTime, nullable=True)
    detection_count = Column(Integer, default=1)
    average_power_dbm = Column(Float, nullable=True)
    min_power_dbm = Column(Float, nullable=True)
    max_power_dbm = Column(Float, nullable=True)

    # Location (if associated with a specific location)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    survey = relationship("Survey", back_populates="signals")

    def __repr__(self):
        return f"<SignalOfInterest(freq={self.center_frequency/1e6:.2f}MHz)>"


class ExportJob(Base):
    """Export operation tracking"""
    __tablename__ = 'export_jobs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    survey_id = Column(Integer, ForeignKey('surveys.id'), nullable=True)

    export_type = Column(Enum(ExportTypeEnum), nullable=False)
    status = Column(Enum(ExportStatusEnum), default=ExportStatusEnum.PENDING)

    # File info
    file_name = Column(String(255), nullable=True)
    file_path = Column(Text, nullable=True)
    file_size = Column(Integer, nullable=True)  # bytes

    # Export parameters (JSON)
    parameters = Column(Text, nullable=True)

    # Status tracking
    progress = Column(Float, default=0.0)  # 0-100 percentage
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    survey = relationship("Survey", back_populates="export_jobs")

    def __repr__(self):
        return f"<ExportJob(id={self.id}, type={self.export_type.value}, status={self.status.value})>"


# Database engine and session management
_engine = None
_SessionLocal = None


def get_engine(database_url: Optional[str] = None):
    """
    Get or create database engine.

    Args:
        database_url: Optional database URL (uses settings if not provided)

    Returns:
        SQLAlchemy engine
    """
    global _engine

    if _engine is None:
        url = database_url or settings.database.url

        # SQLite-specific configuration
        if url.startswith("sqlite"):
            _engine = create_engine(
                url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
                echo=settings.database.echo
            )

            # Enable foreign keys for SQLite
            @event.listens_for(_engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()
        else:
            _engine = create_engine(
                url,
                pool_size=settings.database.pool_size,
                echo=settings.database.echo
            )

    return _engine


def get_session_factory():
    """
    Get session factory.

    Returns:
        Session factory
    """
    global _SessionLocal

    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=get_engine()
        )

    return _SessionLocal


def get_session() -> Session:
    """
    Get a new database session.

    Returns:
        Database session
    """
    SessionLocal = get_session_factory()
    return SessionLocal()


def init_db(database_url: Optional[str] = None):
    """
    Initialize database and create all tables.

    Args:
        database_url: Optional database URL
    """
    engine = get_engine(database_url)
    Base.metadata.create_all(bind=engine)


def drop_db(database_url: Optional[str] = None):
    """
    Drop all database tables.

    Args:
        database_url: Optional database URL
    """
    engine = get_engine(database_url)
    Base.metadata.drop_all(bind=engine)


def reset_db(database_url: Optional[str] = None):
    """
    Reset database (drop and recreate all tables).

    Args:
        database_url: Optional database URL
    """
    drop_db(database_url)
    init_db(database_url)


# Context manager for sessions
class DatabaseSession:
    """Context manager for database sessions"""

    def __init__(self):
        self.session = None

    def __enter__(self) -> Session:
        self.session = get_session()
        return self.session

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.session.rollback()
        self.session.close()


def db_session():
    """
    Generator for database sessions (for FastAPI dependency injection).

    Yields:
        Database session
    """
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
