"""
HackRF Device Implementation

This module provides support for HackRF One SDR devices.
HackRF One is a wideband SDR capable of both receive and transmit.

Frequency range: 1 MHz to 6 GHz
Sample rate: 2 MHz to 20 MHz
"""

from typing import Optional, List
import numpy as np
from loguru import logger

from .base import (
    SDRDevice, DeviceType, DeviceInfo,
    DeviceNotFoundError, DeviceConnectionError,
    FrequencyOutOfRangeError, SampleRateError
)

# Try to import hackrf library
try:
    import hackrf
    HACKRF_AVAILABLE = True
except ImportError:
    hackrf = None
    HACKRF_AVAILABLE = False
    logger.warning("hackrf library not installed. HackRF support disabled.")


class HackRFDevice(SDRDevice):
    """
    HackRF One device implementation.

    The HackRF One is a wideband Software Defined Radio peripheral
    capable of transmission or reception of radio signals from 1 MHz to 6 GHz.

    Specifications:
    - Frequency range: 1 MHz - 6 GHz
    - Sample rates: 2 MHz - 20 MHz
    - Resolution: 8-bit ADC
    - Half duplex (TX or RX, not both)
    """

    # Supported sample rates for HackRF
    SUPPORTED_SAMPLE_RATES = [2e6, 4e6, 8e6, 10e6, 12.5e6, 16e6, 20e6]

    # Frequency range
    MIN_FREQ = 1e6       # 1 MHz
    MAX_FREQ = 6000e6    # 6 GHz

    # Gain ranges
    LNA_GAIN_RANGE = list(range(0, 41, 8))  # 0, 8, 16, 24, 32, 40 dB
    VGA_GAIN_RANGE = list(range(0, 63, 2))  # 0-62 dB in 2 dB steps
    AMP_ENABLE = [0, 14]  # RF amplifier: off or 14 dB

    def __init__(self, serial_number: Optional[str] = None):
        """
        Initialize HackRF device.

        Args:
            serial_number: Optional serial number to select specific device
        """
        super().__init__(device_id=serial_number)
        self._device = None
        self._serial = serial_number
        self._lna_gain = 16
        self._vga_gain = 20
        self._amp_enable = False
        self._sample_rate = 8e6  # Default for HackRF

        if not HACKRF_AVAILABLE:
            logger.error("HackRF library not available")

    @property
    def device_type(self) -> DeviceType:
        return DeviceType.HACKRF

    def open(self) -> bool:
        """Open connection to HackRF device."""
        if not HACKRF_AVAILABLE:
            raise DeviceNotFoundError("hackrf library not installed")

        if self.is_open:
            logger.warning("Device already open")
            return True

        try:
            self._device = hackrf.HackRF()
            self.is_open = True

            # Get serial number if not specified
            if self._serial is None:
                try:
                    self._serial = self._device.serial_number
                except Exception:
                    self._serial = "hackrf_unknown"

            # Set default parameters
            self._device.sample_rate = self._sample_rate
            self._device.center_freq = self._center_freq

            # Configure gains
            self._set_gains()

            logger.info(f"HackRF opened: serial={self._serial}")
            return True

        except Exception as e:
            logger.error(f"Failed to open HackRF: {e}")
            raise DeviceConnectionError(f"Failed to open HackRF: {e}")

    def close(self) -> None:
        """Close connection to HackRF device."""
        if self._device is not None:
            try:
                self._device.close()
                logger.info(f"HackRF closed: serial={self._serial}")
            except Exception as e:
                logger.warning(f"Error closing HackRF: {e}")
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
            self._device.center_freq = int(freq)
            self._center_freq = freq
            logger.debug(f"HackRF frequency set to {freq/1e6:.3f} MHz")
            return True
        except Exception as e:
            logger.error(f"Failed to set frequency: {e}")
            return False

    def set_sample_rate(self, rate: float) -> bool:
        """Set sample rate."""
        if not self.is_open or self._device is None:
            raise DeviceConnectionError("Device not open")

        # HackRF supports 2 MHz to 20 MHz
        if rate < 2e6 or rate > 20e6:
            raise SampleRateError(
                f"Sample rate {rate/1e6:.2f} MHz out of range (2 - 20 MHz)"
            )

        try:
            self._device.sample_rate = int(rate)
            self._sample_rate = rate
            logger.debug(f"HackRF sample rate set to {rate/1e6:.3f} MHz")
            return True
        except Exception as e:
            logger.error(f"Failed to set sample rate: {e}")
            return False

    def set_gain(self, gain: int) -> bool:
        """
        Set gain (distributes gain across LNA and VGA).

        Args:
            gain: Total gain in dB (will be split between LNA and VGA)
        """
        if not self.is_open or self._device is None:
            raise DeviceConnectionError("Device not open")

        # Distribute gain between LNA (max 40) and VGA (max 62)
        # Prioritize LNA gain for lower noise figure
        if gain <= 40:
            self._lna_gain = (gain // 8) * 8  # Round to nearest 8
            self._vga_gain = gain - self._lna_gain
        else:
            self._lna_gain = 40
            self._vga_gain = min(gain - 40, 62)

        self._gain = self._lna_gain + self._vga_gain

        return self._set_gains()

    def _set_gains(self) -> bool:
        """Apply current gain settings to device."""
        if self._device is None:
            return False

        try:
            self._device.lna_gain = self._lna_gain
            self._device.vga_gain = self._vga_gain
            if hasattr(self._device, 'amp_enable'):
                self._device.amp_enable = self._amp_enable
            logger.debug(f"HackRF gains: LNA={self._lna_gain}, VGA={self._vga_gain}")
            return True
        except Exception as e:
            logger.error(f"Failed to set gains: {e}")
            return False

    def set_lna_gain(self, gain: int) -> bool:
        """
        Set LNA gain directly.

        Args:
            gain: LNA gain (0, 8, 16, 24, 32, or 40 dB)
        """
        if gain not in self.LNA_GAIN_RANGE:
            logger.warning(f"LNA gain {gain} not in valid range, using nearest")
            gain = min(self.LNA_GAIN_RANGE, key=lambda x: abs(x - gain))

        self._lna_gain = gain
        self._gain = self._lna_gain + self._vga_gain
        return self._set_gains()

    def set_vga_gain(self, gain: int) -> bool:
        """
        Set VGA gain directly.

        Args:
            gain: VGA gain (0-62 dB in 2 dB steps)
        """
        gain = max(0, min(62, gain))
        gain = (gain // 2) * 2  # Round to even

        self._vga_gain = gain
        self._gain = self._lna_gain + self._vga_gain
        return self._set_gains()

    def set_amp_enable(self, enable: bool) -> bool:
        """
        Enable/disable RF amplifier (+14 dB).

        Args:
            enable: True to enable amplifier
        """
        self._amp_enable = enable
        return self._set_gains()

    def read_samples(self, num_samples: int) -> np.ndarray:
        """Read complex IQ samples from device."""
        if not self.is_open or self._device is None:
            raise DeviceConnectionError("Device not open")

        try:
            # HackRF returns interleaved 8-bit signed I/Q samples
            raw_data = self._device.read_samples(num_samples)

            # Convert to complex64
            # The hackrf library should return this directly, but handle raw data too
            if isinstance(raw_data, np.ndarray):
                if raw_data.dtype == np.complex64:
                    return raw_data
                elif raw_data.dtype in (np.int8, np.uint8):
                    # Convert interleaved I/Q to complex
                    raw_float = raw_data.astype(np.float32) / 128.0
                    iq_samples = raw_float[::2] + 1j * raw_float[1::2]
                    return iq_samples.astype(np.complex64)

            return np.array(raw_data, dtype=np.complex64)

        except Exception as e:
            logger.error(f"Failed to read samples: {e}")
            raise

    def get_device_info(self) -> DeviceInfo:
        """Get device information."""
        # Combined gain range
        max_gain = max(self.LNA_GAIN_RANGE) + max(self.VGA_GAIN_RANGE)
        gains = list(range(0, max_gain + 1, 2))

        return DeviceInfo(
            device_type=DeviceType.HACKRF,
            serial_number=self._serial,
            name=f"HackRF One",
            min_freq=self.MIN_FREQ,
            max_freq=self.MAX_FREQ,
            min_sample_rate=2e6,
            max_sample_rate=20e6,
            supported_gains=gains
        )

    def get_supported_sample_rates(self) -> List[float]:
        """Get list of commonly used sample rates."""
        return self.SUPPORTED_SAMPLE_RATES.copy()

    def set_baseband_filter_bandwidth(self, bandwidth: float) -> bool:
        """
        Set the baseband filter bandwidth.

        Args:
            bandwidth: Filter bandwidth in Hz

        Returns:
            True if successful
        """
        if not self.is_open or self._device is None:
            raise DeviceConnectionError("Device not open")

        try:
            if hasattr(self._device, 'baseband_filter_bandwidth'):
                self._device.baseband_filter_bandwidth = int(bandwidth)
                logger.debug(f"HackRF filter bandwidth set to {bandwidth/1e6:.3f} MHz")
            return True
        except Exception as e:
            logger.error(f"Failed to set filter bandwidth: {e}")
            return False

    @staticmethod
    def detect_devices() -> List[dict]:
        """
        Detect all connected HackRF devices.

        Returns:
            List of device info dictionaries
        """
        if not HACKRF_AVAILABLE:
            return []

        devices = []
        try:
            # HackRF library typically handles single device
            device = hackrf.HackRF()
            try:
                serial = device.serial_number
            except Exception:
                serial = "hackrf_unknown"

            devices.append({
                'type': 'hackrf',
                'serial': serial,
                'name': 'HackRF One'
            })
            device.close()
        except Exception as e:
            logger.debug(f"No HackRF found: {e}")

        return devices
