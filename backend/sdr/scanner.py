"""
Spectrum Scanner Engine

This module provides the core spectrum scanning functionality for the
RF Spectrum Monitor. It manages frequency sweeps, continuous scanning,
signal detection, and data processing.
"""

from typing import List, Optional, Callable, Tuple, Dict, Any
from dataclasses import dataclass
import numpy as np
import time
import threading
from loguru import logger
from scipy import signal as scipy_signal
from scipy.ndimage import maximum_filter1d

from .base import (
    SDRDevice, ScanParameters, SpectrumData, SweepResult, DetectedSignal
)


@dataclass
class ScannerConfig:
    """Configuration for the spectrum scanner"""
    fft_size: int = 1024
    window: str = 'hanning'           # Window function
    overlap: float = 0.5              # FFT overlap ratio
    averaging: int = 4                # Number of FFTs to average
    peak_threshold_db: float = 10     # dB above noise floor
    min_peak_distance_hz: float = 100e3  # Minimum separation between peaks
    settle_time: float = 0.01         # Time to wait after frequency change


class SpectrumScanner:
    """
    Manages spectrum scanning operations.

    This class handles:
    - Single frequency spectrum measurements
    - Wideband frequency sweeps
    - Continuous scanning with callbacks
    - Signal/peak detection
    - Bandwidth estimation
    """

    def __init__(self, device: SDRDevice, config: Optional[ScannerConfig] = None):
        """
        Initialize spectrum scanner.

        Args:
            device: SDR device to use for scanning
            config: Optional scanner configuration
        """
        self.device = device
        self.config = config or ScannerConfig()
        self._is_scanning = False
        self._stop_requested = False
        self._scan_thread: Optional[threading.Thread] = None
        self._callback: Optional[Callable[[SweepResult], None]] = None
        self._lock = threading.Lock()

        logger.info(f"Scanner initialized with device: {device}")

    @property
    def is_scanning(self) -> bool:
        """Check if scanning is currently active"""
        return self._is_scanning

    def single_measurement(
        self,
        center_freq: Optional[float] = None,
        sample_rate: Optional[float] = None,
        gain: Optional[int] = None
    ) -> SpectrumData:
        """
        Perform a single spectrum measurement at current/specified frequency.

        Args:
            center_freq: Optional center frequency (uses current if None)
            sample_rate: Optional sample rate (uses current if None)
            gain: Optional gain (uses current if None)

        Returns:
            SpectrumData with measurement results
        """
        if not self.device.is_open:
            raise RuntimeError("Device not open")

        # Apply settings if specified
        if center_freq is not None:
            self.device.set_center_freq(center_freq)
        if sample_rate is not None:
            self.device.set_sample_rate(sample_rate)
        if gain is not None:
            self.device.set_gain(gain)

        # Allow device to settle
        time.sleep(self.config.settle_time)

        # Get spectrum with averaging
        return self.device.get_spectrum(
            fft_size=self.config.fft_size,
            average_count=self.config.averaging
        )

    def single_sweep(self, params: ScanParameters) -> SweepResult:
        """
        Perform a single frequency sweep across the specified range.

        Args:
            params: Scan parameters defining the sweep

        Returns:
            SweepResult with combined spectrum data
        """
        if not self.device.is_open:
            raise RuntimeError("Device not open")

        start_time = time.time()
        logger.info(
            f"Starting sweep: {params.start_freq/1e6:.2f} - {params.stop_freq/1e6:.2f} MHz"
        )

        # Configure device
        self.device.set_sample_rate(params.sample_rate)
        self.device.set_gain(params.gain)

        # Calculate sweep steps
        bandwidth = params.sample_rate * 0.8  # Use 80% of bandwidth (avoid edges)
        num_steps = int(np.ceil((params.stop_freq - params.start_freq) / bandwidth))

        all_frequencies = []
        all_power = []
        step_count = 0

        for i in range(num_steps):
            if self._stop_requested:
                logger.info("Sweep stopped by request")
                break

            # Calculate center frequency for this step
            center_freq = params.start_freq + bandwidth/2 + (i * bandwidth)

            # Don't exceed stop frequency
            if center_freq - bandwidth/2 > params.stop_freq:
                break

            # Set frequency and wait for settle
            self.device.set_center_freq(center_freq)
            time.sleep(self.config.settle_time)

            # Calculate number of samples for integration time
            num_samples = int(params.sample_rate * params.integration_time)
            num_samples = max(num_samples, self.config.fft_size * self.config.averaging)

            # Read samples
            samples = self.device.read_samples(num_samples)

            # Compute averaged spectrum
            spectrum_data = self._compute_averaged_spectrum(samples, params.sample_rate)

            # Trim edges (filter roll-off)
            trim_bins = int(len(spectrum_data.frequencies) * 0.1)
            frequencies = spectrum_data.frequencies[trim_bins:-trim_bins]
            power = spectrum_data.power_dbm[trim_bins:-trim_bins]

            # Filter to requested range
            mask = (frequencies >= params.start_freq) & (frequencies <= params.stop_freq)
            frequencies = frequencies[mask]
            power = power[mask]

            all_frequencies.extend(frequencies)
            all_power.extend(power)
            step_count += 1

        sweep_time = time.time() - start_time

        # Sort by frequency (in case of overlap)
        if all_frequencies:
            sorted_indices = np.argsort(all_frequencies)
            all_frequencies = np.array(all_frequencies)[sorted_indices]
            all_power = np.array(all_power)[sorted_indices]
        else:
            all_frequencies = np.array([])
            all_power = np.array([])

        logger.info(
            f"Sweep completed: {step_count} steps, {len(all_frequencies)} points, "
            f"{sweep_time:.2f}s"
        )

        return SweepResult(
            frequencies=all_frequencies,
            power_dbm=all_power,
            timestamp=start_time,
            sweep_time=sweep_time,
            start_freq=params.start_freq,
            stop_freq=params.stop_freq,
            num_steps=step_count
        )

    def continuous_scan(
        self,
        params: ScanParameters,
        callback: Callable[[SweepResult], None],
        interval: float = 0.0
    ) -> None:
        """
        Start continuous scanning in background thread.

        Args:
            params: Scan parameters
            callback: Function to call with each sweep result
            interval: Minimum time between sweeps (0 = continuous)
        """
        if self._is_scanning:
            logger.warning("Scanning already in progress")
            return

        self._callback = callback
        self._stop_requested = False
        self._is_scanning = True

        def scan_loop():
            try:
                while not self._stop_requested:
                    sweep_start = time.time()

                    result = self.single_sweep(params)

                    if self._callback and not self._stop_requested:
                        try:
                            self._callback(result)
                        except Exception as e:
                            logger.error(f"Callback error: {e}")

                    # Wait for interval if specified
                    elapsed = time.time() - sweep_start
                    if interval > 0 and elapsed < interval:
                        time.sleep(interval - elapsed)

            except Exception as e:
                logger.error(f"Scan loop error: {e}")
            finally:
                self._is_scanning = False
                logger.info("Continuous scanning stopped")

        self._scan_thread = threading.Thread(target=scan_loop, daemon=True)
        self._scan_thread.start()
        logger.info("Continuous scanning started")

    def stop_scan(self) -> None:
        """Stop continuous scanning"""
        if not self._is_scanning:
            return

        logger.info("Requesting scan stop...")
        self._stop_requested = True

        # Wait for thread to finish (with timeout)
        if self._scan_thread and self._scan_thread.is_alive():
            self._scan_thread.join(timeout=5.0)
            if self._scan_thread.is_alive():
                logger.warning("Scan thread did not stop gracefully")

        self._is_scanning = False
        self._scan_thread = None

    def detect_peaks(
        self,
        frequencies: np.ndarray,
        power_dbm: np.ndarray,
        threshold_db: Optional[float] = None,
        min_distance_hz: Optional[float] = None
    ) -> List[DetectedSignal]:
        """
        Detect signal peaks in spectrum data.

        Uses a local maximum algorithm with noise floor estimation
        to find signals above the threshold.

        Args:
            frequencies: Frequency array (Hz)
            power_dbm: Power array (dBm)
            threshold_db: Detection threshold above noise floor
            min_distance_hz: Minimum separation between peaks

        Returns:
            List of DetectedSignal objects
        """
        if len(frequencies) == 0:
            return []

        threshold_db = threshold_db or self.config.peak_threshold_db
        min_distance_hz = min_distance_hz or self.config.min_peak_distance_hz

        # Estimate noise floor (median of lower 30%)
        sorted_power = np.sort(power_dbm)
        noise_floor = np.median(sorted_power[:len(sorted_power) * 3 // 10])

        # Calculate detection threshold
        threshold = noise_floor + threshold_db

        # Calculate minimum peak distance in bins
        freq_step = (frequencies[-1] - frequencies[0]) / (len(frequencies) - 1) if len(frequencies) > 1 else 1
        min_distance_bins = max(1, int(min_distance_hz / freq_step))

        # Find peaks using scipy
        peaks, properties = scipy_signal.find_peaks(
            power_dbm,
            height=threshold,
            distance=min_distance_bins,
            prominence=3  # Minimum prominence in dB
        )

        detected_signals = []
        for peak_idx in peaks:
            freq = frequencies[peak_idx]
            power = power_dbm[peak_idx]
            bandwidth = self._estimate_bandwidth(frequencies, power_dbm, peak_idx)
            snr = power - noise_floor

            detected_signals.append(DetectedSignal(
                frequency=freq,
                power_dbm=power,
                bandwidth=bandwidth,
                snr_db=snr
            ))

        logger.debug(f"Detected {len(detected_signals)} signals above {threshold:.1f} dBm")
        return detected_signals

    def _estimate_bandwidth(
        self,
        frequencies: np.ndarray,
        power_dbm: np.ndarray,
        peak_idx: int,
        db_down: float = 3.0
    ) -> float:
        """
        Estimate the bandwidth of a signal at a peak.

        Uses the -3dB (or specified) points on either side of the peak.

        Args:
            frequencies: Frequency array
            power_dbm: Power array
            peak_idx: Index of the peak
            db_down: dB below peak for bandwidth measurement

        Returns:
            Estimated bandwidth in Hz
        """
        peak_power = power_dbm[peak_idx]
        threshold = peak_power - db_down

        # Find lower edge
        lower_idx = peak_idx
        while lower_idx > 0 and power_dbm[lower_idx] > threshold:
            lower_idx -= 1

        # Find upper edge
        upper_idx = peak_idx
        while upper_idx < len(power_dbm) - 1 and power_dbm[upper_idx] > threshold:
            upper_idx += 1

        # Calculate bandwidth
        bandwidth = abs(frequencies[upper_idx] - frequencies[lower_idx])

        # Minimum bandwidth is one FFT bin
        min_bandwidth = abs(frequencies[1] - frequencies[0]) if len(frequencies) > 1 else 1000
        return max(bandwidth, min_bandwidth)

    def _compute_averaged_spectrum(
        self,
        samples: np.ndarray,
        sample_rate: float
    ) -> SpectrumData:
        """
        Compute averaged power spectrum from samples.

        Uses Welch's method with overlapping segments for noise reduction.

        Args:
            samples: Complex IQ samples
            sample_rate: Sample rate in Hz

        Returns:
            SpectrumData with averaged spectrum
        """
        fft_size = self.config.fft_size

        # Create window
        if self.config.window == 'hanning':
            window = np.hanning(fft_size)
        elif self.config.window == 'hamming':
            window = np.hamming(fft_size)
        elif self.config.window == 'blackman':
            window = np.blackman(fft_size)
        else:
            window = np.ones(fft_size)

        # Calculate overlap
        hop_size = int(fft_size * (1 - self.config.overlap))
        num_segments = (len(samples) - fft_size) // hop_size + 1
        num_segments = max(1, num_segments)

        # Accumulate power spectra
        power_sum = np.zeros(fft_size)

        for i in range(num_segments):
            start = i * hop_size
            segment = samples[start:start + fft_size]

            if len(segment) < fft_size:
                # Pad if necessary
                segment = np.pad(segment, (0, fft_size - len(segment)))

            # Apply window and compute FFT
            windowed = segment * window
            spectrum = np.fft.fftshift(np.fft.fft(windowed))

            # Accumulate power
            power_sum += np.abs(spectrum) ** 2

        # Average and normalize
        power_avg = power_sum / num_segments
        window_power = np.sum(window ** 2)
        power_norm = power_avg / (window_power * fft_size)

        # Convert to dBm
        with np.errstate(divide='ignore'):
            power_dbm = 10 * np.log10(power_norm + 1e-20) + 30

        # Generate frequency axis
        freq_step = sample_rate / fft_size
        frequencies = np.arange(-fft_size/2, fft_size/2) * freq_step + self.device.center_freq

        # Estimate noise floor
        sorted_power = np.sort(power_dbm)
        noise_floor = np.median(sorted_power[:len(sorted_power) // 10])

        return SpectrumData(
            frequencies=frequencies,
            power_dbm=power_dbm,
            timestamp=time.time(),
            center_freq=self.device.center_freq,
            sample_rate=sample_rate,
            fft_size=fft_size,
            noise_floor=noise_floor
        )

    def get_signal_statistics(
        self,
        frequencies: np.ndarray,
        power_dbm: np.ndarray,
        freq_range: Optional[Tuple[float, float]] = None
    ) -> Dict[str, float]:
        """
        Calculate statistics for a spectrum or frequency range.

        Args:
            frequencies: Frequency array
            power_dbm: Power array
            freq_range: Optional (start, stop) frequency range

        Returns:
            Dictionary with statistics
        """
        if freq_range is not None:
            mask = (frequencies >= freq_range[0]) & (frequencies <= freq_range[1])
            power = power_dbm[mask]
        else:
            power = power_dbm

        if len(power) == 0:
            return {}

        return {
            'min_power_dbm': float(np.min(power)),
            'max_power_dbm': float(np.max(power)),
            'mean_power_dbm': float(np.mean(power)),
            'median_power_dbm': float(np.median(power)),
            'std_power_db': float(np.std(power)),
            'noise_floor_dbm': float(np.percentile(power, 10)),
            'dynamic_range_db': float(np.max(power) - np.min(power)),
            'num_points': len(power)
        }


def create_scanner(
    device_type: str = 'mock',
    device_id: Optional[str] = None,
    **kwargs
) -> Tuple[SDRDevice, SpectrumScanner]:
    """
    Factory function to create an SDR device and scanner.

    Args:
        device_type: Type of device ('mock', 'rtlsdr', 'hackrf')
        device_id: Optional device identifier
        **kwargs: Additional arguments for scanner config

    Returns:
        Tuple of (device, scanner)
    """
    from .mock import MockSDRDevice
    from .rtlsdr import RTLSDRDevice
    from .hackrf import HackRFDevice

    if device_type == 'mock':
        device = MockSDRDevice(device_id=device_id or 'mock_0')
    elif device_type == 'rtlsdr':
        device = RTLSDRDevice(device_index=int(device_id or 0))
    elif device_type == 'hackrf':
        device = HackRFDevice(serial_number=device_id)
    else:
        raise ValueError(f"Unknown device type: {device_type}")

    config = ScannerConfig(**kwargs) if kwargs else None
    scanner = SpectrumScanner(device, config)

    return device, scanner
