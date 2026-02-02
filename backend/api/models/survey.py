"""
Survey API Models

Pydantic models for survey-related API requests and responses.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator
from enum import Enum


class SurveyType(str, Enum):
    """Survey type enum"""
    FIXED = "fixed"
    MULTI_LOCATION = "multi_location"
    MOBILE = "mobile"


class SurveyStatus(str, Enum):
    """Survey status enum"""
    PLANNED = "planned"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class LocationType(str, Enum):
    """Location type enum"""
    MANUAL = "manual"
    GPS = "gps"
    MOBILE = "mobile"


# Location models
class LocationBase(BaseModel):
    """Base location model"""
    latitude: float = Field(..., ge=-90, le=90, description="Latitude in degrees")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude in degrees")
    altitude: Optional[float] = Field(None, description="Altitude in meters")
    name: Optional[str] = Field(None, max_length=200, description="Location name")
    description: Optional[str] = None


class LocationCreate(LocationBase):
    """Model for creating a location"""
    location_type: LocationType = LocationType.MANUAL
    sequence_order: int = Field(default=0, ge=0, description="Order in multi-location survey")


class LocationResponse(LocationBase):
    """Model for location response"""
    id: int
    survey_id: int
    location_type: LocationType
    sequence_order: int
    accuracy: Optional[float] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Survey models
class SurveyBase(BaseModel):
    """Base survey model"""
    name: str = Field(..., min_length=1, max_length=200, description="Survey name")
    description: Optional[str] = Field(None, description="Survey description")
    survey_type: SurveyType = Field(..., description="Type of survey")
    start_frequency: float = Field(..., gt=0, description="Start frequency in Hz")
    stop_frequency: float = Field(..., gt=0, description="Stop frequency in Hz")
    step_size: Optional[float] = Field(None, gt=0, description="Frequency step size in Hz")
    bandwidth: float = Field(default=200000, gt=0, description="Resolution bandwidth in Hz")
    integration_time: float = Field(default=0.1, gt=0, le=60, description="Integration time in seconds")

    @field_validator('stop_frequency')
    @classmethod
    def stop_must_be_greater(cls, v, info):
        if 'start_frequency' in info.data and v <= info.data['start_frequency']:
            raise ValueError('stop_frequency must be greater than start_frequency')
        return v


class SurveyCreate(SurveyBase):
    """Model for creating a survey"""
    device_id: Optional[int] = Field(None, description="ID of device to use")
    locations: Optional[List[LocationCreate]] = Field(None, description="Locations for multi-location survey")


class SurveyUpdate(BaseModel):
    """Model for updating survey (all fields optional)"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    device_id: Optional[int] = None
    start_frequency: Optional[float] = Field(None, gt=0)
    stop_frequency: Optional[float] = Field(None, gt=0)
    step_size: Optional[float] = Field(None, gt=0)
    bandwidth: Optional[float] = Field(None, gt=0)
    integration_time: Optional[float] = Field(None, gt=0, le=60)


class SurveyResponse(SurveyBase):
    """Model for survey response"""
    id: int
    device_id: Optional[int]
    status: SurveyStatus
    progress: float = Field(ge=0, le=100)
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    frequency_range_mhz: str = Field(description="Human-readable frequency range")
    duration_seconds: Optional[float] = Field(description="Survey duration if completed")

    model_config = ConfigDict(from_attributes=True)


class SurveyDetailResponse(SurveyResponse):
    """Detailed survey response including locations"""
    locations: List[LocationResponse] = []
    measurement_count: int = 0
    signal_count: int = 0


class SurveyListResponse(BaseModel):
    """Model for list of surveys"""
    surveys: List[SurveyResponse]
    total: int


class SurveyStatistics(BaseModel):
    """Survey statistics"""
    survey_id: int
    name: str
    status: str
    measurement_count: int
    signal_count: int
    location_count: int
    min_power_dbm: Optional[float]
    max_power_dbm: Optional[float]
    avg_power_dbm: Optional[float]
    duration_seconds: Optional[float]
    frequency_range: str


class GPSMode(str, Enum):
    """GPS operation modes"""
    MANUAL = "manual"
    GPSD = "gpsd"
    MOCK = "mock"


class SurveyStartRequest(BaseModel):
    """Request to start a survey"""
    device_id: Optional[int] = Field(None, description="Override device ID")
    location: Optional[LocationCreate] = Field(None, description="Starting location for fixed surveys")
    gps_mode: Optional[str] = Field(
        default="manual",
        description="GPS mode: 'manual', 'gpsd', or 'mock'"
    )
    continuous_gps: bool = Field(
        default=False,
        description="Enable continuous GPS updates for mobile surveys"
    )


class SurveyStatusUpdate(BaseModel):
    """Manual survey status update"""
    status: SurveyStatus
    error_message: Optional[str] = None


class SurveyProgressResponse(BaseModel):
    """Real-time survey progress"""
    survey_id: int
    status: SurveyStatus
    progress: float = Field(ge=0, le=100)
    measurements_collected: int
    current_frequency: Optional[float] = None
    current_location: Optional[Dict[str, Any]] = None
    elapsed_seconds: Optional[float] = None
    errors: List[str] = []
    task_id: Optional[str] = None
