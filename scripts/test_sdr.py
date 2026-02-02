#!/usr/bin/env python3
"""
SDR Test Script

This script tests the SDR functionality of the RF Spectrum Monitor.
It can be run with or without actual hardware - uses mock SDR when
no hardware is available.

Usage:
    python scripts/test_sdr.py              # Run all tests with mock SDR
    python scripts/test_sdr.py --device rtlsdr   # Test with RTL-SDR
    python scripts/test_sdr.py --device hackrf   # Test with HackRF
    python scripts/test_sdr.py --sweep           # Run frequency sweep test
    python scripts/test_sdr.py --detect          # Just detect devices
"""

import sys
import os
import argparse
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np


def print_header(title: str):
    """Print a formatted header"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_result(name: str, success: bool, message: str = ""):
    """Print test result"""
    status = "[PASS]" if success else "[FAIL]"
    color = "\033[92m" if success else "\033[91m"
    reset = "\033[0m"
    print(f"  {color}{status}{reset} {name}")
    if message:
        print(f"         {message}")


def test_device_detection():
    """Test device detection functionality"""
    print_header("Device Detection")

    from backend.sdr import (
        detect_all_devices,
        RTLSDR_AVAILABLE,
        HACKRF_AVAILABLE
    )

    print(f"\n  RTL-SDR library available: {RTLSDR_AVAILABLE}")
    print(f"  HackRF library available: {HACKRF_AVAILABLE}")

    devices = detect_all_devices()
    print(f"\n  Detected {len(devices)} device(s):")

    for device in devices:
        print(f"    - Type: {device.get('type', 'unknown')}")
        if 'serial' in device:
            print(f"      Serial: {device['serial']}")
        if 'name' in device:
            print(f"      Name: {device['name']}")

    return len(devices) > 0


def test_mock_device():
    """Test mock SDR device functionality"""
    print_header("Mock SDR Device Test")

    from backend.sdr import MockSDRDevice, ScanParameters

    device = MockSDRDevice(scenario='fm_broadcast')

    # Test open
    success = device.open()
    print_result("Device open", success)

    # Test frequency setting
    success = device.set_center_freq(100e6)
    print_result("Set frequency (100 MHz)", success)

    # Test sample rate
    success = device.set_sample_rate(2.4e6)
    print_result("Set sample rate (2.4 MHz)", success)

    # Test gain
    success = device.set_gain(30)
    print_result("Set gain (30 dB)", success)

    # Test reading samples
    try:
        samples = device.read_samples(1024)
        success = len(samples) == 1024 and samples.dtype == np.complex64
        print_result("Read 1024 samples", success,
                    f"Shape: {samples.shape}, dtype: {samples.dtype}")
    except Exception as e:
        print_result("Read samples", False, str(e))
        success = False

    # Test spectrum computation
    try:
        spectrum = device.get_spectrum(fft_size=512)
        has_data = len(spectrum.frequencies) > 0 and len(spectrum.power_dbm) > 0
        print_result("Get spectrum", has_data,
                    f"Points: {len(spectrum.frequencies)}, "
                    f"Noise floor: {spectrum.noise_floor:.1f} dBm")
    except Exception as e:
        print_result("Get spectrum", False, str(e))
        success = False

    # Test device info
    info = device.get_device_info()
    print_result("Get device info", True,
                f"Type: {info.device_type.value}, "
                f"Freq: {info.min_freq/1e6:.0f}-{info.max_freq/1e6:.0f} MHz")

    # Test close
    device.close()
    print_result("Device close", not device.is_open)

    return success


def test_scanner():
    """Test spectrum scanner functionality"""
    print_header("Spectrum Scanner Test")

    from backend.sdr import create_scanner, ScanParameters, ScannerConfig

    # Create scanner with mock device
    device, scanner = create_scanner('mock', fft_size=512, averaging=2)
    device.open()

    success = True

    # Test single measurement
    try:
        spectrum = scanner.single_measurement(center_freq=100e6)
        has_data = len(spectrum.frequencies) > 0
        print_result("Single measurement", has_data,
                    f"Center: {spectrum.center_freq/1e6:.1f} MHz, "
                    f"Points: {len(spectrum.frequencies)}")
    except Exception as e:
        print_result("Single measurement", False, str(e))
        success = False

    # Test frequency sweep
    try:
        params = ScanParameters(
            start_freq=88e6,
            stop_freq=108e6,
            sample_rate=2.4e6,
            gain=20,
            integration_time=0.05
        )
        result = scanner.single_sweep(params)

        has_data = len(result.frequencies) > 0
        print_result("Frequency sweep (88-108 MHz)", has_data,
                    f"Points: {len(result.frequencies)}, "
                    f"Steps: {result.num_steps}, "
                    f"Time: {result.sweep_time:.2f}s")
    except Exception as e:
        print_result("Frequency sweep", False, str(e))
        success = False

    # Test peak detection
    try:
        if len(result.frequencies) > 0:
            signals = scanner.detect_peaks(
                result.frequencies,
                result.power_dbm,
                threshold_db=8
            )
            print_result("Peak detection", True,
                        f"Found {len(signals)} signals")

            for i, sig in enumerate(signals[:5]):  # Show first 5
                print(f"         Signal {i+1}: {sig.frequency/1e6:.2f} MHz, "
                      f"{sig.power_dbm:.1f} dBm, "
                      f"BW: {sig.bandwidth/1e3:.1f} kHz")
    except Exception as e:
        print_result("Peak detection", False, str(e))
        success = False

    # Test statistics
    try:
        stats = scanner.get_signal_statistics(result.frequencies, result.power_dbm)
        print_result("Statistics", True,
                    f"Min: {stats['min_power_dbm']:.1f}, "
                    f"Max: {stats['max_power_dbm']:.1f}, "
                    f"Mean: {stats['mean_power_dbm']:.1f} dBm")
    except Exception as e:
        print_result("Statistics", False, str(e))
        success = False

    device.close()
    return success


def test_continuous_scan():
    """Test continuous scanning functionality"""
    print_header("Continuous Scan Test")

    from backend.sdr import create_scanner, ScanParameters
    import threading

    device, scanner = create_scanner('mock')
    device.open()

    scan_count = 0
    scan_complete = threading.Event()

    def on_sweep(result):
        nonlocal scan_count
        scan_count += 1
        print(f"         Sweep {scan_count}: {len(result.frequencies)} points, "
              f"{result.sweep_time:.2f}s")
        if scan_count >= 3:
            scan_complete.set()

    params = ScanParameters(
        start_freq=88e6,
        stop_freq=92e6,
        sample_rate=2.4e6,
        gain=20,
        integration_time=0.02
    )

    try:
        scanner.continuous_scan(params, on_sweep, interval=0.5)
        print_result("Start continuous scan", scanner.is_scanning)

        # Wait for 3 sweeps or timeout
        completed = scan_complete.wait(timeout=10)

        scanner.stop_scan()
        print_result("Stop continuous scan", not scanner.is_scanning,
                    f"Completed {scan_count} sweeps")

        success = scan_count >= 3
    except Exception as e:
        print_result("Continuous scan", False, str(e))
        success = False
        scanner.stop_scan()

    device.close()
    return success


def test_real_device(device_type: str):
    """Test with real SDR hardware"""
    print_header(f"Real Device Test: {device_type.upper()}")

    from backend.sdr import get_device, SpectrumScanner, ScanParameters

    try:
        device = get_device(device_type)
        print_result(f"Create {device_type} device", True)
    except Exception as e:
        print_result(f"Create {device_type} device", False, str(e))
        return False

    try:
        device.open()
        print_result("Device open", device.is_open)
    except Exception as e:
        print_result("Device open", False, str(e))
        return False

    scanner = SpectrumScanner(device)

    # Test basic operations
    try:
        info = device.get_device_info()
        print(f"\n  Device Info:")
        print(f"    Type: {info.device_type.value}")
        print(f"    Serial: {info.serial_number}")
        print(f"    Frequency range: {info.min_freq/1e6:.1f} - {info.max_freq/1e6:.1f} MHz")
        print(f"    Sample rate: {info.min_sample_rate/1e6:.2f} - {info.max_sample_rate/1e6:.2f} MHz")
    except Exception as e:
        print(f"  Warning: Could not get device info: {e}")

    # Run a quick scan of FM band
    try:
        print("\n  Running FM band scan (88-108 MHz)...")
        params = ScanParameters(
            start_freq=88e6,
            stop_freq=108e6,
            sample_rate=2.4e6,
            gain=30,
            integration_time=0.1
        )

        result = scanner.single_sweep(params)
        print_result("FM band sweep", len(result.frequencies) > 0,
                    f"{len(result.frequencies)} points in {result.sweep_time:.2f}s")

        # Detect FM stations
        signals = scanner.detect_peaks(
            result.frequencies, result.power_dbm,
            threshold_db=10, min_distance_hz=500e3
        )
        print(f"\n  Detected {len(signals)} FM stations:")
        for sig in signals[:10]:
            print(f"    {sig.frequency/1e6:.1f} MHz: {sig.power_dbm:.1f} dBm")

        success = True
    except Exception as e:
        print_result("FM band sweep", False, str(e))
        success = False

    device.close()
    print_result("Device close", not device.is_open)

    return success


def test_scenarios():
    """Test different mock scenarios"""
    print_header("Mock Scenario Test")

    from backend.sdr import MockSDRDevice, SpectrumScanner, ScanParameters

    scenarios = ['fm_broadcast', 'ism_433', 'wifi_2.4ghz', 'empty']

    for scenario in scenarios:
        device = MockSDRDevice(scenario=scenario)
        device.open()
        scanner = SpectrumScanner(device)

        # Get appropriate frequency range for scenario
        if scenario == 'fm_broadcast':
            params = ScanParameters(start_freq=88e6, stop_freq=108e6, sample_rate=2.4e6, gain=20)
        elif scenario == 'ism_433':
            params = ScanParameters(start_freq=430e6, stop_freq=436e6, sample_rate=2.4e6, gain=20)
        elif scenario == 'wifi_2.4ghz':
            params = ScanParameters(start_freq=2400e6, stop_freq=2500e6, sample_rate=8e6, gain=20)
        else:
            params = ScanParameters(start_freq=100e6, stop_freq=110e6, sample_rate=2.4e6, gain=20)

        try:
            result = scanner.single_sweep(params)
            signals = scanner.detect_peaks(result.frequencies, result.power_dbm)
            print_result(f"Scenario: {scenario}", True, f"Found {len(signals)} signals")
        except Exception as e:
            print_result(f"Scenario: {scenario}", False, str(e))

        device.close()


def main():
    parser = argparse.ArgumentParser(description='Test SDR functionality')
    parser.add_argument('--device', '-d', choices=['mock', 'rtlsdr', 'hackrf'],
                       default='mock', help='Device type to test')
    parser.add_argument('--detect', action='store_true',
                       help='Only run device detection')
    parser.add_argument('--sweep', action='store_true',
                       help='Only run sweep test')
    parser.add_argument('--scenarios', action='store_true',
                       help='Test different mock scenarios')
    parser.add_argument('--all', action='store_true',
                       help='Run all tests')

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("  RF Spectrum Monitor - SDR Test Suite")
    print("=" * 60)

    results = []

    # Always run device detection
    results.append(("Device Detection", test_device_detection()))

    if args.detect:
        # Only detection requested
        pass
    elif args.scenarios:
        test_scenarios()
    elif args.device != 'mock':
        # Test real hardware
        results.append((f"{args.device.upper()} Device", test_real_device(args.device)))
    else:
        # Run standard mock tests
        results.append(("Mock Device", test_mock_device()))

        if args.sweep or args.all:
            results.append(("Scanner", test_scanner()))

        if args.all:
            results.append(("Continuous Scan", test_continuous_scan()))
            test_scenarios()

    # Summary
    print_header("Test Summary")
    passed = sum(1 for _, r in results if r)
    total = len(results)
    print(f"\n  Passed: {passed}/{total}")

    for name, result in results:
        status = "\033[92mPASS\033[0m" if result else "\033[91mFAIL\033[0m"
        print(f"    {name}: {status}")

    print("\n")
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
