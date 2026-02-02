#!/usr/bin/env python3
"""
Survey Orchestration Test Script

Tests the complete survey workflow including:
- Survey configuration
- GPS handling
- Background task execution
- Measurement storage
- Progress tracking
"""

import sys
import time
import requests
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


API_BASE = "http://localhost:8000"


def print_section(title: str):
    """Print a section header"""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")


def test_api_health():
    """Test API is running"""
    print_section("Testing API Health")
    try:
        response = requests.get(f"{API_BASE}/health", timeout=5)
        if response.status_code == 200:
            print(f"[OK] API is healthy: {response.json()}")
            return True
        else:
            print(f"[FAIL] API returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"[FAIL] Cannot connect to API at {API_BASE}")
        print("       Make sure the server is running: python -m uvicorn backend.api.main:app")
        return False


def test_device_registration():
    """Register a mock device for testing"""
    print_section("Testing Device Registration")

    # First check if device exists
    response = requests.get(f"{API_BASE}/api/devices")
    devices = response.json().get('devices', [])

    mock_device = None
    for device in devices:
        if device.get('device_type') == 'mock':
            mock_device = device
            print(f"[OK] Mock device already exists: ID {device['id']}")
            break

    if not mock_device:
        # Register new mock device
        device_data = {
            "name": "Test Mock SDR",
            "device_type": "mock",
            "serial_number": "MOCK-TEST-001",
            "sample_rate": 2400000,
            "gain": 30,
            "is_active": True
        }
        response = requests.post(f"{API_BASE}/api/devices", json=device_data)
        if response.status_code == 201:
            mock_device = response.json()
            print(f"[OK] Created mock device: ID {mock_device['id']}")
        else:
            print(f"[FAIL] Failed to create device: {response.text}")
            return None

    return mock_device['id']


def test_survey_creation(device_id: int):
    """Create a test survey"""
    print_section("Testing Survey Creation")

    survey_data = {
        "name": "Test FM Band Survey",
        "description": "Automated test of FM broadcast band",
        "survey_type": "fixed",
        "device_id": device_id,
        "start_frequency": 88000000,  # 88 MHz
        "stop_frequency": 108000000,  # 108 MHz
        "step_size": 200000,  # 200 kHz steps
        "bandwidth": 200000,  # 200 kHz RBW
        "integration_time": 0.1
    }

    response = requests.post(f"{API_BASE}/api/surveys", json=survey_data)
    if response.status_code == 201:
        survey = response.json()
        print(f"[OK] Created survey: ID {survey['id']} - {survey['name']}")
        print(f"     Frequency range: {survey['frequency_range_mhz']}")
        print(f"     Status: {survey['status']}")
        return survey['id']
    else:
        print(f"[FAIL] Failed to create survey: {response.text}")
        return None


def test_survey_start(survey_id: int, device_id: int):
    """Start the survey with location"""
    print_section("Testing Survey Start")

    start_data = {
        "device_id": device_id,
        "location": {
            "latitude": 40.7128,
            "longitude": -74.0060,
            "altitude": 10.0,
            "name": "Test Location - NYC"
        },
        "gps_mode": "manual"
    }

    response = requests.post(f"{API_BASE}/api/surveys/{survey_id}/start", json=start_data)
    if response.status_code == 200:
        survey = response.json()
        print(f"[OK] Started survey: ID {survey['id']}")
        print(f"     Status: {survey['status']}")
        return True
    else:
        print(f"[FAIL] Failed to start survey: {response.text}")
        return False


def test_survey_progress(survey_id: int):
    """Monitor survey progress"""
    print_section("Testing Survey Progress")

    max_checks = 20
    check_interval = 2

    for i in range(max_checks):
        response = requests.get(f"{API_BASE}/api/surveys/{survey_id}/progress")
        if response.status_code == 200:
            progress = response.json()
            print(f"  [{i+1}/{max_checks}] Status: {progress['status']}, "
                  f"Progress: {progress['progress']:.1f}%, "
                  f"Measurements: {progress['measurements_collected']}")

            if progress.get('current_frequency'):
                freq_mhz = progress['current_frequency'] / 1e6
                print(f"            Current frequency: {freq_mhz:.2f} MHz")

            if progress['status'] in ['completed', 'failed', 'paused']:
                print(f"\n[OK] Survey finished with status: {progress['status']}")
                return progress['status']

        time.sleep(check_interval)

    print(f"\n[WARN] Survey still running after {max_checks * check_interval}s")
    return "running"


def test_survey_stop(survey_id: int):
    """Stop the survey"""
    print_section("Testing Survey Stop")

    response = requests.post(f"{API_BASE}/api/surveys/{survey_id}/stop")
    if response.status_code == 200:
        survey = response.json()
        print(f"[OK] Stopped survey: Status = {survey['status']}")
        return True
    elif response.status_code == 409:
        print(f"[INFO] Survey not running (already completed or stopped)")
        return True
    else:
        print(f"[FAIL] Failed to stop survey: {response.text}")
        return False


def test_survey_statistics(survey_id: int):
    """Get survey statistics"""
    print_section("Testing Survey Statistics")

    response = requests.get(f"{API_BASE}/api/surveys/{survey_id}/statistics")
    if response.status_code == 200:
        stats = response.json()
        print(f"[OK] Survey statistics:")
        print(f"     Name: {stats.get('name')}")
        print(f"     Status: {stats.get('status')}")
        print(f"     Measurements: {stats.get('measurement_count')}")
        print(f"     Locations: {stats.get('location_count')}")
        print(f"     Signals: {stats.get('signal_count')}")
        if stats.get('min_power_dbm') is not None:
            print(f"     Power range: {stats.get('min_power_dbm'):.1f} to {stats.get('max_power_dbm'):.1f} dBm")
        return True
    else:
        print(f"[FAIL] Failed to get statistics: {response.text}")
        return False


def test_measurements_query(survey_id: int):
    """Query measurements from the survey"""
    print_section("Testing Measurements Query")

    response = requests.get(
        f"{API_BASE}/api/spectrum/measurements",
        params={"survey_id": survey_id, "limit": 10}
    )
    if response.status_code == 200:
        data = response.json()
        measurements = data.get('measurements', [])
        print(f"[OK] Retrieved {len(measurements)} measurements (of {data.get('total', 0)} total)")
        if measurements:
            print(f"\n     Sample measurements:")
            for m in measurements[:5]:
                freq_mhz = m['frequency'] / 1e6
                print(f"       {freq_mhz:.2f} MHz: {m['power_dbm']:.1f} dBm")
        return True
    else:
        print(f"[FAIL] Failed to query measurements: {response.text}")
        return False


def test_survey_cleanup(survey_id: int):
    """Clean up test survey"""
    print_section("Cleanup")

    response = requests.delete(f"{API_BASE}/api/surveys/{survey_id}")
    if response.status_code == 204:
        print(f"[OK] Deleted test survey {survey_id}")
        return True
    elif response.status_code == 409:
        print(f"[WARN] Cannot delete running survey, stopping first...")
        test_survey_stop(survey_id)
        response = requests.delete(f"{API_BASE}/api/surveys/{survey_id}")
        if response.status_code == 204:
            print(f"[OK] Deleted test survey {survey_id}")
            return True
    print(f"[FAIL] Failed to delete survey: {response.text}")
    return False


def run_core_module_tests():
    """Test core modules directly without API"""
    print_section("Testing Core Modules (Direct)")

    try:
        # Test GPS Handler
        print("\n  Testing GPS Handler...")
        from backend.core import GPSHandler, GPSMode, GPSLocation

        gps = GPSHandler(mode=GPSMode.MOCK)
        gps.start()
        location = gps.get_location()
        if location:
            print(f"    [OK] Mock GPS location: {location.latitude:.6f}, {location.longitude:.6f}")
        gps.stop()

        # Test Signal Processor
        print("\n  Testing Signal Processor...")
        from backend.core import SignalProcessor
        import numpy as np

        processor = SignalProcessor()
        frequencies = np.linspace(88e6, 108e6, 1000)
        # Simulate FM stations at 91.1, 95.5, 101.9 MHz
        power = np.random.normal(-90, 3, 1000)
        for station_freq in [91.1e6, 95.5e6, 101.9e6]:
            idx = np.argmin(np.abs(frequencies - station_freq))
            power[max(0, idx-5):min(len(power), idx+5)] += 30

        peaks = processor.detect_peaks(frequencies, power)
        print(f"    [OK] Detected {len(peaks)} peaks")
        for peak in peaks[:3]:
            print(f"        {peak.frequency/1e6:.1f} MHz: {peak.power_dbm:.1f} dBm, BW: {peak.bandwidth/1e3:.1f} kHz")

        # Test Task Manager
        print("\n  Testing Task Manager...")
        from backend.core import get_task_manager, TaskType

        manager = get_task_manager()

        def sample_task(x, y):
            time.sleep(0.5)
            return x + y

        task_id = manager.submit(TaskType.ANALYSIS, sample_task, 10, 20)
        print(f"    [OK] Submitted task: {task_id}")

        # Wait for completion
        for _ in range(10):
            status = manager.get_status(task_id)
            if status and status.status.value == 'completed':
                print(f"    [OK] Task completed with result: {status.result}")
                break
            time.sleep(0.2)

        print("\n  [OK] All core module tests passed")
        return True

    except Exception as e:
        print(f"\n  [FAIL] Core module test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print(" RF Spectrum Monitor - Survey Orchestration Test")
    print("="*60)

    # Run core module tests first (no API needed)
    if not run_core_module_tests():
        print("\n[FAIL] Core module tests failed. Fix before testing API.")
        return 1

    # Check if API is available
    if not test_api_health():
        print("\n[INFO] Skipping API tests (server not running)")
        print("       To run full tests, start the server first:")
        print("       uvicorn backend.api.main:app --reload")
        return 0

    # Run API tests
    device_id = test_device_registration()
    if not device_id:
        return 1

    survey_id = test_survey_creation(device_id)
    if not survey_id:
        return 1

    # Start and monitor survey
    if test_survey_start(survey_id, device_id):
        # Give it time to run
        final_status = test_survey_progress(survey_id)

        # If still running, stop it
        if final_status == "running":
            test_survey_stop(survey_id)

    # Get results
    test_survey_statistics(survey_id)
    test_measurements_query(survey_id)

    # Ask about cleanup
    print("\n")
    cleanup = input("Delete test survey? [y/N]: ").strip().lower()
    if cleanup == 'y':
        test_survey_cleanup(survey_id)
    else:
        print(f"[INFO] Test survey {survey_id} preserved for inspection")

    print("\n" + "="*60)
    print(" Test Complete")
    print("="*60 + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
