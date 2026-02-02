"""
Spectrum API Models

Pydantic models for spectrum data API requests and responses.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class MeasurementBase(BaseModel):
    """Base measurement model"""
    frequency: float = Field(..., gt=0, description="Center frequency in Hz")
    bandwidth: float = Field(..., gt=0, description="Measurement bandwidth in Hz")
    power_dbm: float = Field(..., description="Signal power in dBm")
    noise_floor_dbm: Optional[float] = Field(None, description="Noise floor in dBm")
    snr_db: Optional[float] = Field(None, description="Signal-to-noise ratio in dB")
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    altitude: Optional[float] = None


class MeasurementCreate(MeasurementBase):
    """Model for creating a measurement"""
    survey_id: int
    location_id: Optional[int] = None
    device_id: Optional[int] = None
    timestamp: Optional[datetime] = None


class MeasurementResponse(MeasurementBase):
    """Model for measurement response"""
    id: int
    survey_id: int
    location_id: Optional[int]
    device_id: Optional[int]
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class MeasurementListResponse(BaseModel):
    """Model for list of measurements"""
    measurements: List[MeasurementResponse]
    total: int
    has_more: bool


class MeasurementQuery(BaseModel):
    """Query parameters for measurements"""
    survey_id: Optional[int] = None
    start_freq: Optional[float] = Field(None, gt=0, description="Start frequency in Hz")
    end_freq: Optional[float] = Field(None, gt=0, description="End frequency in Hz")
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    min_power: Optional[float] = None
    max_power: Optional[float] = None
    has_location: Optional[bool] = None
    limit: int = Field(default=1000, ge=1, le=50000)
    offset: int = Field(default=0, ge=0)


class FrequencyStatistics(BaseModel):
    """Statistics for a frequency range"""
    min_power_dbm: Optional[float]
    max_power_dbm: Optional[float]
    avg_power_dbm: Optional[float]
    count: int
    min_frequency: Optional[float]
    max_frequency: Optional[float]


class SpectrumPoint(BaseModel):
    """Single point in spectrum data"""
    frequency: float = Field(description="Frequency in Hz")
    power_dbm: float = Field(description="Power in dBm")


class SpectrumData(BaseModel):
    """Spectrum measurement data"""
    frequencies: List[float] = Field(description="Frequency array in Hz")
    power_dbm: List[float] = Field(description="Power array in dBm")
    timestamp: datetime
    center_freq: float
    sample_rate: float
    fft_size: int
    noise_floor: Optional[float] = None


class SweepResult(BaseModel):
    """Result of a frequency sweep"""
    frequencies: List[float] = Field(description="Frequency array in Hz")
    power_dbm: List[float] = Field(description="Power array in dBm")
    timestamp: datetime
    sweep_time: float = Field(description="Sweep duration in seconds")
    start_freq: float
    stop_freq: float
    num_steps: int


class DetectedSignal(BaseModel):
    """Detected signal from spectrum analysis"""
    frequency: float = Field(description="Center frequency in Hz")
    power_dbm: float = Field(description="Peak power in dBm")
    bandwidth: float = Field(description="Estimated bandwidth in Hz")
    snr_db: Optional[float] = Field(None, description="Signal-to-noise ratio")


class ScanRequest(BaseModel):
    """Request to perform spectrum scan"""
    device_id: int = Field(..., description="Device to use for scanning")
    start_freq: float = Field(..., gt=0, description="Start frequency in Hz")
    stop_freq: float = Field(..., gt=0, description="Stop frequency in Hz")
    sample_rate: float = Field(default=2.4e6, gt=0, description="Sample rate in Hz")
    gain: int = Field(default=20, ge=0, le=100, description="Gain in dB")
    integration_time: float = Field(default=0.1, gt=0, le=10, description="Integration time in seconds")
    detect_signals: bool = Field(default=True, description="Perform signal detection")
    threshold_db: float = Field(default=10, description="Detection threshold above noise floor")


class ScanResponse(BaseModel):
    """Response from spectrum scan"""
    sweep: SweepResult
    signals: List[DetectedSignal] = []
    statistics: FrequencyStatistics


class LiveSpectrumRequest(BaseModel):
    """Request for live spectrum snapshot"""
    device_id: int
    center_freq: float = Field(..., gt=0)
    sample_rate: float = Field(default=2.4e6, gt=0)
    gain: int = Field(default=20, ge=0, le=100)
    fft_size: int = Field(default=1024, ge=256, le=8192)
    averaging: int = Field(default=4, ge=1, le=100)


# Signal of Interest models
class SignalOfInterestBase(BaseModel):
    """Base signal of interest model"""
    center_frequency: float = Field(..., gt=0, description="Center frequency in Hz")
    bandwidth: Optional[float] = Field(None, gt=0, description="Bandwidth in Hz")
    modulation: Optional[str] = Field(None, max_length=50, description="Modulation type")
    description: Optional[str] = None
    tags: Optional[str] = None  # JSON array as string
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)


class SignalOfInterestCreate(SignalOfInterestBase):
    """Model for creating signal of interest"""
    survey_id: Optional[int] = None
    average_power_dbm: Optional[float] = None


class SignalOfInterestResponse(SignalOfInterestBase):
    """Model for signal of interest response"""
    id: int
    survey_id: Optional[int]
    first_detected: Optional[datetime]
    last_detected: Optional[datetime]
    detection_count: int
    average_power_dbm: Optional[float]
    min_power_dbm: Optional[float]
    max_power_dbm: Optional[float]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SignalListResponse(BaseModel):
    """Model for list of signals"""
    signals: List[SignalOfInterestResponse]
    total: int
