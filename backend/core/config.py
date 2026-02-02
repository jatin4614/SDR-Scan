"""
Application Configuration

This module provides centralized configuration management using Pydantic Settings.
Configuration can be loaded from environment variables or .env files.
"""

from typing import Optional, List
from pathlib import Path
from functools import lru_cache
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# Get project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent


class DatabaseSettings(BaseSettings):
    """Database configuration"""
    url: str = Field(
        default=f"sqlite:///{PROJECT_ROOT}/data/database/spectrum.db",
        description="Database connection URL"
    )
    echo: bool = Field(default=False, description="Echo SQL statements")
    pool_size: int = Field(default=5, description="Connection pool size")

    model_config = SettingsConfigDict(env_prefix="DATABASE_")


class APISettings(BaseSettings):
    """API server configuration"""
    host: str = Field(default="0.0.0.0", description="API host")
    port: int = Field(default=8000, description="API port")
    reload: bool = Field(default=False, description="Auto-reload on changes")
    workers: int = Field(default=4, description="Number of workers")
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        description="Allowed CORS origins"
    )

    model_config = SettingsConfigDict(env_prefix="API_")

    @field_validator('cors_origins', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',')]
        return v


class SDRSettings(BaseSettings):
    """SDR device configuration"""
    default_device: str = Field(default="mock", description="Default SDR device type")
    sample_rate: int = Field(default=2400000, description="Default sample rate (Hz)")
    gain: int = Field(default=20, description="Default gain (dB)")
    integration_time: float = Field(default=0.1, description="Integration time (seconds)")
    fft_size: int = Field(default=1024, description="FFT window size")

    # HackRF specific
    hackrf_lna_gain: int = Field(default=16, description="HackRF LNA gain")
    hackrf_vga_gain: int = Field(default=20, description="HackRF VGA gain")
    hackrf_sample_rate: int = Field(default=8000000, description="HackRF sample rate")

    # RTL-SDR specific
    rtlsdr_ppm_correction: int = Field(default=0, description="RTL-SDR PPM correction")

    model_config = SettingsConfigDict(env_prefix="SDR_")


class GPSSettings(BaseSettings):
    """GPS configuration"""
    mode: str = Field(default="manual", description="GPS mode: manual, gpsd, mock")
    gpsd_host: str = Field(default="localhost", description="GPSD host")
    gpsd_port: int = Field(default=2947, description="GPSD port")
    mock_default_lat: float = Field(default=28.6139, description="Mock default latitude")
    mock_default_lon: float = Field(default=77.2090, description="Mock default longitude")

    model_config = SettingsConfigDict(env_prefix="GPS_")


class ScanningSettings(BaseSettings):
    """Spectrum scanning configuration"""
    min_frequency: int = Field(default=30000000, description="Minimum frequency (Hz)")
    max_frequency: int = Field(default=6000000000, description="Maximum frequency (Hz)")
    max_sweep_time: int = Field(default=60, description="Maximum sweep time (seconds)")
    min_step_size: int = Field(default=1000, description="Minimum step size (Hz)")
    default_bandwidth: int = Field(default=200000, description="Default bandwidth (Hz)")

    model_config = SettingsConfigDict(env_prefix="SCANNING_")


class ExportSettings(BaseSettings):
    """Export configuration"""
    directory: str = Field(
        default=str(PROJECT_ROOT / "data" / "exports"),
        description="Export directory"
    )
    max_file_size: int = Field(
        default=1073741824,  # 1GB
        description="Maximum export file size"
    )

    model_config = SettingsConfigDict(env_prefix="EXPORT_")


class CelerySettings(BaseSettings):
    """Celery task queue configuration"""
    broker_url: str = Field(
        default="redis://localhost:6379/0",
        description="Celery broker URL"
    )
    result_backend: str = Field(
        default="redis://localhost:6379/0",
        description="Celery result backend"
    )

    model_config = SettingsConfigDict(env_prefix="CELERY_")


class LoggingSettings(BaseSettings):
    """Logging configuration"""
    level: str = Field(default="INFO", description="Log level")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format"
    )
    file: Optional[str] = Field(
        default=str(PROJECT_ROOT / "logs" / "spectrum_monitor.log"),
        description="Log file path"
    )

    model_config = SettingsConfigDict(env_prefix="LOG_")


class Settings(BaseSettings):
    """Main application settings"""

    # Application info
    app_name: str = Field(default="RF Spectrum Monitor", description="Application name")
    app_version: str = Field(default="1.0.0", description="Application version")
    debug: bool = Field(default=False, description="Debug mode")

    # Sub-settings
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    api: APISettings = Field(default_factory=APISettings)
    sdr: SDRSettings = Field(default_factory=SDRSettings)
    gps: GPSSettings = Field(default_factory=GPSSettings)
    scanning: ScanningSettings = Field(default_factory=ScanningSettings)
    export: ExportSettings = Field(default_factory=ExportSettings)
    celery: CelerySettings = Field(default_factory=CelerySettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached application settings.

    Returns:
        Settings instance (cached)
    """
    return Settings()


# Convenience access to settings
settings = get_settings()
