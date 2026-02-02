"""
API Dependencies

FastAPI dependency injection functions for database sessions,
authentication, and other common dependencies.
"""

from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..storage.database import get_session
from ..storage.repositories import (
    DeviceRepository,
    SurveyRepository,
    LocationRepository,
    MeasurementRepository,
    SignalOfInterestRepository,
    ExportJobRepository,
)


def get_db() -> Generator[Session, None, None]:
    """
    Database session dependency.

    Yields a database session and handles cleanup after request completion.
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


def get_device_repository(db: Session = Depends(get_db)) -> DeviceRepository:
    """Get device repository instance"""
    return DeviceRepository(db)


def get_survey_repository(db: Session = Depends(get_db)) -> SurveyRepository:
    """Get survey repository instance"""
    return SurveyRepository(db)


def get_location_repository(db: Session = Depends(get_db)) -> LocationRepository:
    """Get location repository instance"""
    return LocationRepository(db)


def get_measurement_repository(db: Session = Depends(get_db)) -> MeasurementRepository:
    """Get measurement repository instance"""
    return MeasurementRepository(db)


def get_signal_repository(db: Session = Depends(get_db)) -> SignalOfInterestRepository:
    """Get signal of interest repository instance"""
    return SignalOfInterestRepository(db)


def get_export_repository(db: Session = Depends(get_db)) -> ExportJobRepository:
    """Get export job repository instance"""
    return ExportJobRepository(db)


class CommonQueryParams:
    """Common query parameters for list endpoints"""

    def __init__(
        self,
        limit: int = 100,
        offset: int = 0,
    ):
        self.limit = min(limit, 1000)  # Cap at 1000
        self.offset = max(offset, 0)


def common_parameters(
    limit: int = 100,
    offset: int = 0,
) -> CommonQueryParams:
    """Dependency for common pagination parameters"""
    return CommonQueryParams(limit=limit, offset=offset)
