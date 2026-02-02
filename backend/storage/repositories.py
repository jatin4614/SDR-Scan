"""
Data Repositories

This module provides repository classes for database operations.
Repositories encapsulate database access logic and provide a clean
interface for CRUD operations and queries.
"""

from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc, asc
from loguru import logger

from .database import (
    Device, Survey, Location, Measurement, SignalOfInterest, ExportJob,
    DeviceTypeEnum, SurveyTypeEnum, SurveyStatusEnum,
    LocationTypeEnum, ExportTypeEnum, ExportStatusEnum
)


class BaseRepository:
    """Base repository with common CRUD operations"""

    def __init__(self, session: Session):
        self.session = session

    def commit(self):
        """Commit current transaction"""
        self.session.commit()

    def rollback(self):
        """Rollback current transaction"""
        self.session.rollback()

    def flush(self):
        """Flush pending changes"""
        self.session.flush()


class DeviceRepository(BaseRepository):
    """Repository for Device model"""

    def create(
        self,
        name: str,
        device_type: DeviceTypeEnum,
        serial_number: Optional[str] = None,
        sample_rate: int = 2400000,
        gain: int = 20,
        calibration_offset: float = 0.0
    ) -> Device:
        """Create a new device"""
        device = Device(
            name=name,
            device_type=device_type,
            serial_number=serial_number,
            sample_rate=sample_rate,
            gain=gain,
            calibration_offset=calibration_offset
        )
        self.session.add(device)
        self.session.flush()
        logger.info(f"Created device: {device}")
        return device

    def get_by_id(self, device_id: int) -> Optional[Device]:
        """Get device by ID"""
        return self.session.query(Device).filter(Device.id == device_id).first()

    def get_by_serial(self, serial_number: str) -> Optional[Device]:
        """Get device by serial number"""
        return self.session.query(Device).filter(
            Device.serial_number == serial_number
        ).first()

    def get_all(self, active_only: bool = True) -> List[Device]:
        """Get all devices"""
        query = self.session.query(Device)
        if active_only:
            query = query.filter(Device.is_active == True)
        return query.order_by(Device.name).all()

    def get_by_type(self, device_type: DeviceTypeEnum) -> List[Device]:
        """Get devices by type"""
        return self.session.query(Device).filter(
            Device.device_type == device_type,
            Device.is_active == True
        ).all()

    def update(self, device_id: int, **kwargs) -> Optional[Device]:
        """Update device attributes"""
        device = self.get_by_id(device_id)
        if device:
            for key, value in kwargs.items():
                if hasattr(device, key):
                    setattr(device, key, value)
            self.session.flush()
            logger.info(f"Updated device {device_id}: {kwargs}")
        return device

    def delete(self, device_id: int) -> bool:
        """Delete device (soft delete by setting is_active=False)"""
        device = self.get_by_id(device_id)
        if device:
            device.is_active = False
            self.session.flush()
            logger.info(f"Deleted device: {device_id}")
            return True
        return False

    def hard_delete(self, device_id: int) -> bool:
        """Permanently delete device"""
        device = self.get_by_id(device_id)
        if device:
            self.session.delete(device)
            self.session.flush()
            return True
        return False


class SurveyRepository(BaseRepository):
    """Repository for Survey model"""

    def create(
        self,
        name: str,
        survey_type: SurveyTypeEnum,
        start_frequency: float,
        stop_frequency: float,
        device_id: Optional[int] = None,
        description: Optional[str] = None,
        step_size: Optional[float] = None,
        bandwidth: float = 200000,
        integration_time: float = 0.1
    ) -> Survey:
        """Create a new survey"""
        survey = Survey(
            name=name,
            survey_type=survey_type,
            start_frequency=start_frequency,
            stop_frequency=stop_frequency,
            device_id=device_id,
            description=description,
            step_size=step_size,
            bandwidth=bandwidth,
            integration_time=integration_time
        )
        self.session.add(survey)
        self.session.flush()
        logger.info(f"Created survey: {survey}")
        return survey

    def get_by_id(self, survey_id: int) -> Optional[Survey]:
        """Get survey by ID"""
        return self.session.query(Survey).filter(Survey.id == survey_id).first()

    def get_all(
        self,
        status: Optional[SurveyStatusEnum] = None,
        survey_type: Optional[SurveyTypeEnum] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Survey]:
        """Get all surveys with optional filters"""
        query = self.session.query(Survey)

        if status:
            query = query.filter(Survey.status == status)
        if survey_type:
            query = query.filter(Survey.survey_type == survey_type)

        return query.order_by(desc(Survey.created_at)).offset(offset).limit(limit).all()

    def get_active(self) -> List[Survey]:
        """Get surveys that are currently running"""
        return self.session.query(Survey).filter(
            Survey.status == SurveyStatusEnum.RUNNING
        ).all()

    def update(self, survey_id: int, **kwargs) -> Optional[Survey]:
        """Update survey attributes"""
        survey = self.get_by_id(survey_id)
        if survey:
            for key, value in kwargs.items():
                if hasattr(survey, key):
                    setattr(survey, key, value)
            self.session.flush()
            logger.info(f"Updated survey {survey_id}: {kwargs}")
        return survey

    def update_status(
        self,
        survey_id: int,
        status: SurveyStatusEnum,
        error_message: Optional[str] = None
    ) -> Optional[Survey]:
        """Update survey status with timestamp handling"""
        survey = self.get_by_id(survey_id)
        if survey:
            survey.status = status
            survey.error_message = error_message

            if status == SurveyStatusEnum.RUNNING:
                survey.started_at = datetime.utcnow()
            elif status in (SurveyStatusEnum.COMPLETED, SurveyStatusEnum.FAILED):
                survey.completed_at = datetime.utcnow()

            self.session.flush()
            logger.info(f"Survey {survey_id} status changed to {status.value}")
        return survey

    def update_progress(self, survey_id: int, progress: float) -> Optional[Survey]:
        """Update survey progress (0-100)"""
        survey = self.get_by_id(survey_id)
        if survey:
            survey.progress = min(100.0, max(0.0, progress))
            self.session.flush()
        return survey

    def delete(self, survey_id: int) -> bool:
        """Delete survey and all related data"""
        survey = self.get_by_id(survey_id)
        if survey:
            self.session.delete(survey)
            self.session.flush()
            logger.info(f"Deleted survey: {survey_id}")
            return True
        return False

    def get_statistics(self, survey_id: int) -> Dict[str, Any]:
        """Get survey statistics"""
        survey = self.get_by_id(survey_id)
        if not survey:
            return {}

        # Count measurements
        measurement_count = self.session.query(func.count(Measurement.id)).filter(
            Measurement.survey_id == survey_id
        ).scalar()

        # Get power statistics
        power_stats = self.session.query(
            func.min(Measurement.power_dbm),
            func.max(Measurement.power_dbm),
            func.avg(Measurement.power_dbm)
        ).filter(Measurement.survey_id == survey_id).first()

        # Count signals of interest
        signal_count = self.session.query(func.count(SignalOfInterest.id)).filter(
            SignalOfInterest.survey_id == survey_id
        ).scalar()

        # Count locations
        location_count = self.session.query(func.count(Location.id)).filter(
            Location.survey_id == survey_id
        ).scalar()

        return {
            'survey_id': survey_id,
            'name': survey.name,
            'status': survey.status.value,
            'measurement_count': measurement_count or 0,
            'signal_count': signal_count or 0,
            'location_count': location_count or 0,
            'min_power_dbm': power_stats[0] if power_stats[0] else None,
            'max_power_dbm': power_stats[1] if power_stats[1] else None,
            'avg_power_dbm': power_stats[2] if power_stats[2] else None,
            'duration_seconds': survey.duration_seconds,
            'frequency_range': survey.frequency_range_mhz
        }


class LocationRepository(BaseRepository):
    """Repository for Location model"""

    def create(
        self,
        survey_id: int,
        latitude: float,
        longitude: float,
        name: Optional[str] = None,
        description: Optional[str] = None,
        altitude: Optional[float] = None,
        accuracy: Optional[float] = None,
        location_type: LocationTypeEnum = LocationTypeEnum.MANUAL,
        sequence_order: int = 0
    ) -> Location:
        """Create a new location"""
        location = Location(
            survey_id=survey_id,
            latitude=latitude,
            longitude=longitude,
            name=name,
            description=description,
            altitude=altitude,
            accuracy=accuracy,
            location_type=location_type,
            sequence_order=sequence_order
        )
        self.session.add(location)
        self.session.flush()
        return location

    def get_by_id(self, location_id: int) -> Optional[Location]:
        """Get location by ID"""
        return self.session.query(Location).filter(Location.id == location_id).first()

    def get_by_survey(self, survey_id: int) -> List[Location]:
        """Get all locations for a survey"""
        return self.session.query(Location).filter(
            Location.survey_id == survey_id
        ).order_by(Location.sequence_order).all()

    def delete(self, location_id: int) -> bool:
        """Delete location"""
        location = self.get_by_id(location_id)
        if location:
            self.session.delete(location)
            self.session.flush()
            return True
        return False

    def bulk_create(self, survey_id: int, locations: List[Dict]) -> List[Location]:
        """Create multiple locations at once"""
        created = []
        for i, loc_data in enumerate(locations):
            location = Location(
                survey_id=survey_id,
                latitude=loc_data['latitude'],
                longitude=loc_data['longitude'],
                name=loc_data.get('name'),
                altitude=loc_data.get('altitude'),
                sequence_order=loc_data.get('sequence_order', i)
            )
            self.session.add(location)
            created.append(location)
        self.session.flush()
        return created


class MeasurementRepository(BaseRepository):
    """Repository for Measurement model"""

    def create(
        self,
        survey_id: int,
        frequency: float,
        bandwidth: float,
        power_dbm: float,
        location_id: Optional[int] = None,
        device_id: Optional[int] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        altitude: Optional[float] = None,
        noise_floor_dbm: Optional[float] = None,
        snr_db: Optional[float] = None,
        timestamp: Optional[datetime] = None
    ) -> Measurement:
        """Create a new measurement"""
        measurement = Measurement(
            survey_id=survey_id,
            frequency=frequency,
            bandwidth=bandwidth,
            power_dbm=power_dbm,
            location_id=location_id,
            device_id=device_id,
            latitude=latitude,
            longitude=longitude,
            altitude=altitude,
            noise_floor_dbm=noise_floor_dbm,
            snr_db=snr_db,
            timestamp=timestamp or datetime.utcnow()
        )
        self.session.add(measurement)
        return measurement

    def bulk_create(self, measurements: List[Dict]) -> int:
        """
        Create multiple measurements efficiently.

        Args:
            measurements: List of measurement dictionaries

        Returns:
            Number of measurements created
        """
        objects = [Measurement(**m) for m in measurements]
        self.session.bulk_save_objects(objects)
        self.session.flush()
        return len(objects)

    def get_by_id(self, measurement_id: int) -> Optional[Measurement]:
        """Get measurement by ID"""
        return self.session.query(Measurement).filter(
            Measurement.id == measurement_id
        ).first()

    def get_by_survey(
        self,
        survey_id: int,
        freq_range: Optional[Tuple[float, float]] = None,
        time_range: Optional[Tuple[datetime, datetime]] = None,
        limit: int = 10000,
        offset: int = 0
    ) -> List[Measurement]:
        """Get measurements for a survey with optional filters"""
        query = self.session.query(Measurement).filter(
            Measurement.survey_id == survey_id
        )

        if freq_range:
            query = query.filter(
                Measurement.frequency >= freq_range[0],
                Measurement.frequency <= freq_range[1]
            )

        if time_range:
            query = query.filter(
                Measurement.timestamp >= time_range[0],
                Measurement.timestamp <= time_range[1]
            )

        return query.order_by(Measurement.frequency).offset(offset).limit(limit).all()

    def get_by_frequency(
        self,
        survey_id: int,
        frequency: float,
        tolerance: float = 100000  # Hz
    ) -> List[Measurement]:
        """Get measurements near a specific frequency"""
        return self.session.query(Measurement).filter(
            Measurement.survey_id == survey_id,
            Measurement.frequency >= frequency - tolerance,
            Measurement.frequency <= frequency + tolerance
        ).order_by(Measurement.timestamp).all()

    def get_by_location(
        self,
        survey_id: int,
        latitude: float,
        longitude: float,
        radius_deg: float = 0.001  # ~100m
    ) -> List[Measurement]:
        """Get measurements near a geographic location"""
        return self.session.query(Measurement).filter(
            Measurement.survey_id == survey_id,
            Measurement.latitude.isnot(None),
            Measurement.latitude >= latitude - radius_deg,
            Measurement.latitude <= latitude + radius_deg,
            Measurement.longitude >= longitude - radius_deg,
            Measurement.longitude <= longitude + radius_deg
        ).all()

    def get_geo_referenced(
        self,
        survey_id: int,
        limit: int = 10000
    ) -> List[Measurement]:
        """Get only geo-referenced measurements"""
        return self.session.query(Measurement).filter(
            Measurement.survey_id == survey_id,
            Measurement.latitude.isnot(None),
            Measurement.longitude.isnot(None)
        ).limit(limit).all()

    def get_frequency_statistics(
        self,
        survey_id: int,
        freq_range: Optional[Tuple[float, float]] = None
    ) -> Dict[str, Any]:
        """Get statistics for measurements in a frequency range"""
        query = self.session.query(
            func.min(Measurement.power_dbm),
            func.max(Measurement.power_dbm),
            func.avg(Measurement.power_dbm),
            func.count(Measurement.id),
            func.min(Measurement.frequency),
            func.max(Measurement.frequency)
        ).filter(Measurement.survey_id == survey_id)

        if freq_range:
            query = query.filter(
                Measurement.frequency >= freq_range[0],
                Measurement.frequency <= freq_range[1]
            )

        result = query.first()

        return {
            'min_power_dbm': result[0],
            'max_power_dbm': result[1],
            'avg_power_dbm': result[2],
            'count': result[3],
            'min_frequency': result[4],
            'max_frequency': result[5]
        }

    def delete_by_survey(self, survey_id: int) -> int:
        """Delete all measurements for a survey"""
        count = self.session.query(Measurement).filter(
            Measurement.survey_id == survey_id
        ).delete()
        self.session.flush()
        return count

    def count_by_survey(self, survey_id: int) -> int:
        """Count measurements for a survey"""
        return self.session.query(func.count(Measurement.id)).filter(
            Measurement.survey_id == survey_id
        ).scalar() or 0


class SignalOfInterestRepository(BaseRepository):
    """Repository for SignalOfInterest model"""

    def create(
        self,
        center_frequency: float,
        survey_id: Optional[int] = None,
        bandwidth: Optional[float] = None,
        modulation: Optional[str] = None,
        description: Optional[str] = None,
        average_power_dbm: Optional[float] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None
    ) -> SignalOfInterest:
        """Create a new signal of interest"""
        signal = SignalOfInterest(
            center_frequency=center_frequency,
            survey_id=survey_id,
            bandwidth=bandwidth,
            modulation=modulation,
            description=description,
            average_power_dbm=average_power_dbm,
            min_power_dbm=average_power_dbm,
            max_power_dbm=average_power_dbm,
            latitude=latitude,
            longitude=longitude,
            first_detected=datetime.utcnow(),
            last_detected=datetime.utcnow()
        )
        self.session.add(signal)
        self.session.flush()
        return signal

    def get_by_id(self, signal_id: int) -> Optional[SignalOfInterest]:
        """Get signal by ID"""
        return self.session.query(SignalOfInterest).filter(
            SignalOfInterest.id == signal_id
        ).first()

    def get_by_survey(self, survey_id: int) -> List[SignalOfInterest]:
        """Get all signals for a survey"""
        return self.session.query(SignalOfInterest).filter(
            SignalOfInterest.survey_id == survey_id
        ).order_by(SignalOfInterest.center_frequency).all()

    def get_all(self, limit: int = 100) -> List[SignalOfInterest]:
        """Get all signals of interest"""
        return self.session.query(SignalOfInterest).order_by(
            desc(SignalOfInterest.last_detected)
        ).limit(limit).all()

    def find_by_frequency(
        self,
        frequency: float,
        tolerance: float = 100000  # Hz
    ) -> Optional[SignalOfInterest]:
        """Find existing signal near a frequency"""
        return self.session.query(SignalOfInterest).filter(
            SignalOfInterest.center_frequency >= frequency - tolerance,
            SignalOfInterest.center_frequency <= frequency + tolerance
        ).first()

    def update_detection(
        self,
        signal_id: int,
        power_dbm: float
    ) -> Optional[SignalOfInterest]:
        """Update signal with new detection"""
        signal = self.get_by_id(signal_id)
        if signal:
            signal.detection_count += 1
            signal.last_detected = datetime.utcnow()

            # Update power statistics
            if signal.min_power_dbm is None or power_dbm < signal.min_power_dbm:
                signal.min_power_dbm = power_dbm
            if signal.max_power_dbm is None or power_dbm > signal.max_power_dbm:
                signal.max_power_dbm = power_dbm

            # Update running average
            if signal.average_power_dbm is not None:
                n = signal.detection_count
                signal.average_power_dbm = (
                    signal.average_power_dbm * (n - 1) + power_dbm
                ) / n
            else:
                signal.average_power_dbm = power_dbm

            self.session.flush()
        return signal

    def delete(self, signal_id: int) -> bool:
        """Delete signal"""
        signal = self.get_by_id(signal_id)
        if signal:
            self.session.delete(signal)
            self.session.flush()
            return True
        return False


class ExportJobRepository(BaseRepository):
    """Repository for ExportJob model"""

    def create(
        self,
        export_type: ExportTypeEnum,
        survey_id: Optional[int] = None,
        parameters: Optional[str] = None
    ) -> ExportJob:
        """Create a new export job"""
        job = ExportJob(
            export_type=export_type,
            survey_id=survey_id,
            parameters=parameters
        )
        self.session.add(job)
        self.session.flush()
        return job

    def get_by_id(self, job_id: int) -> Optional[ExportJob]:
        """Get export job by ID"""
        return self.session.query(ExportJob).filter(ExportJob.id == job_id).first()

    def get_pending(self) -> List[ExportJob]:
        """Get all pending export jobs"""
        return self.session.query(ExportJob).filter(
            ExportJob.status == ExportStatusEnum.PENDING
        ).order_by(ExportJob.created_at).all()

    def get_by_survey(self, survey_id: int) -> List[ExportJob]:
        """Get all export jobs for a survey"""
        return self.session.query(ExportJob).filter(
            ExportJob.survey_id == survey_id
        ).order_by(desc(ExportJob.created_at)).all()

    def update_status(
        self,
        job_id: int,
        status: ExportStatusEnum,
        file_path: Optional[str] = None,
        file_size: Optional[int] = None,
        error_message: Optional[str] = None
    ) -> Optional[ExportJob]:
        """Update export job status"""
        job = self.get_by_id(job_id)
        if job:
            job.status = status
            if file_path:
                job.file_path = file_path
                job.file_name = file_path.split('/')[-1]
            if file_size:
                job.file_size = file_size
            if error_message:
                job.error_message = error_message

            if status == ExportStatusEnum.PROCESSING:
                job.started_at = datetime.utcnow()
            elif status in (ExportStatusEnum.COMPLETED, ExportStatusEnum.FAILED):
                job.completed_at = datetime.utcnow()

            self.session.flush()
        return job

    def update_progress(self, job_id: int, progress: float) -> Optional[ExportJob]:
        """Update export job progress"""
        job = self.get_by_id(job_id)
        if job:
            job.progress = min(100.0, max(0.0, progress))
            self.session.flush()
        return job

    def delete(self, job_id: int) -> bool:
        """Delete export job"""
        job = self.get_by_id(job_id)
        if job:
            self.session.delete(job)
            self.session.flush()
            return True
        return False
