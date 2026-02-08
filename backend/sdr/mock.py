"""
Mock SDR Device Implementation

This module provides a simulated SDR device for testing and development
without requiring actual hardware. It generates realistic RF spectrum data
with configurable signals.
"""

from typing import Optional, List
import numpy as np
from dataclasses import dataclass, field
from loguru import logger

from .base import (
    SDRDevice, DeviceType, DeviceInfo,
    DeviceConnectionError
)


@dataclass
class MockSignal:
    """Configuration for a simulated RF signal"""
    frequency: float            # Center frequency in Hz
    power_dbm: float            # Signal power in dBm
    bandwidth: float = 200e3    # Signal bandwidth in Hz
    modulation: str = 'fm'      # Signal type: 'fm', 'am', 'carrier', 'noise'
    active: bool = True         # Whether signal is currently active


@dataclass
class MockScenario:
    """A collection of signals representing a realistic RF environment"""
    name: str
    signals: List[MockSignal] = field(default_factory=list)
    noise_floor_dbm: float = -100.0


# Predefined scenarios for common RF environments
SCENARIOS = {
    'fm_broadcast': MockScenario(
        name="FM Broadcast Band",
        noise_floor_dbm=-95,
        signals=[
            MockSignal(frequency=88.1e6, power_dbm=-40, bandwidth=200e3, modulation='fm'),
            MockSignal(frequency=91.5e6, power_dbm=-35, bandwidth=200e3, modulation='fm'),
            MockSignal(frequency=93.3e6, power_dbm=-45, bandwidth=200e3, modulation='fm'),
            MockSignal(frequency=95.7e6, power_dbm=-38, bandwidth=200e3, modulation='fm'),
            MockSignal(frequency=98.1e6, power_dbm=-42, bandwidth=200e3, modulation='fm'),
            MockSignal(frequency=101.1e6, power_dbm=-30, bandwidth=200e3, modulation='fm'),
            MockSignal(frequency=104.3e6, power_dbm=-48, bandwidth=200e3, modulation='fm'),
            MockSignal(frequency=107.5e6, power_dbm=-44, bandwidth=200e3, modulation='fm'),
        ]
    ),
    'ism_433': MockScenario(
        name="433 MHz ISM Band",
        noise_floor_dbm=-100,
        signals=[
            MockSignal(frequency=433.05e6, power_dbm=-55, bandwidth=10e3, modulation='carrier'),
            MockSignal(frequency=433.42e6, power_dbm=-60, bandwidth=20e3, modulation='fm'),
            MockSignal(frequency=433.92e6, power_dbm=-50, bandwidth=50e3, modulation='fm'),
        ]
    ),
    'cellular_lte': MockScenario(
        name="LTE Cellular Band",
        noise_floor_dbm=-95,
        signals=[
            MockSignal(frequency=806e6, power_dbm=-45, bandwidth=10e6, modulation='noise'),
            MockSignal(frequency=850e6, power_dbm=-50, bandwidth=5e6, modulation='noise'),
            MockSignal(frequency=1850e6, power_dbm=-55, bandwidth=20e6, modulation='noise'),
        ]
    ),
    'wifi_2.4ghz': MockScenario(
        name="2.4 GHz WiFi",
        noise_floor_dbm=-90,
        signals=[
            MockSignal(frequency=2412e6, power_dbm=-45, bandwidth=22e6, modulation='noise'),
            MockSignal(frequency=2437e6, power_dbm=-50, bandwidth=22e6, modulation='noise'),
            MockSignal(frequency=2462e6, power_dbm=-55, bandwidth=22e6, modulation='noise'),
        ]
    ),
    'empty': MockScenario(
        name="Empty Spectrum",
        noise_floor_dbm=-100,
        signals=[]
    ),
}


class MockSDRDevice(SDRDevice):
    """
    Mock SDR device for testing without hardware.

    Generates realistic RF spectrum data with configurable signals,
    noise, and other characteristics. Useful for:
    - Development and testing without SDR hardware
    - Demonstrating the system
    - Unit testing
    - Training and documentation
    """

    # Simulated device parameters
    MIN_FREQ = 1e6       # 1 MHz
    MAX_FREQ = 6000e6    # 6 GHz
    SUPPORTED_SAMPLE_RATES = [225e3, 1e6, 2e6, 2.4e6, 3.2e6, 8e6, 10e6, 20e6]

    def __init__(
        self,
        device_id: str = "mock_sdr_0",
        scenario: str = 'fm_broadcast',
        custom_signals: Optional[List[MockSignal]] = None
    ):
        """
        Initialize mock SDR device.

        Args:
            device_id: Identifier for this mock device
            scenario: Name of predefined scenario to use
            custom_signals: Optional list of custom signals to add
        """
        super().__init__(device_id=device_id)
        self._scenario = SCENARIOS.get(scenario, SCENARIOS['fm_broadcast'])
        self._custom_signals = custom_signals or []
        self._noise_floor_dbm = self._scenario.noise_floor_dbm

        logger.info(f"Mock SDR initialized with scenario: {self._scenario.name}")

    @property
    def device_type(self) -> DeviceType:
        return DeviceType.MOCK

    def open(self) -> bool:
        """Simulate opening the device."""
        if self.is_open:
            logger.warning("Mock device already open")
            return True

        self.is_open = True
        logger.info(f"Mock SDR opened: {self.device_id}")
        return True

    def close(self) -> None:
        """Simulate closing the device."""
        self.is_open = False
        logger.info(f"Mock SDR closed: {self.device_id}")

    def set_center_freq(self, freq: float) -> bool:
        """Set center frequency."""
        if not self.is_open:
            raise DeviceConnectionError("Device not open")

        self._center_freq = freq
        logger.debug(f"Mock SDR frequency set to {freq/1e6:.3f} MHz")
        return True

    def set_sample_rate(self, rate: float) -> bool:
        """Set sample rate."""
        if not self.is_open:
            raise DeviceConnectionError("Device not open")

        self._sample_rate = rate
        logger.debug(f"Mock SDR sample rate set to {rate/1e6:.3f} MHz")
        return True

    def set_gain(self, gain: int) -> bool:
        """Set gain (affects simulated signal levels)."""
        if not self.is_open:
            raise DeviceConnectionError("Device not open")

        self._gain = gain
        logger.debug(f"Mock SDR gain set to {gain} dB")
        return True

    def set_noise_floor(self, noise_dbm: float) -> None:
        """Set the simulated noise floor level."""
        self._noise_floor_dbm = noise_dbm

    def add_signal(self, signal: MockSignal) -> None:
        """Add a signal to the simulation."""
        self._custom_signals.append(signal)
        logger.debug(f"Added signal at {signal.frequency/1e6:.3f} MHz")

    def clear_custom_signals(self) -> None:
        """Remove all custom signals."""
        self._custom_signals.clear()

    def set_scenario(self, scenario_name: str) -> bool:
        """
        Switch to a different predefined scenario.

        Args:
            scenario_name: Name of the scenario to use
        """
        if scenario_name in SCENARIOS:
            self._scenario = SCENARIOS[scenario_name]
            self._noise_floor_dbm = self._scenario.noise_floor_dbm
            logger.info(f"Switched to scenario: {scenario_name}")
            return True
        else:
            logger.warning(f"Unknown scenario: {scenario_name}")
            return False

    def read_samples(self, num_samples: int) -> np.ndarray:
        """Generate simulated IQ samples."""
        if not self.is_open:
            raise DeviceConnectionError("Device not open")

        # Time vector
        t = np.arange(num_samples) / self._sample_rate

        # Start with complex Gaussian noise
        noise_power = 10 ** (self._noise_floor_dbm / 10) / 1000  # Convert dBm to watts
        noise_amplitude = np.sqrt(noise_power / 2)  # For complex noise
        samples = noise_amplitude * (
            np.random.randn(num_samples) + 1j * np.random.randn(num_samples)
        )

        # Get all active signals
        all_signals = [s for s in self._scenario.signals if s.active]
        all_signals.extend([s for s in self._custom_signals if s.active])

        # Add each signal
        for signal in all_signals:
            # Check if signal is within our bandwidth
            freq_offset = signal.frequency - self._center_freq
            if abs(freq_offset) > self._sample_rate / 2 + signal.bandwidth / 2:
                continue  # Signal outside our window

            # Signal amplitude
            signal_power = 10 ** (signal.power_dbm / 10) / 1000  # Watts
            amplitude = np.sqrt(signal_power)

            # Generate signal based on modulation type
            if signal.modulation == 'carrier':
                # Pure carrier (CW)
                sig = amplitude * np.exp(1j * 2 * np.pi * freq_offset * t)

            elif signal.modulation == 'fm':
                # FM modulated signal with random modulation
                mod_freq = 1000 + np.random.rand() * 4000  # 1-5 kHz modulation
                deviation = signal.bandwidth / 4
                phase = 2 * np.pi * freq_offset * t + \
                        (deviation / mod_freq) * np.sin(2 * np.pi * mod_freq * t)
                sig = amplitude * np.exp(1j * phase)

            elif signal.modulation == 'am':
                # AM modulated signal
                mod_freq = 500 + np.random.rand() * 2000
                mod_index = 0.5 + np.random.rand() * 0.3
                carrier = amplitude * np.exp(1j * 2 * np.pi * freq_offset * t)
                modulation = 1 + mod_index * np.sin(2 * np.pi * mod_freq * t)
                sig = carrier * modulation

            elif signal.modulation == 'noise':
                # Wideband noise-like signal (e.g., digital modulation)
                bandwidth_samples = int(signal.bandwidth / self._sample_rate * num_samples)
                bandwidth_samples = max(bandwidth_samples, 1)

                # Generate band-limited noise
                noise_sig = np.random.randn(num_samples) + 1j * np.random.randn(num_samples)
                noise_sig = noise_sig * amplitude

                # Shift to signal frequency
                sig = noise_sig * np.exp(1j * 2 * np.pi * freq_offset * t)

            else:
                # Default: carrier
                sig = amplitude * np.exp(1j * 2 * np.pi * freq_offset * t)

            # Add some random phase offset
            sig = sig * np.exp(1j * np.random.uniform(0, 2 * np.pi))

            # Add to samples
            samples = samples + sig

        # Add some time-varying effects (fading)
        fading = 1 + 0.1 * np.sin(2 * np.pi * 0.5 * t)
        samples = samples * fading

        # Apply gain effect (simple scaling)
        gain_linear = 10 ** (self._gain / 20)
        samples = samples * gain_linear

        return samples.astype(np.complex64)

    def get_device_info(self) -> DeviceInfo:
        """Get device information."""
        return DeviceInfo(
            device_type=DeviceType.MOCK,
            serial_number=self.device_id,
            name=f"Mock SDR ({self._scenario.name})",
            min_freq=self.MIN_FREQ,
            max_freq=self.MAX_FREQ,
            min_sample_rate=min(self.SUPPORTED_SAMPLE_RATES),
            max_sample_rate=max(self.SUPPORTED_SAMPLE_RATES),
            supported_gains=list(range(0, 51, 10))
        )

    def get_supported_sample_rates(self) -> List[float]:
        """Get list of supported sample rates."""
        return self.SUPPORTED_SAMPLE_RATES.copy()

    @staticmethod
    def detect_devices() -> List[dict]:
        """
        Return list of available mock devices.

        Returns one mock device per scenario (excluding 'empty'),
        allowing multi-device testing without hardware.
        """
        devices = []
        for key, scenario in SCENARIOS.items():
            if key == 'empty':
                continue
            devices.append({
                'type': 'mock',
                'device_id': f'mock_{key}',
                'name': f'Mock SDR - {scenario.name}',
                'scenario': key,
            })
        return devices

    @staticmethod
    def get_available_scenarios() -> List[str]:
        """Get list of available scenario names."""
        return list(SCENARIOS.keys())
