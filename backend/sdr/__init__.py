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

# Registry
from .registry import DeviceRegistry, get_device_registry

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
    'get_scanner',

    # Registry
    'DeviceRegistry',
    'get_device_registry',
]


_default_scanner: tuple = None


def get_scanner(device_type: str = 'mock', device_id: str = None) -> 'SpectrumScanner':
    """
    Get a ready-to-use scanner instance.

    Creates a device and scanner, opens the device, and returns the scanner.
    Caches the result so subsequent calls return the same scanner.

    For multi-device support, prefer using get_device_registry().acquire(db_id)
    instead. This function is kept for backward compatibility.

    Args:
        device_type: Type of device ('mock', 'rtlsdr', 'hackrf')
        device_id: Optional device identifier

    Returns:
        SpectrumScanner instance with an open device
    """
    global _default_scanner
    if _default_scanner is None:
        device, scanner = create_scanner(device_type, device_id)
        device.open()
        _default_scanner = (device, scanner)
    return _default_scanner[1]


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
        # Extract scenario from device_id (e.g. 'mock_fm_broadcast' → 'fm_broadcast')
        scenario = 'fm_broadcast'
        if device_id and device_id.startswith('mock_'):
            scenario_key = device_id[len('mock_'):]
            if scenario_key in MockSDRDevice.get_available_scenarios():
                scenario = scenario_key
        return MockSDRDevice(device_id=device_id or 'mock_0', scenario=scenario)
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
