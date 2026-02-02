"""
RTL-SDR Device Implementation

This module provides support for RTL-SDR devices using the pyrtlsdr library.
RTL-SDR is a low-cost SDR based on DVB-T TV tuners with RTL2832U chipset.

Supported frequency range: ~24 MHz to ~1.766 GHz (varies by tuner)
"""

from typing import Optional, List
import numpy as np
from loguru import logger

from .base import (
    SDRDevice, DeviceType, DeviceInfo,
    DeviceNotFoundError, DeviceConnectionError,
    FrequencyOutOfRangeError, SampleRateError
)

# Try to import rtlsdr library
try:
    from rtlsdr import RtlSdr
    RTLSDR_AVAILABLE = True
except ImportError:
    RtlSdr = None
    RTLSDR_AVAILABLE = False
    logger.warning("pyrtlsdr library not installed. RTL-SDR support disabled.")


class RTLSDRDevice(SDRDevice):
    """
    RTL-SDR device implementation.

    Uses the pyrtlsdr library to interface with RTL2832U-based SDR dongles.
    These are commonly available as inexpensive USB TV tuners.

    Typical specifications:
    - Frequency range: 24 MHz - 1766 MHz (R820T/R820T2 tuner)
    - Sample rates: 225 kHz - 3.2 MHz
    - Resolution: 8-bit ADC
    """

    # Common sample rates for RTL-SDR
    SUPPORTED_SAMPLE_RATES = [225e3, 300e3, 900e3, 1.024e6, 1.2e6, 1.8e6, 2.4e6, 2.56e6, 3.2e6]

    # Frequency range (R820T tuner - most common)
    MIN_FREQ = 24e6      # 24 MHz
    MAX_FREQ = 1766e6    # 1.766 GHz

    def __init__(self, device_index: int = 0):
        """
        Initialize RTL-SDR device.

        Args:
            device_index: Index of the RTL-SDR device (0 for first device)
        """
        super().__init__(device_id=str(device_index))
        self.device_index = device_index
        self._device: Optional['RtlSdr'] = None
        self._serial: Optional[str] = None

        if not RTLSDR_AVAILABLE:
            logger.error("RTL-SDR library not available")

    @property
    def device_type(self) -> DeviceType:
        return DeviceType.RTLSDR

    def open(self) -> bool:
        """Open connection to RTL-SDR device."""
        if not RTLSDR_AVAILABLE:
            raise DeviceNotFoundError("pyrtlsdr library not installed")

        if self.is_open:
            logger.warning("Device already open")
            return True

        try:
            self._device = RtlSdr(self.device_index)
            self.is_open = True

            # Get serial number
            try:
                self._serial = self._device.get_device_serial_addresses()[self.device_index]
            except Exception:
                self._serial = f"rtlsdr_{self.device_index}"

            # Set default parameters
            self._device.sample_rate = self._sample_rate
            self._device.center_freq = self._center_freq
            self._device.gain = self._gain

            logger.info(f"RTL-SDR opened: index={self.device_index}, serial={self._serial}")
            return True

        except Exception as e:
            logger.error(f"Failed to open RTL-SDR: {e}")
            raise DeviceConnectionError(f"Failed to open RTL-SDR device {self.device_index}: {e}")

    def close(self) -> None:
        """Close connection to RTL-SDR device."""
        if self._device is not None:
            try:
                self._device.close()
                logger.info(f"RTL-SDR closed: index={self.device_index}")
            except Exception as e:
                logger.warning(f"Error closing RTL-SDR: {e}")
            finally:
                self._device = None
                self.is_open = False

    def set_center_freq(self, freq: float) -> bool:
        """Set center frequency."""
        if not self.is_open or self._device is None:
            raise DeviceConnectionError("Device not open")

        if freq < self.MIN_FREQ or freq > self.MAX_FREQ:
            raise FrequencyOutOfRangeError(
                f"Frequency {freq/1e6:.2f} MHz out of range "
                f"({self.MIN_FREQ/1e6:.0f} - {self.MAX_FREQ/1e6:.0f} MHz)"
            )

        try:
            self._device.center_freq = freq
            self._center_freq = freq
            logger.debug(f"RTL-SDR frequency set to {freq/1e6:.3f} MHz")
            return True
        except Exception as e:
            logger.error(f"Failed to set frequency: {e}")
            return False

    def set_sample_rate(self, rate: float) -> bool:
        """Set sample rate."""
        if not self.is_open or self._device is None:
            raise DeviceConnectionError("Device not open")

        # RTL-SDR supports 225 kHz to 3.2 MHz
        if rate < 225e3 or rate > 3.2e6:
            raise SampleRateError(
                f"Sample rate {rate/1e6:.2f} MHz out of range (0.225 - 3.2 MHz)"
            )

        try:
            self._device.sample_rate = rate
            self._sample_rate = rate
            logger.debug(f"RTL-SDR sample rate set to {rate/1e6:.3f} MHz")
            return True
        except Exception as e:
            logger.error(f"Failed to set sample rate: {e}")
            return False

    def set_gain(self, gain: int) -> bool:
        """
        Set gain.

        Args:
            gain: Gain in dB. Use 'auto' mode if gain is 0.
        """
        if not self.is_open or self._device is None:
            raise DeviceConnectionError("Device not open")

        try:
            if gain == 0:
                # Enable automatic gain
                self._device.gain = 'auto'
            else:
                # Set manual gain - RTL-SDR will select nearest supported value
                self._device.gain = gain

            self._gain = gain
            logger.debug(f"RTL-SDR gain set to {gain} dB")
            return True
        except Exception as e:
            logger.error(f"Failed to set gain: {e}")
            return False

    def read_samples(self, num_samples: int) -> np.ndarray:
        """Read complex IQ samples from device."""
        if not self.is_open or self._device is None:
            raise DeviceConnectionError("Device not open")

        try:
            # pyrtlsdr returns complex64 samples
            samples = self._device.read_samples(num_samples)
            return np.array(samples, dtype=np.complex64)
        except Exception as e:
            logger.error(f"Failed to read samples: {e}")
            raise

    def get_device_info(self) -> DeviceInfo:
        """Get device information."""
        gains = []
        if self.is_open and self._device is not None:
            try:
                gains = list(self._device.valid_gains_db)
            except Exception:
                gains = [0, 10, 20, 30, 40, 50]

        return DeviceInfo(
            device_type=DeviceType.RTLSDR,
            serial_number=self._serial,
            name=f"RTL-SDR #{self.device_index}",
            min_freq=self.MIN_FREQ,
            max_freq=self.MAX_FREQ,
            min_sample_rate=225e3,
            max_sample_rate=3.2e6,
            supported_gains=gains
        )

    def get_supported_sample_rates(self) -> List[float]:
        """Get list of commonly used sample rates."""
        return self.SUPPORTED_SAMPLE_RATES.copy()

    def set_freq_correction(self, ppm: int) -> bool:
        """
        Set frequency correction in PPM.

        Args:
            ppm: Parts per million correction value

        Returns:
            True if successful
        """
        if not self.is_open or self._device is None:
            raise DeviceConnectionError("Device not open")

        try:
            self._device.freq_correction = ppm
            logger.debug(f"RTL-SDR frequency correction set to {ppm} PPM")
            return True
        except Exception as e:
            logger.error(f"Failed to set frequency correction: {e}")
            return False

    def set_direct_sampling(self, mode: int) -> bool:
        """
        Enable direct sampling mode for HF reception.

        Args:
            mode: 0=disabled, 1=I-branch, 2=Q-branch

        Returns:
            True if successful
        """
        if not self.is_open or self._device is None:
            raise DeviceConnectionError("Device not open")

        try:
            self._device.set_direct_sampling(mode)
            logger.debug(f"RTL-SDR direct sampling mode set to {mode}")
            return True
        except Exception as e:
            logger.error(f"Failed to set direct sampling: {e}")
            return False

    @staticmethod
    def get_device_count() -> int:
        """Get number of available RTL-SDR devices."""
        if not RTLSDR_AVAILABLE:
            return 0

        try:
            # Try to enumerate devices
            count = 0
            for i in range(10):  # Check up to 10 devices
                try:
                    sdr = RtlSdr(i)
                    sdr.close()
                    count += 1
                except Exception:
                    break
            return count
        except Exception:
            return 0

    @staticmethod
    def detect_devices() -> List[dict]:
        """
        Detect all connected RTL-SDR devices.

        Returns:
            List of device info dictionaries
        """
        if not RTLSDR_AVAILABLE:
            return []

        devices = []
        for i in range(10):
            try:
                sdr = RtlSdr(i)
                try:
                    serial = sdr.get_device_serial_addresses()[i]
                except Exception:
                    serial = f"rtlsdr_{i}"

                devices.append({
                    'type': 'rtlsdr',
                    'index': i,
                    'serial': serial,
                    'name': f"RTL-SDR #{i}"
                })
                sdr.close()
            except Exception:
                break

        return devices
