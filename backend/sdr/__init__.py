"""
SDR (Software Defined Radio) Module

This module provides the abstraction layer for working with various
SDR devices including HackRF, RTL-SDR, and simulated devices.

Example usage:
    from backend.sdr import create_scanner, ScanParameters

    # Create a mock scanner for testing
    device, scanner = create_scanner('mock')
    device.open()

    # Perform a frequency sweep
    params = ScanParameters(
        start_freq=88e6,
        stop_freq=108e6,
        sample_rate=2.4e6,
        gain=20
    )
    result = scanner.single_sweep(params)

    # Detect signals
    signals = scanner.detect_peaks(result.frequencies, result.power_dbm)
    for sig in signals:
        print(f"Signal at {sig.frequency/1e6:.2f} MHz: {sig.power_dbm:.1f} dBm")

    device.close()
"""

# Base classes and types
from .base import (
    SDRDevice,
    DeviceType,
    DeviceInfo,
    ScanParameters,
    SpectrumData,
    SweepResult,
    DetectedSignal,
    SDRError,
    DeviceNotFoundError,
    DeviceConnectionError,
    FrequencyOutOfRangeError,
    SampleRateError,
)

# Device implementations
from .mock import MockSDRDevice, MockSignal, MockScenario
from .rtlsdr import RTLSDRDevice, RTLSDR_AVAILABLE
from .hackrf import HackRFDevice, HACKRF_AVAILABLE

# Scanner
from .scanner import (
    SpectrumScanner,
    ScannerConfig,
    create_scanner,
)

__all__ = [
    # Base
    'SDRDevice',
    'DeviceType',
    'DeviceInfo',
    'ScanParameters',
    'SpectrumData',
    'SweepResult',
    'DetectedSignal',
    'SDRError',
    'DeviceNotFoundError',
    'DeviceConnectionError',
    'FrequencyOutOfRangeError',
    'SampleRateError',

    # Devices
    'MockSDRDevice',
    'MockSignal',
    'MockScenario',
    'RTLSDRDevice',
    'HackRFDevice',
    'RTLSDR_AVAILABLE',
    'HACKRF_AVAILABLE',

    # Scanner
    'SpectrumScanner',
    'ScannerConfig',
    'create_scanner',
]


def detect_all_devices() -> list:
    """
    Detect all available SDR devices.

    Returns:
        List of device info dictionaries
    """
    devices = []

    # Check for RTL-SDR devices
    if RTLSDR_AVAILABLE:
        devices.extend(RTLSDRDevice.detect_devices())

    # Check for HackRF devices
    if HACKRF_AVAILABLE:
        devices.extend(HackRFDevice.detect_devices())

    # Always include mock device for testing
    devices.extend(MockSDRDevice.detect_devices())

    return devices


def get_device(device_type: str, device_id=None) -> SDRDevice:
    """
    Factory function to create an SDR device instance.

    Args:
        device_type: Type of device ('mock', 'rtlsdr', 'hackrf')
        device_id: Optional device identifier

    Returns:
        SDR device instance (not opened)
    """
    if device_type == 'mock':
        return MockSDRDevice(device_id=device_id or 'mock_0')
    elif device_type == 'rtlsdr':
        if not RTLSDR_AVAILABLE:
            raise ImportError("RTL-SDR support not available (pyrtlsdr not installed)")
        return RTLSDRDevice(device_index=int(device_id or 0))
    elif device_type == 'hackrf':
        if not HACKRF_AVAILABLE:
            raise ImportError("HackRF support not available (hackrf library not installed)")
        return HackRFDevice(serial_number=device_id)
    else:
        raise ValueError(f"Unknown device type: {device_type}")
