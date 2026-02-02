"""
Export API Routes

Endpoints for exporting survey data to various formats (CSV, GeoPackage).
"""

from typing import List, Optional
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import FileResponse
from loguru import logger

from ..models import (
    ExportType,
    ExportStatus,
    ExportRequest,
    ExportJobResponse,
    ExportJobListResponse,
)
from ..dependencies import (
    get_export_repository,
    get_survey_repository,
    get_measurement_repository,
)
from ...storage.repositories import (
    ExportJobRepository,
    SurveyRepository,
    MeasurementRepository,
)
from ...storage.database import ExportTypeEnum, ExportStatusEnum
from ...core.config import settings

router = APIRouter()


def _convert_export_type(api_type: ExportType) -> ExportTypeEnum:
    """Convert API ExportType to database enum"""
    return ExportTypeEnum[api_type.value.upper()]


@router.get("/jobs", response_model=ExportJobListResponse)
async def list_export_jobs(
    survey_id: Optional[int] = None,
    status: Optional[ExportStatus] = None,
    repo: ExportJobRepository = Depends(get_export_repository)
):
    """
    List export jobs with optional filters.
    """
    if survey_id:
        jobs = repo.get_by_survey(survey_id)
    else:
        jobs = repo.get_pending()

    # Filter by status if provided
    if status:
        db_status = ExportStatusEnum[status.value.upper()]
        jobs = [j for j in jobs if j.status == db_status]

    return ExportJobListResponse(
        jobs=[ExportJobResponse.model_validate(j) for j in jobs],
        total=len(jobs)
    )


@router.get("/jobs/{job_id}", response_model=ExportJobResponse)
async def get_export_job(
    job_id: int,
    repo: ExportJobRepository = Depends(get_export_repository)
):
    """
    Get export job status and details.
    """
    job = repo.get_by_id(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Export job {job_id} not found"
        )
    return ExportJobResponse.model_validate(job)


@router.post("/csv", response_model=ExportJobResponse)
async def export_csv(
    request: ExportRequest,
    background_tasks: BackgroundTasks,
    export_repo: ExportJobRepository = Depends(get_export_repository),
    survey_repo: SurveyRepository = Depends(get_survey_repository)
):
    """
    Export survey data to CSV format.

    Creates an export job that runs in the background.
    """
    survey = survey_repo.get_by_id(request.survey_id)
    if not survey:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Survey {request.survey_id} not found"
        )

    # Create export job
    import json
    params_json = json.dumps(request.parameters.model_dump() if request.parameters else {})

    job = export_repo.create(
        export_type=ExportTypeEnum.CSV,
        survey_id=request.survey_id,
        parameters=params_json
    )
    export_repo.commit()

    # Add background task
    background_tasks.add_task(
        run_csv_export,
        job.id,
        request.survey_id
    )

    logger.info(f"Created CSV export job: {job.id} for survey {request.survey_id}")
    return ExportJobResponse.model_validate(job)


@router.post("/geopackage", response_model=ExportJobResponse)
async def export_geopackage(
    request: ExportRequest,
    background_tasks: BackgroundTasks,
    export_repo: ExportJobRepository = Depends(get_export_repository),
    survey_repo: SurveyRepository = Depends(get_survey_repository)
):
    """
    Export survey data to GeoPackage format for QGIS.

    Creates an export job that runs in the background.
    Optional parameters:
    - create_heatmap: Create interpolated heatmap layer
    - create_frequency_layers: Create separate layers per frequency band
    """
    survey = survey_repo.get_by_id(request.survey_id)
    if not survey:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Survey {request.survey_id} not found"
        )

    # Create export job
    import json
    params_json = json.dumps(request.parameters.model_dump() if request.parameters else {})

    job = export_repo.create(
        export_type=ExportTypeEnum.GEOPACKAGE,
        survey_id=request.survey_id,
        parameters=params_json
    )
    export_repo.commit()

    # Add background task
    background_tasks.add_task(
        run_geopackage_export,
        job.id,
        request.survey_id,
        request.parameters.model_dump() if request.parameters else {}
    )

    logger.info(f"Created GeoPackage export job: {job.id} for survey {request.survey_id}")
    return ExportJobResponse.model_validate(job)


@router.get("/download/{job_id}")
async def download_export(
    job_id: int,
    repo: ExportJobRepository = Depends(get_export_repository)
):
    """
    Download completed export file.
    """
    job = repo.get_by_id(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Export job {job_id} not found"
        )

    if job.status != ExportStatusEnum.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Export job not completed. Status: {job.status.value}"
        )

    if not job.file_path or not Path(job.file_path).exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export file not found"
        )

    return FileResponse(
        path=job.file_path,
        filename=job.file_name,
        media_type="application/octet-stream"
    )


@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_export_job(
    job_id: int,
    delete_file: bool = True,
    repo: ExportJobRepository = Depends(get_export_repository)
):
    """
    Delete an export job and optionally its file.
    """
    job = repo.get_by_id(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Export job {job_id} not found"
        )

    # Delete file if it exists and requested
    if delete_file and job.file_path:
        file_path = Path(job.file_path)
        if file_path.exists():
            file_path.unlink()
            logger.info(f"Deleted export file: {job.file_path}")

    repo.delete(job_id)
    repo.commit()


# Background task functions
async def run_csv_export(job_id: int, survey_id: int):
    """Background task to run CSV export"""
    from ...storage.database import get_session
    from ...storage.repositories import ExportJobRepository, MeasurementRepository, SurveyRepository
    import csv
    import os

    session = get_session()
    export_repo = ExportJobRepository(session)
    measurement_repo = MeasurementRepository(session)
    survey_repo = SurveyRepository(session)

    try:
        # Update status
        export_repo.update_status(job_id, ExportStatusEnum.PROCESSING)
        session.commit()

        survey = survey_repo.get_by_id(survey_id)
        measurements = measurement_repo.get_by_survey(survey_id, limit=100000)

        # Create export directory
        export_dir = Path(settings.export.directory)
        export_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"survey_{survey_id}_{timestamp}.csv"
        filepath = export_dir / filename

        # Write CSV
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'frequency_hz', 'power_dbm', 'bandwidth_hz',
                'latitude', 'longitude', 'altitude',
                'timestamp', 'noise_floor_dbm', 'snr_db'
            ])

            for m in measurements:
                writer.writerow([
                    m.frequency, m.power_dbm, m.bandwidth,
                    m.latitude, m.longitude, m.altitude,
                    m.timestamp.isoformat() if m.timestamp else '',
                    m.noise_floor_dbm, m.snr_db
                ])

        file_size = os.path.getsize(filepath)

        export_repo.update_status(
            job_id,
            ExportStatusEnum.COMPLETED,
            file_path=str(filepath),
            file_size=file_size
        )
        session.commit()
        logger.info(f"CSV export completed: {filepath}")

    except Exception as e:
        logger.error(f"CSV export failed: {e}")
        export_repo.update_status(
            job_id,
            ExportStatusEnum.FAILED,
            error_message=str(e)
        )
        session.commit()
    finally:
        session.close()


async def run_geopackage_export(job_id: int, survey_id: int, parameters: dict):
    """Background task to run GeoPackage export"""
    from ...storage.database import get_session
    from ...storage.repositories import ExportJobRepository, MeasurementRepository, SurveyRepository
    import os

    session = get_session()
    export_repo = ExportJobRepository(session)
    measurement_repo = MeasurementRepository(session)
    survey_repo = SurveyRepository(session)

    try:
        # Update status
        export_repo.update_status(job_id, ExportStatusEnum.PROCESSING)
        session.commit()

        survey = survey_repo.get_by_id(survey_id)
        measurements = measurement_repo.get_geo_referenced(survey_id, limit=100000)

        if not measurements:
            raise ValueError("No geo-referenced measurements found")

        # Create export directory
        export_dir = Path(settings.export.directory)
        export_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"survey_{survey_id}_{timestamp}.gpkg"
        filepath = export_dir / filename

        # Try to use geopandas
        try:
            import geopandas as gpd
            from shapely.geometry import Point
            import pandas as pd

            # Convert to DataFrame
            data = []
            for m in measurements:
                data.append({
                    'frequency_hz': m.frequency,
                    'frequency_mhz': m.frequency / 1e6,
                    'power_dbm': m.power_dbm,
                    'bandwidth_hz': m.bandwidth,
                    'latitude': m.latitude,
                    'longitude': m.longitude,
                    'altitude': m.altitude,
                    'timestamp': m.timestamp,
                    'noise_floor_dbm': m.noise_floor_dbm,
                    'snr_db': m.snr_db
                })

            df = pd.DataFrame(data)
            geometry = [Point(xy) for xy in zip(df.longitude, df.latitude)]
            gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")

            # Write main layer
            gdf.to_file(str(filepath), driver='GPKG', layer='measurements')

            # Create frequency band layers if requested
            if parameters.get('create_frequency_layers'):
                freq_bands = parameters.get('frequency_bands', [
                    [88e6, 108e6],    # FM broadcast
                    [430e6, 440e6],   # 70cm amateur
                    [2400e6, 2500e6]  # 2.4 GHz ISM
                ])
                for band in freq_bands:
                    band_data = gdf[
                        (gdf.frequency_hz >= band[0]) &
                        (gdf.frequency_hz <= band[1])
                    ]
                    if not band_data.empty:
                        layer_name = f'freq_{band[0]/1e6:.0f}_{band[1]/1e6:.0f}_MHz'
                        band_data.to_file(str(filepath), driver='GPKG', layer=layer_name)

        except ImportError:
            # Fallback: create a simple JSON file
            import json
            filepath = filepath.with_suffix('.json')
            data = [{
                'frequency_hz': m.frequency,
                'power_dbm': m.power_dbm,
                'latitude': m.latitude,
                'longitude': m.longitude,
                'timestamp': m.timestamp.isoformat() if m.timestamp else None
            } for m in measurements]
            with open(filepath, 'w') as f:
                json.dump({'type': 'FeatureCollection', 'features': data}, f)

        file_size = os.path.getsize(filepath)

        export_repo.update_status(
            job_id,
            ExportStatusEnum.COMPLETED,
            file_path=str(filepath),
            file_size=file_size
        )
        session.commit()
        logger.info(f"GeoPackage export completed: {filepath}")

    except Exception as e:
        logger.error(f"GeoPackage export failed: {e}")
        export_repo.update_status(
            job_id,
            ExportStatusEnum.FAILED,
            error_message=str(e)
        )
        session.commit()
    finally:
        session.close()
