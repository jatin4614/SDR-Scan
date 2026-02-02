"""
Signal Processor

This module provides DSP utilities for spectrum analysis including
peak detection, bandwidth estimation, signal classification, and
statistical analysis.
"""

from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict, Any
import numpy as np
from scipy import signal as scipy_signal
from scipy.ndimage import maximum_filter1d, minimum_filter1d
from loguru import logger


@dataclass
class SignalPeak:
    """Detected signal peak"""
    frequency: float        # Center frequency in Hz
    power_dbm: float        # Peak power in dBm
    bandwidth: float        # Estimated bandwidth in Hz
    snr_db: float          # Signal-to-noise ratio
    prominence: float       # Peak prominence in dB
    left_freq: float       # Left edge frequency
    right_freq: float      # Right edge frequency


@dataclass
class SpectrumStatistics:
    """Statistics for a spectrum segment"""
    min_power: float
    max_power: float
    mean_power: float
    median_power: float
    std_power: float
    noise_floor: float
    dynamic_range: float
    num_points: int
    freq_start: float
    freq_stop: float


class SignalProcessor:
    """
    Digital signal processing utilities for spectrum analysis.

    Provides methods for:
    - Peak detection
    - Bandwidth estimation
    - Noise floor estimation
    - Signal classification
    - Spectral smoothing
    """

    def __init__(
        self,
        peak_threshold_db: float = 10.0,
        min_peak_distance_hz: float = 50000,
        noise_percentile: float = 10
    ):
        """
        Initialize signal processor.

        Args:
            peak_threshold_db: Default threshold above noise floor for peak detection
            min_peak_distance_hz: Minimum frequency separation between peaks
            noise_percentile: Percentile for noise floor estimation
        """
        self.peak_threshold_db = peak_threshold_db
        self.min_peak_distance_hz = min_peak_distance_hz
        self.noise_percentile = noise_percentile

    def estimate_noise_floor(
        self,
        power_dbm: np.ndarray,
        method: str = 'percentile'
    ) -> float:
        """
        Estimate the noise floor of a spectrum.

        Args:
            power_dbm: Power array in dBm
            method: 'percentile', 'median', or 'histogram'

        Returns:
            Estimated noise floor in dBm
        """
        if len(power_dbm) == 0:
            return -100.0

        if method == 'percentile':
            return float(np.percentile(power_dbm, self.noise_percentile))

        elif method == 'median':
            # Use median of lower half
            sorted_power = np.sort(power_dbm)
            lower_half = sorted_power[:len(sorted_power)//2]
            return float(np.median(lower_half))

        elif method == 'histogram':
            # Find the mode of the histogram
            hist, bin_edges = np.histogram(power_dbm, bins=50)
            max_bin = np.argmax(hist)
            return float((bin_edges[max_bin] + bin_edges[max_bin + 1]) / 2)

        else:
            raise ValueError(f"Unknown method: {method}")

    def detect_peaks(
        self,
        frequencies: np.ndarray,
        power_dbm: np.ndarray,
        threshold_db: Optional[float] = None,
        min_distance_hz: Optional[float] = None,
        min_prominence: float = 3.0
    ) -> List[SignalPeak]:
        """
        Detect signal peaks in spectrum data.

        Args:
            frequencies: Frequency array in Hz
            power_dbm: Power array in dBm
            threshold_db: Detection threshold above noise floor
            min_distance_hz: Minimum separation between peaks
            min_prominence: Minimum peak prominence in dB

        Returns:
            List of detected SignalPeak objects
        """
        if len(frequencies) < 3:
            return []

        threshold_db = threshold_db or self.peak_threshold_db
        min_distance_hz = min_distance_hz or self.min_peak_distance_hz

        # Estimate noise floor
        noise_floor = self.estimate_noise_floor(power_dbm)
        detection_threshold = noise_floor + threshold_db

        # Calculate minimum distance in bins
        freq_step = (frequencies[-1] - frequencies[0]) / (len(frequencies) - 1)
        min_distance_bins = max(1, int(min_distance_hz / freq_step))

        # Find peaks using scipy
        peaks, properties = scipy_signal.find_peaks(
            power_dbm,
            height=detection_threshold,
            distance=min_distance_bins,
            prominence=min_prominence,
            width=1
        )

        # Build SignalPeak objects
        detected_signals = []
        for i, peak_idx in enumerate(peaks):
            # Estimate bandwidth
            left_idx, right_idx = self._find_bandwidth_edges(
                power_dbm, peak_idx, db_down=3.0
            )

            left_freq = frequencies[left_idx]
            right_freq = frequencies[right_idx]
            bandwidth = right_freq - left_freq

            peak = SignalPeak(
                frequency=frequencies[peak_idx],
                power_dbm=power_dbm[peak_idx],
                bandwidth=bandwidth,
                snr_db=power_dbm[peak_idx] - noise_floor,
                prominence=properties['prominences'][i],
                left_freq=left_freq,
                right_freq=right_freq
            )
            detected_signals.append(peak)

        logger.debug(f"Detected {len(detected_signals)} peaks above {detection_threshold:.1f} dBm")
        return detected_signals

    def _find_bandwidth_edges(
        self,
        power_dbm: np.ndarray,
        peak_idx: int,
        db_down: float = 3.0
    ) -> Tuple[int, int]:
        """
        Find the -3dB (or specified) bandwidth edges.

        Args:
            power_dbm: Power array
            peak_idx: Index of peak
            db_down: dB below peak for bandwidth measurement

        Returns:
            Tuple of (left_index, right_index)
        """
        peak_power = power_dbm[peak_idx]
        threshold = peak_power - db_down

        # Find left edge
        left_idx = peak_idx
        while left_idx > 0 and power_dbm[left_idx] > threshold:
            left_idx -= 1

        # Find right edge
        right_idx = peak_idx
        while right_idx < len(power_dbm) - 1 and power_dbm[right_idx] > threshold:
            right_idx += 1

        return left_idx, right_idx

    def smooth_spectrum(
        self,
        power_dbm: np.ndarray,
        window_size: int = 5,
        method: str = 'moving_average'
    ) -> np.ndarray:
        """
        Smooth spectrum data.

        Args:
            power_dbm: Power array in dBm
            window_size: Smoothing window size
            method: 'moving_average', 'gaussian', or 'savgol'

        Returns:
            Smoothed power array
        """
        if method == 'moving_average':
            kernel = np.ones(window_size) / window_size
            return np.convolve(power_dbm, kernel, mode='same')

        elif method == 'gaussian':
            from scipy.ndimage import gaussian_filter1d
            sigma = window_size / 3
            return gaussian_filter1d(power_dbm, sigma)

        elif method == 'savgol':
            if window_size % 2 == 0:
                window_size += 1
            return scipy_signal.savgol_filter(power_dbm, window_size, 2)

        else:
            raise ValueError(f"Unknown smoothing method: {method}")

    def calculate_statistics(
        self,
        frequencies: np.ndarray,
        power_dbm: np.ndarray,
        freq_range: Optional[Tuple[float, float]] = None
    ) -> SpectrumStatistics:
        """
        Calculate statistics for a spectrum.

        Args:
            frequencies: Frequency array in Hz
            power_dbm: Power array in dBm
            freq_range: Optional (start, stop) frequency range

        Returns:
            SpectrumStatistics object
        """
        if freq_range:
            mask = (frequencies >= freq_range[0]) & (frequencies <= freq_range[1])
            freqs = frequencies[mask]
            power = power_dbm[mask]
        else:
            freqs = frequencies
            power = power_dbm

        if len(power) == 0:
            return SpectrumStatistics(
                min_power=0, max_power=0, mean_power=0, median_power=0,
                std_power=0, noise_floor=0, dynamic_range=0, num_points=0,
                freq_start=0, freq_stop=0
            )

        noise_floor = self.estimate_noise_floor(power)

        return SpectrumStatistics(
            min_power=float(np.min(power)),
            max_power=float(np.max(power)),
            mean_power=float(np.mean(power)),
            median_power=float(np.median(power)),
            std_power=float(np.std(power)),
            noise_floor=noise_floor,
            dynamic_range=float(np.max(power) - np.min(power)),
            num_points=len(power),
            freq_start=float(freqs[0]) if len(freqs) > 0 else 0,
            freq_stop=float(freqs[-1]) if len(freqs) > 0 else 0
        )

    def classify_signal(
        self,
        frequencies: np.ndarray,
        power_dbm: np.ndarray,
        center_freq: float,
        bandwidth: float
    ) -> Dict[str, Any]:
        """
        Attempt to classify a signal based on spectral characteristics.

        Args:
            frequencies: Frequency array
            power_dbm: Power array
            center_freq: Signal center frequency
            bandwidth: Signal bandwidth

        Returns:
            Dictionary with classification results
        """
        # Extract signal region
        mask = (frequencies >= center_freq - bandwidth) & \
               (frequencies <= center_freq + bandwidth)
        signal_power = power_dbm[mask]
        signal_freqs = frequencies[mask]

        if len(signal_power) < 3:
            return {'type': 'unknown', 'confidence': 0}

        # Calculate features
        peak_idx = np.argmax(signal_power)
        peak_power = signal_power[peak_idx]

        # Power variance (FM has more variance than carrier)
        power_variance = np.var(signal_power)

        # Flatness (digital signals are flatter)
        power_range = np.max(signal_power) - np.min(signal_power)

        # Symmetry around peak
        left_mean = np.mean(signal_power[:peak_idx]) if peak_idx > 0 else 0
        right_mean = np.mean(signal_power[peak_idx:]) if peak_idx < len(signal_power) else 0
        symmetry = 1 - abs(left_mean - right_mean) / max(abs(left_mean), abs(right_mean), 1)

        # Classification logic
        if bandwidth < 10000:
            signal_type = 'carrier'
            confidence = 0.8
        elif bandwidth < 20000:
            signal_type = 'narrowband'
            confidence = 0.6
        elif bandwidth > 1e6 and power_range < 10:
            signal_type = 'wideband_digital'
            confidence = 0.7
        elif 100e3 < bandwidth < 300e3 and power_variance > 5:
            signal_type = 'fm_broadcast'
            confidence = 0.75
        elif bandwidth > 5e6:
            signal_type = 'spread_spectrum'
            confidence = 0.5
        else:
            signal_type = 'unknown'
            confidence = 0.3

        return {
            'type': signal_type,
            'confidence': confidence,
            'bandwidth': bandwidth,
            'power_variance': power_variance,
            'power_range': power_range,
            'symmetry': symmetry
        }

    def find_occupied_bands(
        self,
        frequencies: np.ndarray,
        power_dbm: np.ndarray,
        threshold_db: Optional[float] = None
    ) -> List[Tuple[float, float, float]]:
        """
        Find frequency bands with activity above threshold.

        Args:
            frequencies: Frequency array
            power_dbm: Power array
            threshold_db: Threshold above noise floor

        Returns:
            List of (start_freq, stop_freq, avg_power) tuples
        """
        threshold_db = threshold_db or self.peak_threshold_db
        noise_floor = self.estimate_noise_floor(power_dbm)
        threshold = noise_floor + threshold_db

        # Find regions above threshold
        above_threshold = power_dbm > threshold

        bands = []
        in_band = False
        band_start = 0
        band_power = []

        for i, above in enumerate(above_threshold):
            if above and not in_band:
                in_band = True
                band_start = i
                band_power = [power_dbm[i]]
            elif above and in_band:
                band_power.append(power_dbm[i])
            elif not above and in_band:
                in_band = False
                bands.append((
                    frequencies[band_start],
                    frequencies[i-1],
                    np.mean(band_power)
                ))
                band_power = []

        # Handle band at end
        if in_band:
            bands.append((
                frequencies[band_start],
                frequencies[-1],
                np.mean(band_power)
            ))

        return bands

    def interpolate_spectrum(
        self,
        frequencies: np.ndarray,
        power_dbm: np.ndarray,
        target_resolution: float
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Interpolate spectrum to higher resolution.

        Args:
            frequencies: Original frequency array
            power_dbm: Original power array
            target_resolution: Target frequency resolution in Hz

        Returns:
            Tuple of (new_frequencies, new_power)
        """
        from scipy.interpolate import interp1d

        if len(frequencies) < 2:
            return frequencies, power_dbm

        current_resolution = (frequencies[-1] - frequencies[0]) / (len(frequencies) - 1)
        if target_resolution >= current_resolution:
            return frequencies, power_dbm

        # Create interpolation function
        f = interp1d(frequencies, power_dbm, kind='cubic', fill_value='extrapolate')

        # Generate new frequency array
        num_points = int((frequencies[-1] - frequencies[0]) / target_resolution) + 1
        new_frequencies = np.linspace(frequencies[0], frequencies[-1], num_points)
        new_power = f(new_frequencies)

        return new_frequencies, new_power

    def compare_spectra(
        self,
        freq1: np.ndarray,
        power1: np.ndarray,
        freq2: np.ndarray,
        power2: np.ndarray
    ) -> Dict[str, Any]:
        """
        Compare two spectrum measurements.

        Useful for detecting changes between survey runs.

        Args:
            freq1, power1: First spectrum
            freq2, power2: Second spectrum

        Returns:
            Dictionary with comparison results
        """
        # Align frequency ranges
        freq_min = max(freq1[0], freq2[0])
        freq_max = min(freq1[-1], freq2[-1])

        mask1 = (freq1 >= freq_min) & (freq1 <= freq_max)
        mask2 = (freq2 >= freq_min) & (freq2 <= freq_max)

        p1 = power1[mask1]
        p2 = power2[mask2]

        # Interpolate to same length if needed
        if len(p1) != len(p2):
            from scipy.interpolate import interp1d
            f1 = interp1d(freq1[mask1], p1)
            f2 = interp1d(freq2[mask2], p2)
            common_freq = np.linspace(freq_min, freq_max, min(len(p1), len(p2)))
            p1 = f1(common_freq)
            p2 = f2(common_freq)

        # Calculate difference metrics
        diff = p2 - p1
        correlation = np.corrcoef(p1, p2)[0, 1] if len(p1) > 1 else 0

        return {
            'mean_difference': float(np.mean(diff)),
            'max_difference': float(np.max(np.abs(diff))),
            'std_difference': float(np.std(diff)),
            'correlation': float(correlation),
            'freq_range': (freq_min, freq_max),
            'num_points': len(p1)
        }
