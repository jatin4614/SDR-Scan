#!/usr/bin/env python3
"""
Database Test Script

This script tests the database functionality of the RF Spectrum Monitor.
It verifies model creation, CRUD operations, and query performance.

Usage:
    python scripts/test_database.py              # Run all tests
    python scripts/test_database.py --init       # Initialize database only
    python scripts/test_database.py --reset      # Reset and reinitialize database
"""

import sys
import os
import argparse
import time
from datetime import datetime, timedelta
import random

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


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


def test_database_init():
    """Test database initialization"""
    print_header("Database Initialization")

    from backend.storage import init_db, get_engine
    from backend.core.config import settings

    print(f"\n  Database URL: {settings.database.url}")

    try:
        init_db()
        engine = get_engine()
        print_result("Initialize database", True)

        # Verify tables exist
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"         Tables created: {', '.join(tables)}")

        expected_tables = ['devices', 'surveys', 'locations', 'measurements',
                          'signals_of_interest', 'export_jobs']
        all_present = all(t in tables for t in expected_tables)
        print_result("All tables present", all_present)

        return all_present
    except Exception as e:
        print_result("Initialize database", False, str(e))
        return False


def test_device_crud():
    """Test Device CRUD operations"""
    print_header("Device CRUD Operations")

    from backend.storage import (
        DatabaseSession, DeviceRepository, DeviceTypeEnum
    )

    success = True

    with DatabaseSession() as session:
        repo = DeviceRepository(session)

        # Create
        try:
            device = repo.create(
                name="Test RTL-SDR",
                device_type=DeviceTypeEnum.RTLSDR,
                serial_number="TEST001",
                sample_rate=2400000,
                gain=30
            )
            session.commit()
            print_result("Create device", device.id is not None,
                        f"ID: {device.id}, Name: {device.name}")
            device_id = device.id
        except Exception as e:
            print_result("Create device", False, str(e))
            return False

        # Read
        try:
            device = repo.get_by_id(device_id)
            print_result("Read device by ID", device is not None)

            device = repo.get_by_serial("TEST001")
            print_result("Read device by serial", device is not None)
        except Exception as e:
            print_result("Read device", False, str(e))
            success = False

        # Update
        try:
            device = repo.update(device_id, gain=40, name="Updated RTL-SDR")
            session.commit()
            print_result("Update device", device.gain == 40)
        except Exception as e:
            print_result("Update device", False, str(e))
            success = False

        # List
        try:
            devices = repo.get_all()
            print_result("List devices", len(devices) > 0, f"Count: {len(devices)}")
        except Exception as e:
            print_result("List devices", False, str(e))
            success = False

        # Delete
        try:
            deleted = repo.delete(device_id)
            session.commit()
            print_result("Delete device (soft)", deleted)

            # Hard delete
            repo.hard_delete(device_id)
            session.commit()
            device = repo.get_by_id(device_id)
            print_result("Delete device (hard)", device is None)
        except Exception as e:
            print_result("Delete device", False, str(e))
            success = False

    return success


def test_survey_crud():
    """Test Survey CRUD operations"""
    print_header("Survey CRUD Operations")

    from backend.storage import (
        DatabaseSession, DeviceRepository, SurveyRepository,
        DeviceTypeEnum, SurveyTypeEnum, SurveyStatusEnum
    )

    success = True

    with DatabaseSession() as session:
        device_repo = DeviceRepository(session)
        survey_repo = SurveyRepository(session)

        # Create a device first
        device = device_repo.create(
            name="Survey Test Device",
            device_type=DeviceTypeEnum.MOCK
        )
        session.commit()

        # Create survey
        try:
            survey = survey_repo.create(
                name="FM Band Survey",
                survey_type=SurveyTypeEnum.FIXED,
                start_frequency=88e6,
                stop_frequency=108e6,
                device_id=device.id,
                description="Test survey of FM broadcast band",
                bandwidth=200000,
                integration_time=0.1
            )
            session.commit()
            print_result("Create survey", survey.id is not None,
                        f"ID: {survey.id}, Range: {survey.frequency_range_mhz}")
            survey_id = survey.id
        except Exception as e:
            print_result("Create survey", False, str(e))
            return False

        # Read
        try:
            survey = survey_repo.get_by_id(survey_id)
            print_result("Read survey", survey is not None)
        except Exception as e:
            print_result("Read survey", False, str(e))
            success = False

        # Update status
        try:
            survey = survey_repo.update_status(survey_id, SurveyStatusEnum.RUNNING)
            session.commit()
            print_result("Update survey status", survey.status == SurveyStatusEnum.RUNNING)

            survey = survey_repo.update_progress(survey_id, 50.0)
            session.commit()
            print_result("Update survey progress", survey.progress == 50.0)
        except Exception as e:
            print_result("Update survey status", False, str(e))
            success = False

        # List
        try:
            surveys = survey_repo.get_all()
            print_result("List surveys", len(surveys) > 0, f"Count: {len(surveys)}")

            active = survey_repo.get_active()
            print_result("Get active surveys", len(active) > 0)
        except Exception as e:
            print_result("List surveys", False, str(e))
            success = False

        # Statistics
        try:
            stats = survey_repo.get_statistics(survey_id)
            print_result("Get survey statistics", 'survey_id' in stats)
        except Exception as e:
            print_result("Get survey statistics", False, str(e))
            success = False

        # Clean up
        try:
            survey_repo.delete(survey_id)
            device_repo.hard_delete(device.id)
            session.commit()
            print_result("Delete survey", True)
        except Exception as e:
            print_result("Delete survey", False, str(e))
            success = False

    return success


def test_measurements():
    """Test Measurement operations with bulk inserts"""
    print_header("Measurement Operations")

    from backend.storage import (
        DatabaseSession, DeviceRepository, SurveyRepository, MeasurementRepository,
        DeviceTypeEnum, SurveyTypeEnum
    )
    import numpy as np

    success = True

    with DatabaseSession() as session:
        device_repo = DeviceRepository(session)
        survey_repo = SurveyRepository(session)
        measurement_repo = MeasurementRepository(session)

        # Create device and survey
        device = device_repo.create(
            name="Measurement Test Device",
            device_type=DeviceTypeEnum.MOCK
        )
        survey = survey_repo.create(
            name="Measurement Test Survey",
            survey_type=SurveyTypeEnum.FIXED,
            start_frequency=88e6,
            stop_frequency=108e6,
            device_id=device.id
        )
        session.commit()

        # Bulk create measurements
        try:
            num_measurements = 1000
            measurements = []
            base_time = datetime.utcnow()

            for i in range(num_measurements):
                measurements.append({
                    'survey_id': survey.id,
                    'device_id': device.id,
                    'frequency': 88e6 + (i * 20000),
                    'bandwidth': 20000,
                    'power_dbm': -80 + random.random() * 40,
                    'latitude': 28.6139 + random.random() * 0.01,
                    'longitude': 77.2090 + random.random() * 0.01,
                    'timestamp': base_time + timedelta(seconds=i * 0.1)
                })

            start_time = time.time()
            count = measurement_repo.bulk_create(measurements)
            session.commit()
            elapsed = time.time() - start_time

            print_result(
                "Bulk create measurements",
                count == num_measurements,
                f"{count} records in {elapsed:.3f}s ({count/elapsed:.0f}/sec)"
            )
        except Exception as e:
            print_result("Bulk create measurements", False, str(e))
            success = False

        # Query measurements
        try:
            # By survey
            results = measurement_repo.get_by_survey(survey.id, limit=100)
            print_result("Query by survey", len(results) == 100)

            # By frequency range
            results = measurement_repo.get_by_survey(
                survey.id,
                freq_range=(90e6, 100e6)
            )
            print_result("Query by frequency range", len(results) > 0,
                        f"Found {len(results)} in 90-100 MHz")

            # Geo-referenced
            results = measurement_repo.get_geo_referenced(survey.id, limit=500)
            print_result("Query geo-referenced", len(results) > 0)

            # Statistics
            stats = measurement_repo.get_frequency_statistics(survey.id)
            print_result("Get frequency statistics", stats['count'] > 0,
                        f"Min: {stats['min_power_dbm']:.1f}, Max: {stats['max_power_dbm']:.1f} dBm")

            # Count
            count = measurement_repo.count_by_survey(survey.id)
            print_result("Count measurements", count == num_measurements)
        except Exception as e:
            print_result("Query measurements", False, str(e))
            success = False

        # Clean up
        try:
            deleted = measurement_repo.delete_by_survey(survey.id)
            survey_repo.delete(survey.id)
            device_repo.hard_delete(device.id)
            session.commit()
            print_result("Clean up", True, f"Deleted {deleted} measurements")
        except Exception as e:
            print_result("Clean up", False, str(e))
            success = False

    return success


def test_signals_of_interest():
    """Test SignalOfInterest operations"""
    print_header("Signal of Interest Operations")

    from backend.storage import (
        DatabaseSession, SurveyRepository, SignalOfInterestRepository,
        SurveyTypeEnum
    )

    success = True

    with DatabaseSession() as session:
        survey_repo = SurveyRepository(session)
        signal_repo = SignalOfInterestRepository(session)

        # Create survey
        survey = survey_repo.create(
            name="Signal Detection Test",
            survey_type=SurveyTypeEnum.FIXED,
            start_frequency=88e6,
            stop_frequency=108e6
        )
        session.commit()

        # Create signal
        try:
            signal = signal_repo.create(
                center_frequency=91.5e6,
                survey_id=survey.id,
                bandwidth=200000,
                modulation='FM',
                description='Local FM station',
                average_power_dbm=-45
            )
            session.commit()
            print_result("Create signal", signal.id is not None,
                        f"Freq: {signal.center_frequency/1e6:.1f} MHz")
            signal_id = signal.id
        except Exception as e:
            print_result("Create signal", False, str(e))
            return False

        # Update detection
        try:
            for _ in range(5):
                power = -45 + random.random() * 10
                signal_repo.update_detection(signal_id, power)
            session.commit()

            signal = signal_repo.get_by_id(signal_id)
            print_result("Update detection", signal.detection_count == 6,
                        f"Count: {signal.detection_count}, Avg: {signal.average_power_dbm:.1f} dBm")
        except Exception as e:
            print_result("Update detection", False, str(e))
            success = False

        # Find by frequency
        try:
            found = signal_repo.find_by_frequency(91.6e6)
            print_result("Find by frequency", found is not None)
        except Exception as e:
            print_result("Find by frequency", False, str(e))
            success = False

        # Clean up
        try:
            signal_repo.delete(signal_id)
            survey_repo.delete(survey.id)
            session.commit()
            print_result("Clean up", True)
        except Exception as e:
            print_result("Clean up", False, str(e))
            success = False

    return success


def test_export_jobs():
    """Test ExportJob operations"""
    print_header("Export Job Operations")

    from backend.storage import (
        DatabaseSession, SurveyRepository, ExportJobRepository,
        SurveyTypeEnum, ExportTypeEnum, ExportStatusEnum
    )

    success = True

    with DatabaseSession() as session:
        survey_repo = SurveyRepository(session)
        export_repo = ExportJobRepository(session)

        # Create survey
        survey = survey_repo.create(
            name="Export Test Survey",
            survey_type=SurveyTypeEnum.FIXED,
            start_frequency=88e6,
            stop_frequency=108e6
        )
        session.commit()

        # Create export job
        try:
            job = export_repo.create(
                export_type=ExportTypeEnum.GEOPACKAGE,
                survey_id=survey.id,
                parameters='{"include_heatmap": true}'
            )
            session.commit()
            print_result("Create export job", job.id is not None,
                        f"Type: {job.export_type.value}")
            job_id = job.id
        except Exception as e:
            print_result("Create export job", False, str(e))
            return False

        # Update status
        try:
            export_repo.update_status(
                job_id,
                ExportStatusEnum.PROCESSING
            )
            export_repo.update_progress(job_id, 50.0)
            session.commit()

            export_repo.update_status(
                job_id,
                ExportStatusEnum.COMPLETED,
                file_path='/exports/survey_1.gpkg',
                file_size=1024000
            )
            session.commit()

            job = export_repo.get_by_id(job_id)
            print_result("Update export status", job.status == ExportStatusEnum.COMPLETED)
        except Exception as e:
            print_result("Update export status", False, str(e))
            success = False

        # List
        try:
            jobs = export_repo.get_by_survey(survey.id)
            print_result("List export jobs", len(jobs) > 0)
        except Exception as e:
            print_result("List export jobs", False, str(e))
            success = False

        # Clean up
        try:
            export_repo.delete(job_id)
            survey_repo.delete(survey.id)
            session.commit()
            print_result("Clean up", True)
        except Exception as e:
            print_result("Clean up", False, str(e))
            success = False

    return success


def main():
    parser = argparse.ArgumentParser(description='Test database functionality')
    parser.add_argument('--init', action='store_true',
                       help='Initialize database only')
    parser.add_argument('--reset', action='store_true',
                       help='Reset and reinitialize database')

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("  RF Spectrum Monitor - Database Test Suite")
    print("=" * 60)

    # Reset database if requested
    if args.reset:
        print_header("Resetting Database")
        from backend.storage import reset_db
        reset_db()
        print("  Database reset complete.")

    results = []

    # Initialize database
    results.append(("Database Init", test_database_init()))

    if args.init:
        # Only initialization requested
        pass
    else:
        # Run CRUD tests
        results.append(("Device CRUD", test_device_crud()))
        results.append(("Survey CRUD", test_survey_crud()))
        results.append(("Measurements", test_measurements()))
        results.append(("Signals of Interest", test_signals_of_interest()))
        results.append(("Export Jobs", test_export_jobs()))

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
