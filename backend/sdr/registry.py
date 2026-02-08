"""
Device Registry

Thread-safe registry that manages multiple open (device, scanner) pairs
keyed by database device ID. Uses reference counting so multiple WebSocket
clients can share a device safely.
"""

import threading
from typing import Dict, List, Optional, Tuple

from loguru import logger

from .base import SDRDevice
from .scanner import SpectrumScanner


class DeviceRegistry:
    """
    Manages multiple open SDR device/scanner pairs.

    Each entry is keyed by the integer database device ID.
    Devices are opened lazily on first acquire() and cached until released.
    Reference counting ensures a device is only closed when all clients
    have released it.
    """

    def __init__(self):
        # db_id → (device, scanner, ref_count)
        self._scanners: Dict[int, Tuple[SDRDevice, SpectrumScanner, int]] = {}
        self._lock = threading.Lock()
        logger.info("Device registry initialized")

    def acquire(self, db_device_id: int) -> SpectrumScanner:
        """
        Open device if not already open and return its scanner.

        Increments the reference count. If the device is already open,
        returns the cached scanner and bumps the count.

        Args:
            db_device_id: Database primary key of the device

        Returns:
            SpectrumScanner ready to use

        Raises:
            ValueError: If device not found in DB
            RuntimeError: If device fails to open
        """
        with self._lock:
            if db_device_id in self._scanners:
                device, scanner, ref_count = self._scanners[db_device_id]
                self._scanners[db_device_id] = (device, scanner, ref_count + 1)
                logger.debug(f"Registry: reused device {db_device_id} (refs={ref_count + 1})")
                return scanner

        # Look up device from DB (import here to avoid circular imports)
        from ..storage.database import get_session, Device

        session = get_session()
        try:
            db_device = session.query(Device).filter(Device.id == db_device_id).first()
            if not db_device:
                raise ValueError(f"Device {db_device_id} not found in database")

            device_type = db_device.device_type.value.lower()
            serial_number = db_device.serial_number
        finally:
            session.close()

        # Create and open the SDR device
        from . import get_device
        sdr_device = get_device(device_type, serial_number)
        try:
            sdr_device.open()
        except Exception:
            # Ensure device is cleaned up on open failure
            try:
                sdr_device.close()
            except Exception:
                pass
            raise

        scanner = SpectrumScanner(sdr_device)

        with self._lock:
            # Double-check: another thread may have opened it while we waited
            if db_device_id in self._scanners:
                sdr_device.close()
                device, scanner, ref_count = self._scanners[db_device_id]
                self._scanners[db_device_id] = (device, scanner, ref_count + 1)
                logger.debug(f"Registry: reused device {db_device_id} after race (refs={ref_count + 1})")
                return scanner
            self._scanners[db_device_id] = (sdr_device, scanner, 1)

        logger.info(f"Registry: acquired device {db_device_id} ({device_type})")
        return scanner

    def release(self, db_device_id: int) -> None:
        """
        Decrement reference count. Close device only when count reaches 0.

        Args:
            db_device_id: Database primary key of the device
        """
        device_to_close = None

        with self._lock:
            entry = self._scanners.get(db_device_id)
            if not entry:
                return
            device, scanner, ref_count = entry
            if ref_count <= 1:
                self._scanners.pop(db_device_id)
                device_to_close = device
            else:
                self._scanners[db_device_id] = (device, scanner, ref_count - 1)
                logger.debug(f"Registry: decremented device {db_device_id} (refs={ref_count - 1})")

        if device_to_close:
            try:
                device_to_close.close()
            except Exception as e:
                logger.warning(f"Error closing device {db_device_id}: {e}")
            logger.info(f"Registry: released device {db_device_id}")

    def get_scanner(self, db_device_id: int) -> Optional[SpectrumScanner]:
        """
        Get scanner for an already-open device (returns None if not open).

        Args:
            db_device_id: Database primary key of the device

        Returns:
            SpectrumScanner if device is open, None otherwise
        """
        with self._lock:
            entry = self._scanners.get(db_device_id)
            return entry[1] if entry else None

    def close_all(self) -> None:
        """Close all open devices regardless of ref count. For shutdown."""
        with self._lock:
            items = list(self._scanners.items())
            self._scanners.clear()

        for db_id, (device, _, ref_count) in items:
            try:
                device.close()
                logger.debug(f"Registry: closed device {db_id} (had {ref_count} refs)")
            except Exception as e:
                logger.warning(f"Error closing device {db_id}: {e}")

        logger.info(f"Registry: closed {len(items)} device(s)")

    def get_status(self) -> List[dict]:
        """
        Return status of all devices currently managed by the registry.

        Returns:
            List of dicts with device_id, device_type, is_open, and ref_count
        """
        with self._lock:
            result = []
            for db_id, (device, _, ref_count) in self._scanners.items():
                result.append({
                    "device_id": db_id,
                    "device_type": device.device_type.value if hasattr(device.device_type, 'value') else str(device.device_type),
                    "is_open": device.is_open,
                    "ref_count": ref_count,
                })
            return result


# Module-level singleton
_registry: Optional[DeviceRegistry] = None
_registry_lock = threading.Lock()


def get_device_registry() -> DeviceRegistry:
    """Get or create the global DeviceRegistry singleton."""
    global _registry
    if _registry is None:
        with _registry_lock:
            if _registry is None:
                _registry = DeviceRegistry()
    return _registry
