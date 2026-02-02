"""
Core Module

This module provides core business logic, configuration, and
orchestration for the RF Spectrum Monitor application.
"""

from .config import settings, get_settings, Settings
from .gps_handler import GPSHandler, GPSLocation, GPSMode, calculate_grid_points, format_coordinates
from .signal_processor import SignalProcessor, SignalPeak, SpectrumStatistics
from .survey_manager import (
    SurveyManager,
    SurveyConfig,
    SurveyState,
    get_survey_manager,
)
from .task_queue import (
    TaskManager,
    TaskInfo,
    TaskStatus,
    TaskType,
    get_task_manager,
    submit_survey_task,
    submit_export_task,
)

__all__ = [
    # Config
    'settings',
    'get_settings',
    'Settings',
    # GPS
    'GPSHandler',
    'GPSLocation',
    'GPSMode',
    'calculate_grid_points',
    'format_coordinates',
    # Signal Processing
    'SignalProcessor',
    'SignalPeak',
    'SpectrumStatistics',
    # Survey Management
    'SurveyManager',
    'SurveyConfig',
    'SurveyState',
    'get_survey_manager',
    # Task Queue
    'TaskManager',
    'TaskInfo',
    'TaskStatus',
    'TaskType',
    'get_task_manager',
    'submit_survey_task',
    'submit_export_task',
]
