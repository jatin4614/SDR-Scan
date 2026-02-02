"""
Survey Manager

This module orchestrates survey execution, coordinating the SDR scanner,
GPS handler, and database storage to perform spectrum surveys.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Callable, Dict, Any
from datetime import datetime
from enum import Enum
import threading
import time
import numpy as np
from loguru import logger

from .config import settings
from .gps_handler import GPSHandler, GPSLocation, GPSMode
from .signal_processor import SignalProcessor, SignalPeak
from ..sdr import (
    SDRDevice, SpectrumScanner, ScanParameters, ScannerConfig,
    SweepResult, get_device
)
from ..storage.database import (
    get_session, Survey, Measurement, SignalOfInterest, Location,
    SurveyStatusEnum, SurveyTypeEnum
)
from ..storage.repositories import (
    SurveyRepository, MeasurementRepository, LocationRepository,
    SignalOfInterestRepository
)


class SurveyState(Enum):
    """Survey execution state"""
    IDLE = "idle"
    INITIALIZING = "initializing"
    SCANNING = "scanning"
    MOVING = "moving"          # Moving to next location
    PAUSED = "paused"
    COMPLETING = "completing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class SurveyProgress:
    """Survey progress information"""
    state: SurveyState
    progress_percent: float
    current_frequency: float
    current_location: Optional[GPSLocation]
    measurements_count: int
    signals_detected: int
    elapsed_time: float
    estimated_remaining: float
    current_step: int
    total_steps: int
    error_message: Optional[str] = None


@dataclass
class SurveyConfig:
    """Configuration for survey execution"""
    survey_id: int
    device_id: int
    start_frequency: float
    stop_frequency: float
    sample_rate: float = 2.4e6
    gain: int = 20
    bandwidth: float = 200000
    integration_time: float = 0.1
    survey_type: SurveyTypeEnum = SurveyTypeEnum.FIXED
    detect_signals: bool = True
    signal_threshold_db: float = 10.0
    save_all_measurements: bool = True
    locations: List[Dict] = field(default_factory=list)


class SurveyManager:
    """
    Orchestrates survey execution.

    Coordinates SDR scanning, GPS tracking, and data storage to
    perform fixed, multi-location, and mobile spectrum surveys.
    """

    def __init__(self):
        """Initialize survey manager"""
        self._current_survey: Optional[SurveyConfig] = None
        self._device: Optional[SDRDevice] = None
        self._scanner: Optional[SpectrumScanner] = None
        self._gps: Optional[GPSHandler] = None
        self._signal_processor = SignalProcessor()

        self._state = SurveyState.IDLE
        self._progress = 0.0
        self._stop_requested = False
        self._pause_requested = False

        self._scan_thread: Optional[threading.Thread] = None
        self._callbacks: List[Callable[[SurveyProgress], None]] = []
        self._lock = threading.Lock()

        self._measurements_count = 0
        self._signals_count = 0
        self._start_time = 0.0
        self._current_step = 0
        self._total_steps = 0

        logger.info("Survey manager initialized")

    @property
    def state(self) -> SurveyState:
        """Get current survey state"""
        return self._state

    @property
    def is_running(self) -> bool:
        """Check if a survey is currently running"""
        return self._state in (SurveyState.SCANNING, SurveyState.MOVING, SurveyState.INITIALIZING)

    def get_progress(self) -> SurveyProgress:
        """Get current survey progress"""
        elapsed = time.time() - self._start_time if self._start_time else 0

        # Estimate remaining time
        if self._progress > 0:
            estimated_total = elapsed / self._progress
            remaining = estimated_total - elapsed
        else:
            remaining = 0

        return SurveyProgress(
            state=self._state,
            progress_percent=self._progress * 100,
            current_frequency=self._scanner.device.center_freq if self._scanner else 0,
            current_location=self._gps.current_location if self._gps else None,
            measurements_count=self._measurements_count,
            signals_detected=self._signals_count,
            elapsed_time=elapsed,
            estimated_remaining=remaining,
            current_step=self._current_step,
            total_steps=self._total_steps
        )

    def add_progress_callback(self, callback: Callable[[SurveyProgress], None]) -> None:
        """Add callback for progress updates"""
        self._callbacks.append(callback)

    def remove_progress_callback(self, callback: Callable[[SurveyProgress], None]) -> None:
        """Remove progress callback"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def _notify_progress(self) -> None:
        """Notify callbacks of progress update"""
        progress = self.get_progress()
        for callback in self._callbacks:
            try:
                callback(progress)
            except Exception as e:
                logger.error(f"Progress callback error: {e}")

    def start_survey(
        self,
        config: SurveyConfig,
        gps_mode: GPSMode = GPSMode.MANUAL,
        initial_location: Optional[GPSLocation] = None
    ) -> bool:
        """
        Start a survey.

        Args:
            config: Survey configuration
            gps_mode: GPS mode to use
            initial_location: Initial location for manual GPS mode

        Returns:
            True if survey started successfully
        """
        if self.is_running:
            logger.error("Survey already running")
            return False

        self._current_survey = config
        self._state = SurveyState.INITIALIZING
        self._stop_requested = False
        self._pause_requested = False
        self._measurements_count = 0
        self._signals_count = 0
        self._start_time = time.time()
        self._progress = 0.0

        try:
            # Initialize device
            session = get_session()
            from ..storage.repositories import DeviceRepository
            device_repo = DeviceRepository(session)
            device_config = device_repo.get_by_id(config.device_id)

            if not device_config:
                raise ValueError(f"Device {config.device_id} not found")

            self._device = get_device(
                device_config.device_type.value.lower(),
                device_config.serial_number
            )
            self._device.open()

            # Initialize scanner
            scanner_config = ScannerConfig(
                fft_size=1024,
                averaging=4,
                peak_threshold_db=config.signal_threshold_db
            )
            self._scanner = SpectrumScanner(self._device, scanner_config)

            # Initialize GPS
            self._gps = GPSHandler(gps_mode)
            self._gps.start()

            if initial_location:
                self._gps.set_location(
                    initial_location.latitude,
                    initial_location.longitude,
                    initial_location.altitude
                )

            session.close()

            # Calculate total steps
            self._total_steps = self._calculate_total_steps(config)
            self._current_step = 0

            # Start survey thread
            self._scan_thread = threading.Thread(
                target=self._run_survey,
                daemon=True
            )
            self._scan_thread.start()

            logger.info(f"Survey {config.survey_id} started")
            return True

        except Exception as e:
            logger.error(f"Failed to start survey: {e}")
            self._state = SurveyState.FAILED
            self._cleanup()
            return False

    def _calculate_total_steps(self, config: SurveyConfig) -> int:
        """Calculate total number of steps in survey"""
        # Frequency steps
        freq_range = config.stop_frequency - config.start_frequency
        freq_steps = int(np.ceil(freq_range / (config.sample_rate * 0.8)))

        # Location steps
        if config.survey_type == SurveyTypeEnum.MULTI_LOCATION:
            location_steps = len(config.locations)
        else:
            location_steps = 1

        return freq_steps * location_steps

    def _run_survey(self) -> None:
        """Main survey execution loop"""
        config = self._current_survey
        self._state = SurveyState.SCANNING

        try:
            if config.survey_type == SurveyTypeEnum.FIXED:
                self._run_fixed_survey(config)
            elif config.survey_type == SurveyTypeEnum.MULTI_LOCATION:
                self._run_multi_location_survey(config)
            elif config.survey_type == SurveyTypeEnum.MOBILE:
                self._run_mobile_survey(config)

            if not self._stop_requested:
                self._state = SurveyState.COMPLETING
                self._finalize_survey(config)
                self._state = SurveyState.COMPLETED
                self._progress = 1.0

        except Exception as e:
            logger.error(f"Survey failed: {e}")
            self._state = SurveyState.FAILED
            self._update_survey_status(config.survey_id, SurveyStatusEnum.FAILED, str(e))

        finally:
            self._cleanup()
            self._notify_progress()

    def _run_fixed_survey(self, config: SurveyConfig) -> None:
        """Execute a fixed-location survey"""
        logger.info(f"Running fixed survey: {config.start_frequency/1e6:.2f} - {config.stop_frequency/1e6:.2f} MHz")

        params = ScanParameters(
            start_freq=config.start_frequency,
            stop_freq=config.stop_frequency,
            sample_rate=config.sample_rate,
            gain=config.gain,
            integration_time=config.integration_time
        )

        def on_sweep(result: SweepResult):
            if self._stop_requested:
                return

            # Get current location
            location = self._gps.get_location() if self._gps else None

            # Store measurements
            self._store_measurements(config, result, location)

            # Detect and store signals
            if config.detect_signals:
                self._detect_and_store_signals(config, result, location)

            # Update progress
            self._current_step += 1
            self._progress = self._current_step / max(self._total_steps, 1)
            self._notify_progress()

        # Run continuous scan
        while not self._stop_requested:
            if self._pause_requested:
                self._state = SurveyState.PAUSED
                time.sleep(0.5)
                continue

            self._state = SurveyState.SCANNING
            result = self._scanner.single_sweep(params)
            on_sweep(result)

            # For fixed surveys, we might want to repeat
            # Break after one sweep for now
            break

    def _run_multi_location_survey(self, config: SurveyConfig) -> None:
        """Execute a multi-location survey"""
        logger.info(f"Running multi-location survey with {len(config.locations)} locations")

        params = ScanParameters(
            start_freq=config.start_frequency,
            stop_freq=config.stop_frequency,
            sample_rate=config.sample_rate,
            gain=config.gain,
            integration_time=config.integration_time
        )

        for i, loc_data in enumerate(config.locations):
            if self._stop_requested:
                break

            while self._pause_requested:
                self._state = SurveyState.PAUSED
                time.sleep(0.5)
                if self._stop_requested:
                    return

            # Move to location
            self._state = SurveyState.MOVING
            location = GPSLocation(
                latitude=loc_data['latitude'],
                longitude=loc_data['longitude'],
                altitude=loc_data.get('altitude')
            )

            if self._gps:
                self._gps.set_location(location.latitude, location.longitude, location.altitude)

            logger.info(f"At location {i+1}/{len(config.locations)}: {location.latitude:.6f}, {location.longitude:.6f}")

            # Perform sweep at this location
            self._state = SurveyState.SCANNING
            result = self._scanner.single_sweep(params)

            # Store measurements
            self._store_measurements(config, result, location)

            # Detect signals
            if config.detect_signals:
                self._detect_and_store_signals(config, result, location)

            # Update progress
            self._current_step = (i + 1) * (self._total_steps // len(config.locations))
            self._progress = self._current_step / max(self._total_steps, 1)
            self._notify_progress()

    def _run_mobile_survey(self, config: SurveyConfig) -> None:
        """Execute a mobile survey with continuous GPS tracking"""
        logger.info("Running mobile survey with GPS tracking")

        params = ScanParameters(
            start_freq=config.start_frequency,
            stop_freq=config.stop_frequency,
            sample_rate=config.sample_rate,
            gain=config.gain,
            integration_time=config.integration_time
        )

        sweep_count = 0
        max_sweeps = 100  # Limit for mobile surveys

        while not self._stop_requested and sweep_count < max_sweeps:
            if self._pause_requested:
                self._state = SurveyState.PAUSED
                time.sleep(0.5)
                continue

            self._state = SurveyState.SCANNING

            # Get current GPS location
            location = self._gps.get_location() if self._gps else None

            if location is None:
                logger.warning("No GPS fix, skipping sweep")
                time.sleep(1)
                continue

            # Perform sweep
            result = self._scanner.single_sweep(params)

            # Store measurements with current location
            self._store_measurements(config, result, location)

            # Detect signals
            if config.detect_signals:
                self._detect_and_store_signals(config, result, location)

            sweep_count += 1
            self._current_step = sweep_count
            self._progress = sweep_count / max_sweeps
            self._notify_progress()

            # Small delay between sweeps
            time.sleep(0.5)

    def _store_measurements(
        self,
        config: SurveyConfig,
        result: SweepResult,
        location: Optional[GPSLocation]
    ) -> None:
        """Store sweep measurements to database"""
        if not config.save_all_measurements:
            return

        session = get_session()
        try:
            measurement_repo = MeasurementRepository(session)

            # Prepare measurement data
            measurements = []
            for freq, power in zip(result.frequencies, result.power_dbm):
                measurement = {
                    'survey_id': config.survey_id,
                    'frequency': float(freq),
                    'bandwidth': config.bandwidth,
                    'power_dbm': float(power),
                    'timestamp': datetime.fromtimestamp(result.timestamp)
                }

                if location:
                    measurement['latitude'] = location.latitude
                    measurement['longitude'] = location.longitude
                    measurement['altitude'] = location.altitude

                measurements.append(measurement)

            # Bulk insert
            count = measurement_repo.bulk_create(measurements)
            session.commit()

            self._measurements_count += count
            logger.debug(f"Stored {count} measurements")

        except Exception as e:
            logger.error(f"Failed to store measurements: {e}")
            session.rollback()
        finally:
            session.close()

    def _detect_and_store_signals(
        self,
        config: SurveyConfig,
        result: SweepResult,
        location: Optional[GPSLocation]
    ) -> None:
        """Detect and store signals of interest"""
        # Detect peaks
        peaks = self._signal_processor.detect_peaks(
            result.frequencies,
            result.power_dbm,
            threshold_db=config.signal_threshold_db
        )

        if not peaks:
            return

        session = get_session()
        try:
            signal_repo = SignalOfInterestRepository(session)

            for peak in peaks:
                # Check if signal already exists
                existing = signal_repo.find_by_frequency(peak.frequency, tolerance=50000)

                if existing:
                    # Update existing signal
                    signal_repo.update_detection(existing.id, peak.power_dbm)
                else:
                    # Create new signal
                    signal_repo.create(
                        center_frequency=peak.frequency,
                        survey_id=config.survey_id,
                        bandwidth=peak.bandwidth,
                        average_power_dbm=peak.power_dbm,
                        latitude=location.latitude if location else None,
                        longitude=location.longitude if location else None
                    )
                    self._signals_count += 1

            session.commit()

        except Exception as e:
            logger.error(f"Failed to store signals: {e}")
            session.rollback()
        finally:
            session.close()

    def _finalize_survey(self, config: SurveyConfig) -> None:
        """Finalize survey and update status"""
        self._update_survey_status(config.survey_id, SurveyStatusEnum.COMPLETED)
        logger.info(
            f"Survey {config.survey_id} completed: "
            f"{self._measurements_count} measurements, "
            f"{self._signals_count} signals"
        )

    def _update_survey_status(
        self,
        survey_id: int,
        status: SurveyStatusEnum,
        error_message: Optional[str] = None
    ) -> None:
        """Update survey status in database"""
        session = get_session()
        try:
            survey_repo = SurveyRepository(session)
            survey_repo.update_status(survey_id, status, error_message)
            survey_repo.update_progress(survey_id, self._progress * 100)
            session.commit()
        except Exception as e:
            logger.error(f"Failed to update survey status: {e}")
            session.rollback()
        finally:
            session.close()

    def stop_survey(self) -> None:
        """Stop the current survey"""
        if not self.is_running:
            return

        logger.info("Stopping survey...")
        self._stop_requested = True
        self._state = SurveyState.CANCELLED

        if self._scan_thread and self._scan_thread.is_alive():
            self._scan_thread.join(timeout=5.0)

        if self._current_survey:
            self._update_survey_status(
                self._current_survey.survey_id,
                SurveyStatusEnum.PAUSED
            )

    def pause_survey(self) -> None:
        """Pause the current survey"""
        if self.is_running:
            self._pause_requested = True
            logger.info("Survey paused")

    def resume_survey(self) -> None:
        """Resume a paused survey"""
        if self._state == SurveyState.PAUSED:
            self._pause_requested = False
            logger.info("Survey resumed")

    def _cleanup(self) -> None:
        """Clean up resources"""
        if self._device:
            try:
                self._device.close()
            except Exception as e:
                logger.warning(f"Error closing device: {e}")
            self._device = None

        if self._gps:
            try:
                self._gps.stop()
            except Exception as e:
                logger.warning(f"Error stopping GPS: {e}")
            self._gps = None

        self._scanner = None
        self._current_survey = None


# Global survey manager instance
_survey_manager: Optional[SurveyManager] = None


def get_survey_manager() -> SurveyManager:
    """Get the global survey manager instance"""
    global _survey_manager
    if _survey_manager is None:
        _survey_manager = SurveyManager()
    return _survey_manager
