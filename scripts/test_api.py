#!/usr/bin/env python3
"""
API Test Script

This script tests the REST API functionality of the RF Spectrum Monitor.
Requires the API server to be running.

Usage:
    # First start the API server:
    uvicorn backend.api.main:app --reload

    # Then run tests:
    python scripts/test_api.py              # Run all tests
    python scripts/test_api.py --url http://localhost:8000  # Custom URL
"""

import sys
import os
import argparse
import json
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import httpx
except ImportError:
    print("httpx not installed. Run: pip install httpx")
    sys.exit(1)


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


class APITester:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.client = httpx.Client(timeout=30.0)
        self.created_ids = {
            'devices': [],
            'surveys': [],
            'signals': [],
            'exports': []
        }

    def cleanup(self):
        """Clean up created resources"""
        print("\n  Cleaning up...")
        for survey_id in self.created_ids['surveys']:
            try:
                self.client.delete(f"{self.base_url}/api/surveys/{survey_id}")
            except:
                pass
        for device_id in self.created_ids['devices']:
            try:
                self.client.delete(f"{self.base_url}/api/devices/{device_id}?hard=true")
            except:
                pass
        self.client.close()

    def test_health(self) -> bool:
        """Test health endpoint"""
        try:
            response = self.client.get(f"{self.base_url}/health")
            success = response.status_code == 200 and response.json()['status'] == 'healthy'
            print_result("Health check", success, f"Status: {response.status_code}")
            return success
        except Exception as e:
            print_result("Health check", False, str(e))
            return False

    def test_root(self) -> bool:
        """Test root endpoint"""
        try:
            response = self.client.get(f"{self.base_url}/")
            success = response.status_code == 200
            data = response.json()
            print_result("Root endpoint", success, f"App: {data.get('name')}")
            return success
        except Exception as e:
            print_result("Root endpoint", False, str(e))
            return False

    def test_device_detection(self) -> bool:
        """Test device detection"""
        try:
            response = self.client.get(f"{self.base_url}/api/devices/detect")
            success = response.status_code == 200
            data = response.json()
            print_result(
                "Device detection",
                success,
                f"Found {len(data['devices'])} devices, RTL-SDR: {data['rtlsdr_available']}, HackRF: {data['hackrf_available']}"
            )
            return success
        except Exception as e:
            print_result("Device detection", False, str(e))
            return False

    def test_device_crud(self) -> bool:
        """Test device CRUD operations"""
        success = True

        # Create device
        try:
            response = self.client.post(
                f"{self.base_url}/api/devices",
                json={
                    "name": "Test Device",
                    "device_type": "mock",
                    "serial_number": "TEST_API_001",
                    "sample_rate": 2400000,
                    "gain": 30
                }
            )
            if response.status_code == 201:
                device = response.json()
                self.created_ids['devices'].append(device['id'])
                print_result("Create device", True, f"ID: {device['id']}")
            else:
                print_result("Create device", False, response.text)
                success = False
        except Exception as e:
            print_result("Create device", False, str(e))
            return False

        # List devices
        try:
            response = self.client.get(f"{self.base_url}/api/devices")
            data = response.json()
            print_result("List devices", response.status_code == 200, f"Count: {data['total']}")
        except Exception as e:
            print_result("List devices", False, str(e))
            success = False

        # Get device
        try:
            device_id = self.created_ids['devices'][-1]
            response = self.client.get(f"{self.base_url}/api/devices/{device_id}")
            print_result("Get device", response.status_code == 200)
        except Exception as e:
            print_result("Get device", False, str(e))
            success = False

        # Update device
        try:
            device_id = self.created_ids['devices'][-1]
            response = self.client.put(
                f"{self.base_url}/api/devices/{device_id}",
                json={"name": "Updated Device", "gain": 40}
            )
            if response.status_code == 200:
                device = response.json()
                print_result("Update device", device['name'] == "Updated Device")
            else:
                print_result("Update device", False, response.text)
                success = False
        except Exception as e:
            print_result("Update device", False, str(e))
            success = False

        # Test device
        try:
            device_id = self.created_ids['devices'][-1]
            response = self.client.post(f"{self.base_url}/api/devices/{device_id}/test")
            print_result("Test device", response.status_code == 200, response.json().get('message', ''))
        except Exception as e:
            print_result("Test device", False, str(e))
            success = False

        return success

    def test_survey_crud(self) -> bool:
        """Test survey CRUD operations"""
        success = True

        # Ensure we have a device
        if not self.created_ids['devices']:
            self.test_device_crud()

        device_id = self.created_ids['devices'][0] if self.created_ids['devices'] else None

        # Create survey
        try:
            response = self.client.post(
                f"{self.base_url}/api/surveys",
                json={
                    "name": "Test FM Survey",
                    "description": "API test survey",
                    "survey_type": "fixed",
                    "start_frequency": 88000000,
                    "stop_frequency": 108000000,
                    "device_id": device_id,
                    "bandwidth": 200000,
                    "integration_time": 0.1
                }
            )
            if response.status_code == 201:
                survey = response.json()
                self.created_ids['surveys'].append(survey['id'])
                print_result("Create survey", True, f"ID: {survey['id']}, Range: {survey['frequency_range_mhz']}")
            else:
                print_result("Create survey", False, response.text)
                success = False
        except Exception as e:
            print_result("Create survey", False, str(e))
            return False

        # List surveys
        try:
            response = self.client.get(f"{self.base_url}/api/surveys")
            data = response.json()
            print_result("List surveys", response.status_code == 200, f"Count: {data['total']}")
        except Exception as e:
            print_result("List surveys", False, str(e))
            success = False

        # Get survey details
        try:
            survey_id = self.created_ids['surveys'][-1]
            response = self.client.get(f"{self.base_url}/api/surveys/{survey_id}")
            print_result("Get survey details", response.status_code == 200)
        except Exception as e:
            print_result("Get survey details", False, str(e))
            success = False

        # Get survey statistics
        try:
            survey_id = self.created_ids['surveys'][-1]
            response = self.client.get(f"{self.base_url}/api/surveys/{survey_id}/statistics")
            print_result("Get survey statistics", response.status_code == 200)
        except Exception as e:
            print_result("Get survey statistics", False, str(e))
            success = False

        # Add location
        try:
            survey_id = self.created_ids['surveys'][-1]
            response = self.client.post(
                f"{self.base_url}/api/surveys/{survey_id}/locations",
                json={
                    "latitude": 28.6139,
                    "longitude": 77.2090,
                    "name": "Test Location"
                }
            )
            print_result("Add location", response.status_code == 201)
        except Exception as e:
            print_result("Add location", False, str(e))
            success = False

        # Update survey
        try:
            survey_id = self.created_ids['surveys'][-1]
            response = self.client.put(
                f"{self.base_url}/api/surveys/{survey_id}",
                json={"name": "Updated Survey Name"}
            )
            print_result("Update survey", response.status_code == 200)
        except Exception as e:
            print_result("Update survey", False, str(e))
            success = False

        return success

    def test_spectrum_endpoints(self) -> bool:
        """Test spectrum data endpoints"""
        success = True

        # Get measurements (empty)
        try:
            survey_id = self.created_ids['surveys'][-1] if self.created_ids['surveys'] else 1
            response = self.client.get(
                f"{self.base_url}/api/spectrum/measurements",
                params={"survey_id": survey_id, "limit": 10}
            )
            data = response.json()
            print_result("Get measurements", response.status_code == 200, f"Count: {data['total']}")
        except Exception as e:
            print_result("Get measurements", False, str(e))
            success = False

        # Perform scan (with mock device)
        if self.created_ids['devices']:
            try:
                device_id = self.created_ids['devices'][0]
                response = self.client.post(
                    f"{self.base_url}/api/spectrum/scan",
                    json={
                        "device_id": device_id,
                        "start_freq": 88000000,
                        "stop_freq": 92000000,
                        "sample_rate": 2400000,
                        "gain": 20,
                        "integration_time": 0.05,
                        "detect_signals": True
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    print_result(
                        "Perform scan",
                        True,
                        f"Points: {len(data['sweep']['frequencies'])}, Signals: {len(data['signals'])}"
                    )
                else:
                    print_result("Perform scan", False, response.text[:100])
                    success = False
            except Exception as e:
                print_result("Perform scan", False, str(e))
                success = False

        # Get live spectrum
        if self.created_ids['devices']:
            try:
                device_id = self.created_ids['devices'][0]
                response = self.client.post(
                    f"{self.base_url}/api/spectrum/live",
                    json={
                        "device_id": device_id,
                        "center_freq": 100000000,
                        "sample_rate": 2400000,
                        "gain": 20,
                        "fft_size": 512,
                        "averaging": 2
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    print_result("Live spectrum", True, f"Points: {len(data['frequencies'])}")
                else:
                    print_result("Live spectrum", False, response.text[:100])
                    success = False
            except Exception as e:
                print_result("Live spectrum", False, str(e))
                success = False

        # List signals
        try:
            response = self.client.get(f"{self.base_url}/api/spectrum/signals")
            print_result("List signals", response.status_code == 200)
        except Exception as e:
            print_result("List signals", False, str(e))
            success = False

        # Create signal of interest
        try:
            response = self.client.post(
                f"{self.base_url}/api/spectrum/signals",
                json={
                    "center_frequency": 91500000,
                    "bandwidth": 200000,
                    "modulation": "FM",
                    "description": "Test signal"
                }
            )
            if response.status_code == 201:
                signal = response.json()
                self.created_ids['signals'].append(signal['id'])
                print_result("Create signal", True, f"ID: {signal['id']}")
            else:
                print_result("Create signal", False, response.text)
                success = False
        except Exception as e:
            print_result("Create signal", False, str(e))
            success = False

        return success

    def test_export_endpoints(self) -> bool:
        """Test export endpoints"""
        success = True

        if not self.created_ids['surveys']:
            print_result("Export tests", False, "No surveys to export")
            return False

        survey_id = self.created_ids['surveys'][0]

        # Create CSV export
        try:
            response = self.client.post(
                f"{self.base_url}/api/export/csv",
                json={"survey_id": survey_id}
            )
            if response.status_code == 200:
                job = response.json()
                self.created_ids['exports'].append(job['id'])
                print_result("Create CSV export", True, f"Job ID: {job['id']}, Status: {job['status']}")
            else:
                print_result("Create CSV export", False, response.text)
                success = False
        except Exception as e:
            print_result("Create CSV export", False, str(e))
            success = False

        # List export jobs
        try:
            response = self.client.get(f"{self.base_url}/api/export/jobs")
            data = response.json()
            print_result("List export jobs", response.status_code == 200, f"Count: {data['total']}")
        except Exception as e:
            print_result("List export jobs", False, str(e))
            success = False

        return success


def main():
    parser = argparse.ArgumentParser(description='Test RF Spectrum Monitor API')
    parser.add_argument('--url', '-u', default='http://localhost:8000',
                       help='API base URL')
    parser.add_argument('--skip-cleanup', action='store_true',
                       help='Skip cleanup of created resources')

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("  RF Spectrum Monitor - API Test Suite")
    print("=" * 60)
    print(f"\n  API URL: {args.url}")

    tester = APITester(args.url)
    results = []

    # Run tests
    print_header("Basic Endpoints")
    results.append(("Health Check", tester.test_health()))
    results.append(("Root Endpoint", tester.test_root()))

    print_header("Device Endpoints")
    results.append(("Device Detection", tester.test_device_detection()))
    results.append(("Device CRUD", tester.test_device_crud()))

    print_header("Survey Endpoints")
    results.append(("Survey CRUD", tester.test_survey_crud()))

    print_header("Spectrum Endpoints")
    results.append(("Spectrum Data", tester.test_spectrum_endpoints()))

    print_header("Export Endpoints")
    results.append(("Export", tester.test_export_endpoints()))

    # Cleanup
    if not args.skip_cleanup:
        tester.cleanup()

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
