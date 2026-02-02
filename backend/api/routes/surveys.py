"""
Survey Management API Routes

Endpoints for creating, managing, and executing spectrum surveys.
"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from loguru import logger

from ..models import (
    SurveyType,
    SurveyStatus,
    LocationCreate,
    LocationResponse,
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
from ..dependencies import (
    get_survey_repository,
    get_location_repository,
    get_device_repository,
    get_measurement_repository,
    CommonQueryParams,
    common_parameters,
)
from ...storage.repositories import (
    SurveyRepository,
    LocationRepository,
    DeviceRepository,
    MeasurementRepository,
)
from ...storage.database import SurveyTypeEnum, SurveyStatusEnum, LocationTypeEnum
from ...core.survey_manager import get_survey_manager, SurveyConfig, SurveyStatus as SurveyManagerStatus
from ...core.gps_handler import GPSMode, GPSLocation
from ...core.task_queue import get_task_manager, TaskType

router = APIRouter()


def _convert_survey_type(api_type: SurveyType) -> SurveyTypeEnum:
    """Convert API SurveyType to database enum"""
    return SurveyTypeEnum[api_type.value.upper()]


def _convert_survey_status(api_status: SurveyStatus) -> SurveyStatusEnum:
    """Convert API SurveyStatus to database enum"""
    return SurveyStatusEnum[api_status.value.upper()]


def _convert_location_type(api_type) -> LocationTypeEnum:
    """Convert API LocationType to database enum"""
    return LocationTypeEnum[api_type.value.upper()]


@router.get("", response_model=SurveyListResponse)
async def list_surveys(
    status: Optional[SurveyStatus] = None,
    survey_type: Optional[SurveyType] = None,
    params: CommonQueryParams = Depends(common_parameters),
    repo: SurveyRepository = Depends(get_survey_repository)
):
    """
    List all surveys with optional filters.

    - **status**: Filter by survey status
    - **survey_type**: Filter by survey type
    """
    db_status = _convert_survey_status(status) if status else None
    db_type = _convert_survey_type(survey_type) if survey_type else None

    surveys = repo.get_all(
        status=db_status,
        survey_type=db_type,
        limit=params.limit,
        offset=params.offset
    )

    return SurveyListResponse(
        surveys=[SurveyResponse.model_validate(s) for s in surveys],
        total=len(surveys)
    )


@router.get("/active", response_model=List[SurveyResponse])
async def get_active_surveys(
    repo: SurveyRepository = Depends(get_survey_repository)
):
    """
    Get all currently running surveys.
    """
    surveys = repo.get_active()
    return [SurveyResponse.model_validate(s) for s in surveys]


@router.post("", response_model=SurveyResponse, status_code=status.HTTP_201_CREATED)
async def create_survey(
    survey: SurveyCreate,
    survey_repo: SurveyRepository = Depends(get_survey_repository),
    location_repo: LocationRepository = Depends(get_location_repository),
    device_repo: DeviceRepository = Depends(get_device_repository)
):
    """
    Create a new spectrum survey.

    For multi-location surveys, include locations in the request body.
    """
    # Validate device exists if specified
    if survey.device_id:
        device = device_repo.get_by_id(survey.device_id)
        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Device {survey.device_id} not found"
            )

    try:
        db_survey = survey_repo.create(
            name=survey.name,
            survey_type=_convert_survey_type(survey.survey_type),
            start_frequency=survey.start_frequency,
            stop_frequency=survey.stop_frequency,
            device_id=survey.device_id,
            description=survey.description,
            step_size=survey.step_size,
            bandwidth=survey.bandwidth,
            integration_time=survey.integration_time
        )
        survey_repo.commit()

        # Create locations for multi-location surveys
        if survey.locations and survey.survey_type == SurveyType.MULTI_LOCATION:
            for i, loc in enumerate(survey.locations):
                location_repo.create(
                    survey_id=db_survey.id,
                    latitude=loc.latitude,
                    longitude=loc.longitude,
                    altitude=loc.altitude,
                    name=loc.name,
                    description=loc.description,
                    location_type=_convert_location_type(loc.location_type),
                    sequence_order=loc.sequence_order if loc.sequence_order else i
                )
            location_repo.commit()

        logger.info(f"Created survey: {db_survey.id} - {db_survey.name}")
        return SurveyResponse.model_validate(db_survey)

    except Exception as e:
        logger.error(f"Failed to create survey: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/{survey_id}", response_model=SurveyDetailResponse)
async def get_survey(
    survey_id: int,
    survey_repo: SurveyRepository = Depends(get_survey_repository),
    location_repo: LocationRepository = Depends(get_location_repository),
    measurement_repo: MeasurementRepository = Depends(get_measurement_repository)
):
    """
    Get detailed survey information including locations.
    """
    survey = survey_repo.get_by_id(survey_id)
    if not survey:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Survey {survey_id} not found"
        )

    locations = location_repo.get_by_survey(survey_id)
    measurement_count = measurement_repo.count_by_survey(survey_id)
    signal_count = len(survey.signals) if survey.signals else 0

    response = SurveyDetailResponse.model_validate(survey)
    response.locations = [LocationResponse.model_validate(l) for l in locations]
    response.measurement_count = measurement_count
    response.signal_count = signal_count

    return response


@router.get("/{survey_id}/statistics", response_model=SurveyStatistics)
async def get_survey_statistics(
    survey_id: int,
    repo: SurveyRepository = Depends(get_survey_repository)
):
    """
    Get survey statistics including measurement counts and power levels.
    """
    survey = repo.get_by_id(survey_id)
    if not survey:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Survey {survey_id} not found"
        )

    stats = repo.get_statistics(survey_id)
    return SurveyStatistics(**stats)


@router.get("/{survey_id}/progress", response_model=SurveyProgressResponse)
async def get_survey_progress(
    survey_id: int,
    repo: SurveyRepository = Depends(get_survey_repository)
):
    """
    Get real-time progress for a running survey.

    Returns current status, progress percentage, measurements collected,
    current frequency being scanned, and any errors.
    """
    survey = repo.get_by_id(survey_id)
    if not survey:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Survey {survey_id} not found"
        )

    # Get live progress from survey manager
    survey_manager = get_survey_manager()
    state = survey_manager.get_state()

    if state and state.survey_id == survey_id:
        # Survey is currently managed by survey manager
        elapsed = None
        if state.start_time:
            from datetime import datetime
            elapsed = (datetime.utcnow() - state.start_time).total_seconds()

        return SurveyProgressResponse(
            survey_id=survey_id,
            status=SurveyStatus(state.status.value),
            progress=state.progress,
            measurements_collected=state.measurements_collected,
            current_frequency=state.current_frequency,
            current_location=state.current_location.to_dict() if state.current_location else None,
            elapsed_seconds=elapsed,
            errors=state.errors
        )
    else:
        # Return database status for non-active surveys
        return SurveyProgressResponse(
            survey_id=survey_id,
            status=SurveyStatus(survey.status.value),
            progress=survey.progress,
            measurements_collected=0,  # Would need to query measurements table
            current_frequency=None,
            current_location=None,
            elapsed_seconds=None,
            errors=[survey.error_message] if survey.error_message else []
        )


@router.put("/{survey_id}", response_model=SurveyResponse)
async def update_survey(
    survey_id: int,
    survey_update: SurveyUpdate,
    repo: SurveyRepository = Depends(get_survey_repository)
):
    """
    Update survey configuration.

    Cannot update surveys that are currently running.
    """
    survey = repo.get_by_id(survey_id)
    if not survey:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Survey {survey_id} not found"
        )

    if survey.status == SurveyStatusEnum.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot update a running survey"
        )

    update_data = survey_update.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update"
        )

    updated = repo.update(survey_id, **update_data)
    repo.commit()
    return SurveyResponse.model_validate(updated)


@router.delete("/{survey_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_survey(
    survey_id: int,
    repo: SurveyRepository = Depends(get_survey_repository)
):
    """
    Delete a survey and all associated data.

    Cannot delete running surveys.
    """
    survey = repo.get_by_id(survey_id)
    if not survey:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Survey {survey_id} not found"
        )

    if survey.status == SurveyStatusEnum.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete a running survey. Stop it first."
        )

    repo.delete(survey_id)
    repo.commit()
    logger.info(f"Deleted survey: {survey_id}")


@router.post("/{survey_id}/start", response_model=SurveyResponse)
async def start_survey(
    survey_id: int,
    request: SurveyStartRequest = None,
    background_tasks: BackgroundTasks = None,
    survey_repo: SurveyRepository = Depends(get_survey_repository),
    device_repo: DeviceRepository = Depends(get_device_repository),
    location_repo: LocationRepository = Depends(get_location_repository)
):
    """
    Start executing a survey.

    For fixed surveys, optionally provide a starting location.
    The survey will run as a background task.
    """
    survey = survey_repo.get_by_id(survey_id)
    if not survey:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Survey {survey_id} not found"
        )

    if survey.status == SurveyStatusEnum.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Survey is already running"
        )

    if survey.status == SurveyStatusEnum.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Survey has already completed. Create a new survey to run again."
        )

    # Check if another survey is already running
    survey_manager = get_survey_manager()
    current_state = survey_manager.get_state()
    if current_state and current_state.status == SurveyManagerStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Another survey ({current_state.survey_id}) is already running. Stop it first."
        )

    # Check device
    device_id = request.device_id if request else None
    device_id = device_id or survey.device_id

    if not device_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No device specified. Provide device_id in request or survey."
        )

    device = device_repo.get_by_id(device_id)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device {device_id} not found"
        )

    # Determine GPS mode and initial location
    gps_mode = GPSMode.MANUAL
    initial_location = None

    if request and request.gps_mode:
        gps_mode = GPSMode(request.gps_mode)

    # Create location for fixed surveys if provided
    if request and request.location:
        initial_location = GPSLocation(
            latitude=request.location.latitude,
            longitude=request.location.longitude,
            altitude=request.location.altitude
        )
        # Also save to database
        if survey.survey_type == SurveyTypeEnum.FIXED:
            location_repo.create(
                survey_id=survey_id,
                latitude=request.location.latitude,
                longitude=request.location.longitude,
                altitude=request.location.altitude,
                name=request.location.name or "Survey Location",
                location_type=LocationTypeEnum.MANUAL
            )
            location_repo.commit()

    # Update survey status and device
    if device_id != survey.device_id:
        survey_repo.update(survey_id, device_id=device_id)
        survey_repo.commit()

    # Create survey configuration
    survey_config = SurveyConfig(
        survey_id=survey_id,
        device_id=device_id,
        start_frequency=survey.start_frequency,
        stop_frequency=survey.stop_frequency,
        step_size=survey.step_size or 100000,  # 100 kHz default
        bandwidth=survey.bandwidth or 200000,   # 200 kHz default
        integration_time=survey.integration_time or 0.1,
        survey_type=survey.survey_type.value,
    )

    # Start survey in background task
    def run_survey_task():
        """Execute survey in background thread"""
        try:
            manager = get_survey_manager()
            result = manager.start_survey(
                config=survey_config,
                gps_mode=gps_mode,
                initial_location=initial_location
            )

            # Update database status based on result
            from ...storage.database import get_session
            with get_session() as session:
                from ...storage.repositories import SurveyRepository
                repo = SurveyRepository(session)
                if result.get('status') == 'completed':
                    repo.update_status(survey_id, SurveyStatusEnum.COMPLETED)
                elif result.get('status') == 'failed':
                    repo.update_status(survey_id, SurveyStatusEnum.FAILED, result.get('error'))
                elif result.get('status') == 'stopped':
                    repo.update_status(survey_id, SurveyStatusEnum.PAUSED)
                repo.commit()

            return result
        except Exception as e:
            logger.error(f"Survey {survey_id} failed: {e}")
            from ...storage.database import get_session
            with get_session() as session:
                from ...storage.repositories import SurveyRepository
                repo = SurveyRepository(session)
                repo.update_status(survey_id, SurveyStatusEnum.FAILED, str(e))
                repo.commit()
            raise

    # Submit to task queue
    task_manager = get_task_manager()
    task_id = task_manager.submit(
        TaskType.SURVEY,
        run_survey_task,
        metadata={'survey_id': survey_id, 'device_id': device_id}
    )

    # Update survey status to running
    survey = survey_repo.update_status(survey_id, SurveyStatusEnum.RUNNING)
    survey_repo.commit()

    logger.info(f"Started survey: {survey_id} with device {device_id}, task_id: {task_id}")

    response = SurveyResponse.model_validate(survey)
    # Add task_id to response metadata (if needed)
    return response


@router.post("/{survey_id}/stop", response_model=SurveyResponse)
async def stop_survey(
    survey_id: int,
    repo: SurveyRepository = Depends(get_survey_repository)
):
    """
    Stop a running survey.
    """
    survey = repo.get_by_id(survey_id)
    if not survey:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Survey {survey_id} not found"
        )

    if survey.status != SurveyStatusEnum.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Survey is not running"
        )

    # Stop the survey via SurveyManager
    survey_manager = get_survey_manager()
    current_state = survey_manager.get_state()

    if current_state and current_state.survey_id == survey_id:
        survey_manager.stop_survey()
        logger.info(f"Stopped survey via manager: {survey_id}")
    else:
        logger.warning(f"Survey {survey_id} not found in manager, updating status only")

    survey = repo.update_status(survey_id, SurveyStatusEnum.PAUSED)
    repo.commit()

    logger.info(f"Stopped survey: {survey_id}")
    return SurveyResponse.model_validate(survey)


@router.post("/{survey_id}/pause", response_model=SurveyResponse)
async def pause_survey(
    survey_id: int,
    repo: SurveyRepository = Depends(get_survey_repository)
):
    """
    Pause a running survey. Can be resumed later.
    """
    survey = repo.get_by_id(survey_id)
    if not survey:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Survey {survey_id} not found"
        )

    if survey.status != SurveyStatusEnum.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Survey is not running"
        )

    # Pause the survey via SurveyManager
    survey_manager = get_survey_manager()
    current_state = survey_manager.get_state()

    if current_state and current_state.survey_id == survey_id:
        if survey_manager.pause_survey():
            logger.info(f"Paused survey via manager: {survey_id}")
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to pause survey"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Survey {survey_id} is not the currently active survey"
        )

    survey = repo.update_status(survey_id, SurveyStatusEnum.PAUSED)
    repo.commit()

    return SurveyResponse.model_validate(survey)


@router.post("/{survey_id}/resume", response_model=SurveyResponse)
async def resume_survey(
    survey_id: int,
    repo: SurveyRepository = Depends(get_survey_repository)
):
    """
    Resume a paused survey.
    """
    survey = repo.get_by_id(survey_id)
    if not survey:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Survey {survey_id} not found"
        )

    if survey.status != SurveyStatusEnum.PAUSED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Survey is not paused"
        )

    # Resume the survey via SurveyManager
    survey_manager = get_survey_manager()
    current_state = survey_manager.get_state()

    if current_state and current_state.survey_id == survey_id:
        if survey_manager.resume_survey():
            logger.info(f"Resumed survey via manager: {survey_id}")
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to resume survey"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Survey {survey_id} is not the currently active survey"
        )

    survey = repo.update_status(survey_id, SurveyStatusEnum.RUNNING)
    repo.commit()

    return SurveyResponse.model_validate(survey)


@router.post("/{survey_id}/complete", response_model=SurveyResponse)
async def complete_survey(
    survey_id: int,
    repo: SurveyRepository = Depends(get_survey_repository)
):
    """
    Mark a survey as completed.
    """
    survey = repo.get_by_id(survey_id)
    if not survey:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Survey {survey_id} not found"
        )

    # If survey is running, stop it first
    survey_manager = get_survey_manager()
    current_state = survey_manager.get_state()
    if current_state and current_state.survey_id == survey_id:
        survey_manager.stop_survey()

    survey = repo.update_status(survey_id, SurveyStatusEnum.COMPLETED)
    repo.commit()

    logger.info(f"Completed survey: {survey_id}")
    return SurveyResponse.model_validate(survey)


@router.put("/{survey_id}/status", response_model=SurveyResponse)
async def update_survey_status(
    survey_id: int,
    status_update: SurveyStatusUpdate,
    repo: SurveyRepository = Depends(get_survey_repository)
):
    """
    Manually update survey status.
    """
    survey = repo.get_by_id(survey_id)
    if not survey:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Survey {survey_id} not found"
        )

    survey = repo.update_status(
        survey_id,
        _convert_survey_status(status_update.status),
        status_update.error_message
    )
    repo.commit()

    return SurveyResponse.model_validate(survey)


# Location endpoints
@router.get("/{survey_id}/locations", response_model=List[LocationResponse])
async def get_survey_locations(
    survey_id: int,
    survey_repo: SurveyRepository = Depends(get_survey_repository),
    location_repo: LocationRepository = Depends(get_location_repository)
):
    """
    Get all locations for a survey.
    """
    survey = survey_repo.get_by_id(survey_id)
    if not survey:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Survey {survey_id} not found"
        )

    locations = location_repo.get_by_survey(survey_id)
    return [LocationResponse.model_validate(l) for l in locations]


@router.post("/{survey_id}/locations", response_model=LocationResponse, status_code=status.HTTP_201_CREATED)
async def add_survey_location(
    survey_id: int,
    location: LocationCreate,
    survey_repo: SurveyRepository = Depends(get_survey_repository),
    location_repo: LocationRepository = Depends(get_location_repository)
):
    """
    Add a location to a survey.
    """
    survey = survey_repo.get_by_id(survey_id)
    if not survey:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Survey {survey_id} not found"
        )

    db_location = location_repo.create(
        survey_id=survey_id,
        latitude=location.latitude,
        longitude=location.longitude,
        altitude=location.altitude,
        name=location.name,
        description=location.description,
        location_type=_convert_location_type(location.location_type),
        sequence_order=location.sequence_order
    )
    location_repo.commit()

    return LocationResponse.model_validate(db_location)


@router.delete("/{survey_id}/locations/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_survey_location(
    survey_id: int,
    location_id: int,
    location_repo: LocationRepository = Depends(get_location_repository)
):
    """
    Delete a location from a survey.
    """
    location = location_repo.get_by_id(location_id)
    if not location or location.survey_id != survey_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Location {location_id} not found in survey {survey_id}"
        )

    location_repo.delete(location_id)
    location_repo.commit()
