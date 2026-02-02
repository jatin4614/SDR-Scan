"""
Device Management API Routes

Endpoints for managing SDR devices (HackRF, RTL-SDR, etc.)
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger

from ..models import (
    DeviceType,
    DeviceCreate,
    DeviceUpdate,
    DeviceResponse,
    DeviceListResponse,
    DetectedDevice,
    DetectedDevicesResponse,
    DeviceInfo,
)
from ..dependencies import get_device_repository, CommonQueryParams, common_parameters
from ...storage.repositories import DeviceRepository
from ...storage.database import DeviceTypeEnum
from ...sdr import (
    detect_all_devices,
    RTLSDR_AVAILABLE,
    HACKRF_AVAILABLE,
    get_device as get_sdr_device,
)

router = APIRouter()


def _convert_device_type(api_type: DeviceType) -> DeviceTypeEnum:
    """Convert API DeviceType to database DeviceTypeEnum"""
    return DeviceTypeEnum[api_type.value.upper()]


def _convert_to_api_type(db_type: DeviceTypeEnum) -> DeviceType:
    """Convert database DeviceTypeEnum to API DeviceType"""
    return DeviceType(db_type.value.lower())


@router.get("", response_model=DeviceListResponse)
async def list_devices(
    active_only: bool = True,
    device_type: DeviceType = None,
    params: CommonQueryParams = Depends(common_parameters),
    repo: DeviceRepository = Depends(get_device_repository)
):
    """
    List all configured SDR devices.

    - **active_only**: Only return active devices (default: true)
    - **device_type**: Filter by device type
    """
    if device_type:
        devices = repo.get_by_type(_convert_device_type(device_type))
    else:
        devices = repo.get_all(active_only=active_only)

    return DeviceListResponse(
        devices=[DeviceResponse.model_validate(d) for d in devices],
        total=len(devices)
    )


@router.get("/detect", response_model=DetectedDevicesResponse)
async def detect_devices():
    """
    Auto-detect connected SDR devices.

    Scans for all connected HackRF and RTL-SDR devices.
    Always includes a mock device for testing.
    """
    detected = detect_all_devices()

    devices = []
    for d in detected:
        devices.append(DetectedDevice(
            device_type=DeviceType(d['type']),
            serial_number=d.get('serial'),
            name=d.get('name', f"{d['type']} device"),
            index=d.get('index')
        ))

    return DetectedDevicesResponse(
        devices=devices,
        rtlsdr_available=RTLSDR_AVAILABLE,
        hackrf_available=HACKRF_AVAILABLE
    )


@router.post("", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED)
async def create_device(
    device: DeviceCreate,
    repo: DeviceRepository = Depends(get_device_repository)
):
    """
    Register a new SDR device.

    Create a device configuration that can be used for surveys.
    """
    # Check for duplicate serial number
    if device.serial_number:
        existing = repo.get_by_serial(device.serial_number)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Device with serial number '{device.serial_number}' already exists"
            )

    try:
        db_device = repo.create(
            name=device.name,
            device_type=_convert_device_type(device.device_type),
            serial_number=device.serial_number,
            sample_rate=device.sample_rate,
            gain=device.gain,
            calibration_offset=device.calibration_offset
        )
        repo.commit()
        logger.info(f"Created device: {db_device.id} - {db_device.name}")
        return DeviceResponse.model_validate(db_device)
    except Exception as e:
        logger.error(f"Failed to create device: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device(
    device_id: int,
    repo: DeviceRepository = Depends(get_device_repository)
):
    """
    Get device details by ID.
    """
    device = repo.get_by_id(device_id)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device {device_id} not found"
        )
    return DeviceResponse.model_validate(device)


@router.get("/{device_id}/info", response_model=DeviceInfo)
async def get_device_info(
    device_id: int,
    repo: DeviceRepository = Depends(get_device_repository)
):
    """
    Get detailed device information including capabilities.

    Returns frequency range, sample rates, and supported gains
    for the device type.
    """
    device = repo.get_by_id(device_id)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device {device_id} not found"
        )

    try:
        # Get SDR device to query capabilities
        sdr_device = get_sdr_device(
            device.device_type.value.lower(),
            device.serial_number
        )
        info = sdr_device.get_device_info()

        return DeviceInfo(
            device_type=DeviceType(device.device_type.value.lower()),
            serial_number=device.serial_number,
            name=device.name,
            min_frequency=info.min_freq,
            max_frequency=info.max_freq,
            min_sample_rate=info.min_sample_rate,
            max_sample_rate=info.max_sample_rate,
            supported_gains=info.supported_gains
        )
    except Exception as e:
        logger.warning(f"Could not get device info: {e}")
        # Return default info based on device type
        if device.device_type == DeviceTypeEnum.RTLSDR:
            return DeviceInfo(
                device_type=DeviceType.RTLSDR,
                serial_number=device.serial_number,
                name=device.name,
                min_frequency=24e6,
                max_frequency=1766e6,
                min_sample_rate=225e3,
                max_sample_rate=3.2e6,
                supported_gains=[0, 10, 20, 30, 40, 50]
            )
        elif device.device_type == DeviceTypeEnum.HACKRF:
            return DeviceInfo(
                device_type=DeviceType.HACKRF,
                serial_number=device.serial_number,
                name=device.name,
                min_frequency=1e6,
                max_frequency=6000e6,
                min_sample_rate=2e6,
                max_sample_rate=20e6,
                supported_gains=list(range(0, 103, 2))
            )
        else:
            return DeviceInfo(
                device_type=DeviceType.MOCK,
                serial_number=device.serial_number,
                name=device.name,
                min_frequency=1e6,
                max_frequency=6000e6,
                min_sample_rate=225e3,
                max_sample_rate=20e6,
                supported_gains=list(range(0, 51, 10))
            )


@router.put("/{device_id}", response_model=DeviceResponse)
async def update_device(
    device_id: int,
    device_update: DeviceUpdate,
    repo: DeviceRepository = Depends(get_device_repository)
):
    """
    Update device configuration.
    """
    device = repo.get_by_id(device_id)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device {device_id} not found"
        )

    # Build update dict from non-None values
    update_data = device_update.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update"
        )

    updated = repo.update(device_id, **update_data)
    repo.commit()
    return DeviceResponse.model_validate(updated)


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device(
    device_id: int,
    hard: bool = False,
    repo: DeviceRepository = Depends(get_device_repository)
):
    """
    Delete a device.

    - **hard**: If true, permanently delete. Otherwise, soft delete (set inactive).
    """
    device = repo.get_by_id(device_id)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device {device_id} not found"
        )

    if hard:
        repo.hard_delete(device_id)
    else:
        repo.delete(device_id)
    repo.commit()
    logger.info(f"Deleted device: {device_id} (hard={hard})")


@router.post("/{device_id}/test")
async def test_device(
    device_id: int,
    repo: DeviceRepository = Depends(get_device_repository)
):
    """
    Test device connectivity.

    Attempts to open the device and read samples to verify it's working.
    """
    device = repo.get_by_id(device_id)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device {device_id} not found"
        )

    try:
        sdr_device = get_sdr_device(
            device.device_type.value.lower(),
            device.serial_number
        )
        sdr_device.open()
        sdr_device.set_center_freq(100e6)
        samples = sdr_device.read_samples(1024)
        sdr_device.close()

        return {
            "status": "success",
            "message": f"Device {device.name} is working",
            "samples_read": len(samples)
        }
    except Exception as e:
        logger.error(f"Device test failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Device test failed: {str(e)}"
        )
