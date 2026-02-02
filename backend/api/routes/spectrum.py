"""
Spectrum Data API Routes

Endpoints for querying spectrum measurements, performing scans,
and managing signals of interest.
"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from loguru import logger

from ..models import (
    MeasurementResponse,
    MeasurementListResponse,
    FrequencyStatistics,
    SpectrumData,
    SweepResult,
    DetectedSignal,
    ScanRequest,
    ScanResponse,
    LiveSpectrumRequest,
    SignalOfInterestCreate,
    SignalOfInterestResponse,
    SignalListResponse,
)
from ..dependencies import (
    get_measurement_repository,
    get_signal_repository,
    get_device_repository,
    get_survey_repository,
    CommonQueryParams,
    common_parameters,
)
from ...storage.repositories import (
    MeasurementRepository,
    SignalOfInterestRepository,
    DeviceRepository,
    SurveyRepository,
)
from ...sdr import get_device, ScanParameters, SpectrumScanner

router = APIRouter()


@router.get("/measurements", response_model=MeasurementListResponse)
async def get_measurements(
    survey_id: Optional[int] = None,
    start_freq: Optional[float] = Query(None, gt=0, description="Start frequency in Hz"),
    end_freq: Optional[float] = Query(None, gt=0, description="End frequency in Hz"),
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    has_location: Optional[bool] = None,
    limit: int = Query(1000, ge=1, le=50000),
    offset: int = Query(0, ge=0),
    repo: MeasurementRepository = Depends(get_measurement_repository)
):
    """
    Query spectrum measurements with filters.

    - **survey_id**: Filter by survey
    - **start_freq/end_freq**: Filter by frequency range
    - **start_time/end_time**: Filter by time range
    - **has_location**: Only return geo-referenced measurements
    """
    if survey_id:
        freq_range = (start_freq, end_freq) if start_freq and end_freq else None
        time_range = (start_time, end_time) if start_time and end_time else None

        if has_location:
            measurements = repo.get_geo_referenced(survey_id, limit=limit)
        else:
            measurements = repo.get_by_survey(
                survey_id,
                freq_range=freq_range,
                time_range=time_range,
                limit=limit,
                offset=offset
            )
    else:
        # TODO: Add method to query across all surveys
        measurements = []

    total = len(measurements)
    has_more = total == limit

    return MeasurementListResponse(
        measurements=[MeasurementResponse.model_validate(m) for m in measurements],
        total=total,
        has_more=has_more
    )


@router.get("/measurements/{survey_id}/statistics", response_model=FrequencyStatistics)
async def get_measurement_statistics(
    survey_id: int,
    start_freq: Optional[float] = Query(None, gt=0),
    end_freq: Optional[float] = Query(None, gt=0),
    repo: MeasurementRepository = Depends(get_measurement_repository)
):
    """
    Get statistics for measurements in a survey.
    """
    freq_range = (start_freq, end_freq) if start_freq and end_freq else None
    stats = repo.get_frequency_statistics(survey_id, freq_range)
    return FrequencyStatistics(**stats)


@router.get("/measurements/{survey_id}/by-frequency")
async def get_measurements_by_frequency(
    survey_id: int,
    frequency: float = Query(..., gt=0, description="Center frequency in Hz"),
    tolerance: float = Query(100000, gt=0, description="Frequency tolerance in Hz"),
    repo: MeasurementRepository = Depends(get_measurement_repository)
):
    """
    Get measurements near a specific frequency.
    """
    measurements = repo.get_by_frequency(survey_id, frequency, tolerance)
    return {
        "frequency": frequency,
        "tolerance": tolerance,
        "count": len(measurements),
        "measurements": [MeasurementResponse.model_validate(m) for m in measurements[:100]]
    }


@router.get("/measurements/{survey_id}/by-location")
async def get_measurements_by_location(
    survey_id: int,
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius: float = Query(0.001, gt=0, description="Search radius in degrees (~0.001 = 100m)"),
    repo: MeasurementRepository = Depends(get_measurement_repository)
):
    """
    Get measurements near a geographic location.
    """
    measurements = repo.get_by_location(survey_id, latitude, longitude, radius)
    return {
        "latitude": latitude,
        "longitude": longitude,
        "radius": radius,
        "count": len(measurements),
        "measurements": [MeasurementResponse.model_validate(m) for m in measurements[:100]]
    }


@router.post("/scan", response_model=ScanResponse)
async def perform_scan(
    request: ScanRequest,
    device_repo: DeviceRepository = Depends(get_device_repository)
):
    """
    Perform an ad-hoc spectrum scan.

    This endpoint performs a one-time frequency sweep without creating a survey.
    Useful for quick spectrum analysis.
    """
    device_config = device_repo.get_by_id(request.device_id)
    if not device_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device {request.device_id} not found"
        )

    try:
        # Get SDR device
        sdr_device = get_device(
            device_config.device_type.value.lower(),
            device_config.serial_number
        )
        sdr_device.open()

        # Create scanner
        scanner = SpectrumScanner(sdr_device)

        # Configure scan parameters
        params = ScanParameters(
            start_freq=request.start_freq,
            stop_freq=request.stop_freq,
            sample_rate=request.sample_rate,
            gain=request.gain,
            integration_time=request.integration_time
        )

        # Perform sweep
        result = scanner.single_sweep(params)

        # Detect signals if requested
        signals = []
        if request.detect_signals:
            detected = scanner.detect_peaks(
                result.frequencies,
                result.power_dbm,
                threshold_db=request.threshold_db
            )
            signals = [
                DetectedSignal(
                    frequency=s.frequency,
                    power_dbm=s.power_dbm,
                    bandwidth=s.bandwidth,
                    snr_db=s.snr_db
                )
                for s in detected
            ]

        # Get statistics
        stats = scanner.get_signal_statistics(result.frequencies, result.power_dbm)

        sdr_device.close()

        return ScanResponse(
            sweep=SweepResult(
                frequencies=result.frequencies.tolist(),
                power_dbm=result.power_dbm.tolist(),
                timestamp=datetime.fromtimestamp(result.timestamp),
                sweep_time=result.sweep_time,
                start_freq=result.start_freq,
                stop_freq=result.stop_freq,
                num_steps=result.num_steps
            ),
            signals=signals,
            statistics=FrequencyStatistics(**stats)
        )

    except Exception as e:
        logger.error(f"Scan failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Scan failed: {str(e)}"
        )


@router.post("/live", response_model=SpectrumData)
async def get_live_spectrum(
    request: LiveSpectrumRequest,
    device_repo: DeviceRepository = Depends(get_device_repository)
):
    """
    Get a live spectrum snapshot at a specific frequency.

    Returns the current spectrum view from the SDR device.
    """
    device_config = device_repo.get_by_id(request.device_id)
    if not device_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device {request.device_id} not found"
        )

    try:
        sdr_device = get_device(
            device_config.device_type.value.lower(),
            device_config.serial_number
        )
        sdr_device.open()
        sdr_device.set_center_freq(request.center_freq)
        sdr_device.set_sample_rate(request.sample_rate)
        sdr_device.set_gain(request.gain)

        spectrum = sdr_device.get_spectrum(
            fft_size=request.fft_size,
            average_count=request.averaging
        )

        sdr_device.close()

        return SpectrumData(
            frequencies=spectrum.frequencies.tolist(),
            power_dbm=spectrum.power_dbm.tolist(),
            timestamp=datetime.fromtimestamp(spectrum.timestamp),
            center_freq=spectrum.center_freq,
            sample_rate=spectrum.sample_rate,
            fft_size=spectrum.fft_size,
            noise_floor=spectrum.noise_floor
        )

    except Exception as e:
        logger.error(f"Live spectrum failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get live spectrum: {str(e)}"
        )


# Signals of Interest endpoints
@router.get("/signals", response_model=SignalListResponse)
async def list_signals(
    survey_id: Optional[int] = None,
    params: CommonQueryParams = Depends(common_parameters),
    repo: SignalOfInterestRepository = Depends(get_signal_repository)
):
    """
    List signals of interest.
    """
    if survey_id:
        signals = repo.get_by_survey(survey_id)
    else:
        signals = repo.get_all(limit=params.limit)

    return SignalListResponse(
        signals=[SignalOfInterestResponse.model_validate(s) for s in signals],
        total=len(signals)
    )


@router.post("/signals", response_model=SignalOfInterestResponse, status_code=status.HTTP_201_CREATED)
async def create_signal(
    signal: SignalOfInterestCreate,
    repo: SignalOfInterestRepository = Depends(get_signal_repository)
):
    """
    Create a new signal of interest.
    """
    # Check if signal already exists at this frequency
    existing = repo.find_by_frequency(signal.center_frequency, tolerance=50000)
    if existing:
        # Update existing signal
        repo.update_detection(existing.id, signal.average_power_dbm or -50)
        repo.commit()
        return SignalOfInterestResponse.model_validate(existing)

    db_signal = repo.create(
        center_frequency=signal.center_frequency,
        survey_id=signal.survey_id,
        bandwidth=signal.bandwidth,
        modulation=signal.modulation,
        description=signal.description,
        average_power_dbm=signal.average_power_dbm,
        latitude=signal.latitude,
        longitude=signal.longitude
    )
    repo.commit()
    return SignalOfInterestResponse.model_validate(db_signal)


@router.get("/signals/{signal_id}", response_model=SignalOfInterestResponse)
async def get_signal(
    signal_id: int,
    repo: SignalOfInterestRepository = Depends(get_signal_repository)
):
    """
    Get signal of interest by ID.
    """
    signal = repo.get_by_id(signal_id)
    if not signal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Signal {signal_id} not found"
        )
    return SignalOfInterestResponse.model_validate(signal)


@router.delete("/signals/{signal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_signal(
    signal_id: int,
    repo: SignalOfInterestRepository = Depends(get_signal_repository)
):
    """
    Delete a signal of interest.
    """
    if not repo.delete(signal_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Signal {signal_id} not found"
        )
    repo.commit()


@router.post("/signals/detect")
async def detect_signals(
    survey_id: int,
    threshold_db: float = Query(10, description="Detection threshold above noise floor"),
    min_separation_hz: float = Query(100000, description="Minimum separation between signals"),
    measurement_repo: MeasurementRepository = Depends(get_measurement_repository),
    signal_repo: SignalOfInterestRepository = Depends(get_signal_repository),
    survey_repo: SurveyRepository = Depends(get_survey_repository)
):
    """
    Automatically detect signals of interest from survey measurements.
    """
    import numpy as np
    from ...sdr import SpectrumScanner

    survey = survey_repo.get_by_id(survey_id)
    if not survey:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Survey {survey_id} not found"
        )

    # Get measurements
    measurements = measurement_repo.get_by_survey(survey_id, limit=50000)
    if not measurements:
        return {"detected": 0, "signals": []}

    # Convert to arrays
    frequencies = np.array([m.frequency for m in measurements])
    power_dbm = np.array([m.power_dbm for m in measurements])

    # Sort by frequency
    sorted_idx = np.argsort(frequencies)
    frequencies = frequencies[sorted_idx]
    power_dbm = power_dbm[sorted_idx]

    # Detect peaks using scanner
    scanner = SpectrumScanner.__new__(SpectrumScanner)
    scanner.config = type('Config', (), {
        'peak_threshold_db': threshold_db,
        'min_peak_distance_hz': min_separation_hz
    })()

    detected = scanner.detect_peaks(frequencies, power_dbm, threshold_db, min_separation_hz)

    # Create signals of interest
    created_signals = []
    for sig in detected:
        db_signal = signal_repo.create(
            center_frequency=sig.frequency,
            survey_id=survey_id,
            bandwidth=sig.bandwidth,
            average_power_dbm=sig.power_dbm
        )
        created_signals.append(SignalOfInterestResponse.model_validate(db_signal))

    signal_repo.commit()

    return {
        "detected": len(created_signals),
        "signals": created_signals
    }
