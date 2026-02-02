"""
SDR Abstraction Layer - Base Classes

This module provides the abstract interface for Software Defined Radio devices.
All SDR implementations (HackRF, RTL-SDR, etc.) inherit from these base classes.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Tuple, Optional, List, Callable
from enum import Enum
import numpy as np
import time


class DeviceType(Enum):
    """Supported SDR device types"""
    HACKRF = "hackrf"
    RTLSDR = "rtlsdr"
    MOCK = "mock"


@dataclass
class ScanParameters:
    """Parameters for spectrum scanning operations"""
    start_freq: float           # Start frequency in Hz
    stop_freq: float            # Stop frequency in Hz
    bin_size: float = 10000     # FFT bin size in Hz (resolution)
    sample_rate: float = 2.4e6  # Sample rate in Hz
    gain: int = 20              # Gain in dB
    integration_time: float = 0.1  # Seconds per measurement
    fft_size: int = 1024        # FFT window size

    def __post_init__(self):
        """Validate scan parameters"""
        if self.start_freq >= self.stop_freq:
            raise ValueError("start_freq must be less than stop_freq")
        if self.start_freq < 0:
            raise ValueError("start_freq must be positive")
        if self.sample_rate <= 0:
            raise ValueError("sample_rate must be positive")
        if self.integration_time <= 0:
            raise ValueError("integration_time must be positive")

    @property
    def num_steps(self) -> int:
        """Calculate number of frequency steps needed for sweep"""
        return int(np.ceil((self.stop_freq - self.start_freq) / self.sample_rate))

    @property
    def actual_bin_size(self) -> float:
        """Calculate actual frequency resolution"""
        return self.sample_rate / self.fft_size


@dataclass
class SpectrumData:
    """Container for spectrum measurement results"""
    frequencies: np.ndarray     # Frequency array in Hz
    power_dbm: np.ndarray       # Power array in dBm
    timestamp: float            # Unix timestamp
    center_freq: float          # Center frequency of measurement
    sample_rate: float          # Sample rate used
    fft_size: int               # FFT size used
    noise_floor: Optional[float] = None  # Estimated noise floor in dBm

    def __post_init__(self):
        """Ensure arrays are numpy arrays"""
        if not isinstance(self.frequencies, np.ndarray):
            self.frequencies = np.array(self.frequencies)
        if not isinstance(self.power_dbm, np.ndarray):
            self.power_dbm = np.array(self.power_dbm)


@dataclass
class SweepResult:
    """Result of a complete frequency sweep"""
    frequencies: np.ndarray     # Combined frequency array
    power_dbm: np.ndarray       # Combined power array
    timestamp: float            # When sweep started
    sweep_time: float           # Total time for sweep
    start_freq: float           # Sweep start frequency
    stop_freq: float            # Sweep stop frequency
    num_steps: int              # Number of frequency steps

    def get_frequency_range(self, start: float, stop: float) -> Tuple[np.ndarray, np.ndarray]:
        """Extract a frequency range from the sweep result"""
        mask = (self.frequencies >= start) & (self.frequencies <= stop)
        return self.frequencies[mask], self.power_dbm[mask]


@dataclass
class DetectedSignal:
    """Represents a detected signal/peak in the spectrum"""
    frequency: float            # Center frequency in Hz
    power_dbm: float            # Peak power in dBm
    bandwidth: float            # Estimated bandwidth in Hz
    snr_db: Optional[float] = None  # Signal-to-noise ratio


@dataclass
class DeviceInfo:
    """Information about an SDR device"""
    device_type: DeviceType
    serial_number: Optional[str] = None
    name: str = ""
    min_freq: float = 1e6       # Minimum supported frequency
    max_freq: float = 6e9       # Maximum supported frequency
    min_sample_rate: float = 225e3
    max_sample_rate: float = 3.2e6
    supported_gains: List[int] = field(default_factory=list)


class SDRDevice(ABC):
    """
    Abstract base class for all SDR devices.

    This class defines the interface that all SDR device implementations
    must follow. It handles common functionality like power spectrum
    computation while leaving hardware-specific operations to subclasses.
    """

    def __init__(self, device_id: Optional[str] = None):
        """
        Initialize SDR device.

        Args:
            device_id: Optional device identifier (serial number, index, etc.)
        """
        self.device_id = device_id
        self.is_open = False
        self._sample_rate = 2.4e6
        self._center_freq = 100e6
        self._gain = 20
        self._device_info: Optional[DeviceInfo] = None

    @property
    def sample_rate(self) -> float:
        """Current sample rate in Hz"""
        return self._sample_rate

    @property
    def center_freq(self) -> float:
        """Current center frequency in Hz"""
        return self._center_freq

    @property
    def gain(self) -> int:
        """Current gain in dB"""
        return self._gain

    @property
    @abstractmethod
    def device_type(self) -> DeviceType:
        """Return the device type"""
        pass

    @abstractmethod
    def open(self) -> bool:
        """
        Open connection to the SDR device.

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """Close connection to the SDR device"""
        pass

    @abstractmethod
    def set_center_freq(self, freq: float) -> bool:
        """
        Set the center frequency.

        Args:
            freq: Frequency in Hz

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def set_sample_rate(self, rate: float) -> bool:
        """
        Set the sample rate.

        Args:
            rate: Sample rate in Hz

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def set_gain(self, gain: int) -> bool:
        """
        Set the gain.

        Args:
            gain: Gain in dB

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def read_samples(self, num_samples: int) -> np.ndarray:
        """
        Read IQ samples from the device.

        Args:
            num_samples: Number of complex samples to read

        Returns:
            Numpy array of complex IQ samples
        """
        pass

    @abstractmethod
    def get_device_info(self) -> DeviceInfo:
        """
        Get device information.

        Returns:
            DeviceInfo object with device capabilities
        """
        pass

    def get_supported_sample_rates(self) -> List[float]:
        """
        Get list of supported sample rates.

        Returns:
            List of supported sample rates in Hz
        """
        info = self.get_device_info()
        # Return common sample rates within device range
        common_rates = [225e3, 300e3, 900e3, 1.2e6, 1.8e6, 2.4e6, 3.2e6]
        return [r for r in common_rates
                if info.min_sample_rate <= r <= info.max_sample_rate]

    def compute_power_spectrum(
        self,
        samples: np.ndarray,
        fft_size: int = 1024,
        window: str = 'hanning'
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Compute power spectrum from IQ samples.

        Uses FFT to convert time-domain IQ samples to frequency-domain
        power spectrum. Applies windowing to reduce spectral leakage.

        Args:
            samples: Complex IQ samples
            fft_size: FFT window size
            window: Window function ('hanning', 'hamming', 'blackman', 'none')

        Returns:
            Tuple of (frequencies, power_dbm) arrays
        """
        # Apply window function
        if window == 'hanning':
            win = np.hanning(len(samples))
        elif window == 'hamming':
            win = np.hamming(len(samples))
        elif window == 'blackman':
            win = np.blackman(len(samples))
        else:
            win = np.ones(len(samples))

        windowed_samples = samples * win

        # Compute FFT
        spectrum = np.fft.fftshift(np.fft.fft(windowed_samples, n=fft_size))

        # Convert to power (magnitude squared)
        power = np.abs(spectrum) ** 2

        # Normalize by FFT size and window power
        window_power = np.sum(win ** 2)
        power = power / (window_power * fft_size)

        # Convert to dBm (assuming 50 ohm impedance)
        # P(dBm) = 10*log10(P_watts * 1000)
        # For normalized FFT output, we add calibration offset
        with np.errstate(divide='ignore'):
            power_dbm = 10 * np.log10(power + 1e-20) + 30  # +30 for mW to dBm

        # Generate frequency axis
        freq_step = self._sample_rate / fft_size
        frequencies = np.arange(-fft_size/2, fft_size/2) * freq_step + self._center_freq

        return frequencies, power_dbm

    def get_spectrum(
        self,
        num_samples: Optional[int] = None,
        fft_size: int = 1024,
        average_count: int = 1
    ) -> SpectrumData:
        """
        Get a single spectrum measurement at current frequency.

        Args:
            num_samples: Number of samples (default: fft_size * average_count)
            fft_size: FFT size for spectrum computation
            average_count: Number of spectra to average

        Returns:
            SpectrumData object with measurement results
        """
        if not self.is_open:
            raise RuntimeError("Device not open")

        if num_samples is None:
            num_samples = fft_size * average_count

        # Read samples
        samples = self.read_samples(num_samples)

        # Compute averaged spectrum
        power_sum = None
        num_ffts = len(samples) // fft_size

        for i in range(num_ffts):
            chunk = samples[i * fft_size:(i + 1) * fft_size]
            frequencies, power = self.compute_power_spectrum(chunk, fft_size)

            if power_sum is None:
                power_sum = power
            else:
                # Average in linear domain for proper noise reduction
                power_sum = power_sum + 10 ** (power / 10)

        # Convert back to dBm
        power_avg = 10 * np.log10(power_sum / num_ffts)

        # Estimate noise floor (lowest 10% of readings)
        sorted_power = np.sort(power_avg)
        noise_floor = np.mean(sorted_power[:len(sorted_power) // 10])

        return SpectrumData(
            frequencies=frequencies,
            power_dbm=power_avg,
            timestamp=time.time(),
            center_freq=self._center_freq,
            sample_rate=self._sample_rate,
            fft_size=fft_size,
            noise_floor=noise_floor
        )

    def __enter__(self):
        """Context manager entry"""
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()

    def __repr__(self) -> str:
        return (f"{self.__class__.__name__}("
                f"device_id={self.device_id}, "
                f"is_open={self.is_open}, "
                f"center_freq={self._center_freq/1e6:.2f}MHz)")


class SDRError(Exception):
    """Base exception for SDR-related errors"""
    pass


class DeviceNotFoundError(SDRError):
    """Raised when SDR device cannot be found"""
    pass


class DeviceConnectionError(SDRError):
    """Raised when connection to SDR device fails"""
    pass


class FrequencyOutOfRangeError(SDRError):
    """Raised when requested frequency is outside device range"""
    pass


class SampleRateError(SDRError):
    """Raised when sample rate configuration fails"""
    pass
