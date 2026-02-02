"""
Export API Models

Pydantic models for data export API requests and responses.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


class ExportType(str, Enum):
    """Export format types"""
    CSV = "csv"
    GEOPACKAGE = "geopackage"
    JSON = "json"


class ExportStatus(str, Enum):
    """Export job status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ExportParameters(BaseModel):
    """Parameters for export operation"""
    include_measurements: bool = Field(default=True, description="Include all measurements")
    include_signals: bool = Field(default=True, description="Include signals of interest")
    include_locations: bool = Field(default=True, description="Include survey locations")
    frequency_range: Optional[List[float]] = Field(None, description="[start_freq, stop_freq] filter")
    time_range: Optional[List[datetime]] = Field(None, description="[start_time, end_time] filter")

    # GeoPackage specific
    create_heatmap: bool = Field(default=False, description="Create interpolated heatmap layer")
    heatmap_frequency: Optional[float] = Field(None, description="Frequency for heatmap generation")
    create_frequency_layers: bool = Field(default=False, description="Create separate layers per frequency band")
    frequency_bands: Optional[List[List[float]]] = Field(None, description="Frequency bands for layer creation")


class ExportRequest(BaseModel):
    """Request to create an export"""
    survey_id: int = Field(..., description="Survey to export")
    export_type: ExportType = Field(..., description="Export format")
    parameters: Optional[ExportParameters] = Field(default_factory=ExportParameters)


class ExportJobResponse(BaseModel):
    """Response for export job"""
    id: int
    survey_id: Optional[int]
    export_type: ExportType
    status: ExportStatus
    file_name: Optional[str]
    file_path: Optional[str]
    file_size: Optional[int] = Field(None, description="File size in bytes")
    progress: float = Field(ge=0, le=100)
    error_message: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class ExportJobListResponse(BaseModel):
    """List of export jobs"""
    jobs: List[ExportJobResponse]
    total: int
