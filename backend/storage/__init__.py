"""
Storage Module

This module provides database models, repositories, and connection management
for the RF Spectrum Monitor application.

Example usage:
    from backend.storage import (
        init_db, get_session, DatabaseSession,
        DeviceRepository, SurveyRepository, MeasurementRepository
    )

    # Initialize database
    init_db()

    # Use with context manager
    with DatabaseSession() as session:
        device_repo = DeviceRepository(session)
        device = device_repo.create(
            name="My RTL-SDR",
            device_type=DeviceTypeEnum.RTLSDR
        )
        session.commit()

    # Or with dependency injection (FastAPI)
    def get_devices(session: Session = Depends(db_session)):
        repo = DeviceRepository(session)
        return repo.get_all()
"""

# Database models
from .database import (
    Base,
    Device,
    Survey,
    Location,
    Measurement,
    SignalOfInterest,
    ExportJob,
    DeviceTypeEnum,
    SurveyTypeEnum,
    SurveyStatusEnum,
    LocationTypeEnum,
    ExportTypeEnum,
    ExportStatusEnum,
)

# Database connection management
from .database import (
    get_engine,
    get_session,
    get_session_factory,
    init_db,
    drop_db,
    reset_db,
    db_session,
    DatabaseSession,
)

# Repositories
from .repositories import (
    BaseRepository,
    DeviceRepository,
    SurveyRepository,
    LocationRepository,
    MeasurementRepository,
    SignalOfInterestRepository,
    ExportJobRepository,
)

__all__ = [
    # Models
    'Base',
    'Device',
    'Survey',
    'Location',
    'Measurement',
    'SignalOfInterest',
    'ExportJob',

    # Enums
    'DeviceTypeEnum',
    'SurveyTypeEnum',
    'SurveyStatusEnum',
    'LocationTypeEnum',
    'ExportTypeEnum',
    'ExportStatusEnum',

    # Database management
    'get_engine',
    'get_session',
    'get_session_factory',
    'init_db',
    'drop_db',
    'reset_db',
    'db_session',
    'DatabaseSession',

    # Repositories
    'BaseRepository',
    'DeviceRepository',
    'SurveyRepository',
    'LocationRepository',
    'MeasurementRepository',
    'SignalOfInterestRepository',
    'ExportJobRepository',
]
