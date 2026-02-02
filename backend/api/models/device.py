"""
Device API Models

Pydantic models for device-related API requests and responses.
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


class DeviceType(str, Enum):
    """Device type enum for API"""
    HACKRF = "hackrf"
    RTLSDR = "rtlsdr"
    MOCK = "mock"


class DeviceBase(BaseModel):
    """Base device model with common fields"""
    name: str = Field(..., min_length=1, max_length=100, description="Device name")
    device_type: DeviceType = Field(..., description="Type of SDR device")
    serial_number: Optional[str] = Field(None, max_length=100, description="Device serial number")
    sample_rate: int = Field(default=2400000, ge=100000, le=20000000, description="Sample rate in Hz")
    gain: int = Field(default=20, ge=0, le=100, description="Gain in dB")
    calibration_offset: float = Field(default=0.0, ge=-100, le=100, description="Calibration offset in PPM")


class DeviceCreate(DeviceBase):
    """Model for creating a new device"""
    pass


class DeviceUpdate(BaseModel):
    """Model for updating device (all fields optional)"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    sample_rate: Optional[int] = Field(None, ge=100000, le=20000000)
    gain: Optional[int] = Field(None, ge=0, le=100)
    calibration_offset: Optional[float] = Field(None, ge=-100, le=100)
    is_active: Optional[bool] = None


class DeviceResponse(DeviceBase):
    """Model for device response"""
    id: int
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DeviceListResponse(BaseModel):
    """Model for list of devices"""
    devices: List[DeviceResponse]
    total: int


class DetectedDevice(BaseModel):
    """Model for auto-detected device"""
    device_type: DeviceType
    serial_number: Optional[str] = None
    name: str
    index: Optional[int] = None


class DetectedDevicesResponse(BaseModel):
    """Response for device detection"""
    devices: List[DetectedDevice]
    rtlsdr_available: bool
    hackrf_available: bool


class DeviceInfo(BaseModel):
    """Detailed device information"""
    device_type: DeviceType
    serial_number: Optional[str]
    name: str
    min_frequency: float = Field(description="Minimum frequency in Hz")
    max_frequency: float = Field(description="Maximum frequency in Hz")
    min_sample_rate: float = Field(description="Minimum sample rate in Hz")
    max_sample_rate: float = Field(description="Maximum sample rate in Hz")
    supported_gains: List[int] = Field(default_factory=list, description="Supported gain values in dB")
