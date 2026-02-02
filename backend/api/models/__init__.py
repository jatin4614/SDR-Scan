"""
API Models Module

Pydantic models for API request/response schemas.
"""

# Device models
from .device import (
    DeviceType,
    DeviceBase,
    DeviceCreate,
    DeviceUpdate,
    DeviceResponse,
    DeviceListResponse,
    DetectedDevice,
    DetectedDevicesResponse,
    DeviceInfo,
)

# Survey models
from .survey import (
    SurveyType,
    SurveyStatus,
    LocationType,
    GPSMode,
    LocationBase,
    LocationCreate,
    LocationResponse,
    SurveyBase,
    SurveyCreate,
    SurveyUpdate,
    SurveyResponse,
    SurveyDetailResponse,
    SurveyListResponse,
    SurveyStatistics,
    SurveyStartRequest,
    SurveyStatusUpdate,
    SurveyProgressResponse,
)

# Spectrum models
from .spectrum import (
    MeasurementBase,
    MeasurementCreate,
    MeasurementResponse,
    MeasurementListResponse,
    MeasurementQuery,
    FrequencyStatistics,
    SpectrumPoint,
    SpectrumData,
    SweepResult,
    DetectedSignal,
    ScanRequest,
    ScanResponse,
    LiveSpectrumRequest,
    SignalOfInterestBase,
    SignalOfInterestCreate,
    SignalOfInterestResponse,
    SignalListResponse,
)

# Export models
from .export import (
    ExportType,
    ExportStatus,
    ExportParameters,
    ExportRequest,
    ExportJobResponse,
    ExportJobListResponse,
)

__all__ = [
    # Device
    'DeviceType', 'DeviceBase', 'DeviceCreate', 'DeviceUpdate',
    'DeviceResponse', 'DeviceListResponse', 'DetectedDevice',
    'DetectedDevicesResponse', 'DeviceInfo',

    # Survey
    'SurveyType', 'SurveyStatus', 'LocationType', 'GPSMode',
    'LocationBase', 'LocationCreate', 'LocationResponse',
    'SurveyBase', 'SurveyCreate', 'SurveyUpdate',
    'SurveyResponse', 'SurveyDetailResponse', 'SurveyListResponse',
    'SurveyStatistics', 'SurveyStartRequest', 'SurveyStatusUpdate',
    'SurveyProgressResponse',

    # Spectrum
    'MeasurementBase', 'MeasurementCreate', 'MeasurementResponse',
    'MeasurementListResponse', 'MeasurementQuery', 'FrequencyStatistics',
    'SpectrumPoint', 'SpectrumData', 'SweepResult', 'DetectedSignal',
    'ScanRequest', 'ScanResponse', 'LiveSpectrumRequest',
    'SignalOfInterestBase', 'SignalOfInterestCreate',
    'SignalOfInterestResponse', 'SignalListResponse',

    # Export
    'ExportType', 'ExportStatus', 'ExportParameters',
    'ExportRequest', 'ExportJobResponse', 'ExportJobListResponse',
]
