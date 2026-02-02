"""
GPS Handler

This module provides GPS/location services for the RF Spectrum Monitor.
Supports manual location entry, GPSD integration, and mock GPS for testing.
"""

from dataclasses import dataclass, field
from typing import Optional, Tuple, List, Callable
from enum import Enum
import time
import threading
import math
from loguru import logger

from .config import settings


class GPSMode(Enum):
    """GPS operation modes"""
    MANUAL = "manual"
    GPSD = "gpsd"
    MOCK = "mock"


@dataclass
class GPSLocation:
    """GPS location data"""
    latitude: float
    longitude: float
    altitude: Optional[float] = None
    accuracy: Optional[float] = None  # Horizontal accuracy in meters
    speed: Optional[float] = None     # Speed in m/s
    heading: Optional[float] = None   # Heading in degrees
    timestamp: float = field(default_factory=time.time)
    fix_quality: int = 0              # 0=no fix, 1=GPS, 2=DGPS, etc.

    def __post_init__(self):
        """Validate coordinates"""
        if not -90 <= self.latitude <= 90:
            raise ValueError(f"Latitude must be between -90 and 90: {self.latitude}")
        if not -180 <= self.longitude <= 180:
            raise ValueError(f"Longitude must be between -180 and 180: {self.longitude}")

    def distance_to(self, other: 'GPSLocation') -> float:
        """
        Calculate distance to another location using Haversine formula.

        Args:
            other: Another GPS location

        Returns:
            Distance in meters
        """
        R = 6371000  # Earth's radius in meters

        lat1 = math.radians(self.latitude)
        lat2 = math.radians(other.latitude)
        dlat = math.radians(other.latitude - self.latitude)
        dlon = math.radians(other.longitude - self.longitude)

        a = (math.sin(dlat/2)**2 +
             math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

        return R * c

    def bearing_to(self, other: 'GPSLocation') -> float:
        """
        Calculate bearing to another location.

        Args:
            other: Another GPS location

        Returns:
            Bearing in degrees (0-360)
        """
        lat1 = math.radians(self.latitude)
        lat2 = math.radians(other.latitude)
        dlon = math.radians(other.longitude - self.longitude)

        x = math.sin(dlon) * math.cos(lat2)
        y = (math.cos(lat1) * math.sin(lat2) -
             math.sin(lat1) * math.cos(lat2) * math.cos(dlon))

        bearing = math.degrees(math.atan2(x, y))
        return (bearing + 360) % 360

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'latitude': self.latitude,
            'longitude': self.longitude,
            'altitude': self.altitude,
            'accuracy': self.accuracy,
            'speed': self.speed,
            'heading': self.heading,
            'timestamp': self.timestamp,
            'fix_quality': self.fix_quality
        }


class GPSHandler:
    """
    Handles GPS location services.

    Supports three modes:
    - MANUAL: User enters coordinates manually
    - GPSD: Uses GPSD daemon for real GPS
    - MOCK: Simulates GPS movement for testing
    """

    def __init__(self, mode: Optional[GPSMode] = None):
        """
        Initialize GPS handler.

        Args:
            mode: GPS mode (uses settings if not specified)
        """
        mode_str = mode.value if mode else settings.gps.mode
        self.mode = GPSMode(mode_str)

        self._current_location: Optional[GPSLocation] = None
        self._gpsd_session = None
        self._is_running = False
        self._update_thread: Optional[threading.Thread] = None
        self._callbacks: List[Callable[[GPSLocation], None]] = []
        self._lock = threading.Lock()

        # Mock GPS settings
        self._mock_route: List[Tuple[float, float]] = []
        self._mock_index = 0
        self._mock_speed = 1.0  # meters per second

        logger.info(f"GPS handler initialized in {self.mode.value} mode")

    @property
    def current_location(self) -> Optional[GPSLocation]:
        """Get current location"""
        with self._lock:
            return self._current_location

    @property
    def is_available(self) -> bool:
        """Check if GPS is available"""
        if self.mode == GPSMode.MANUAL:
            return self._current_location is not None
        elif self.mode == GPSMode.GPSD:
            return self._gpsd_session is not None and self._is_running
        elif self.mode == GPSMode.MOCK:
            return True
        return False

    def start(self) -> bool:
        """
        Start GPS updates.

        For GPSD mode, connects to the daemon.
        For MOCK mode, starts simulated movement.

        Returns:
            True if started successfully
        """
        if self._is_running:
            return True

        if self.mode == GPSMode.GPSD:
            return self._start_gpsd()
        elif self.mode == GPSMode.MOCK:
            return self._start_mock()
        elif self.mode == GPSMode.MANUAL:
            self._is_running = True
            return True

        return False

    def stop(self) -> None:
        """Stop GPS updates"""
        self._is_running = False

        if self._update_thread and self._update_thread.is_alive():
            self._update_thread.join(timeout=2.0)

        if self._gpsd_session:
            try:
                self._gpsd_session = None
            except Exception as e:
                logger.warning(f"Error closing GPSD: {e}")

        logger.info("GPS handler stopped")

    def set_location(self, latitude: float, longitude: float,
                    altitude: Optional[float] = None,
                    accuracy: Optional[float] = None) -> GPSLocation:
        """
        Set location manually.

        Args:
            latitude: Latitude in degrees
            longitude: Longitude in degrees
            altitude: Altitude in meters (optional)
            accuracy: Accuracy in meters (optional)

        Returns:
            The new location
        """
        location = GPSLocation(
            latitude=latitude,
            longitude=longitude,
            altitude=altitude,
            accuracy=accuracy,
            fix_quality=1  # Manual entry
        )

        with self._lock:
            self._current_location = location

        self._notify_callbacks(location)
        logger.debug(f"Location set: {latitude:.6f}, {longitude:.6f}")
        return location

    def get_location(self) -> Optional[GPSLocation]:
        """
        Get current GPS location.

        For MANUAL mode, returns the last set location.
        For GPSD mode, returns the latest GPS reading.
        For MOCK mode, returns the simulated location.

        Returns:
            Current location or None if unavailable
        """
        if self.mode == GPSMode.MANUAL:
            return self._current_location
        elif self.mode == GPSMode.GPSD:
            return self._get_gpsd_location()
        elif self.mode == GPSMode.MOCK:
            return self._get_mock_location()
        return None

    def add_callback(self, callback: Callable[[GPSLocation], None]) -> None:
        """Add a callback for location updates"""
        self._callbacks.append(callback)

    def remove_callback(self, callback: Callable[[GPSLocation], None]) -> None:
        """Remove a location update callback"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def _notify_callbacks(self, location: GPSLocation) -> None:
        """Notify all callbacks of a location update"""
        for callback in self._callbacks:
            try:
                callback(location)
            except Exception as e:
                logger.error(f"GPS callback error: {e}")

    # GPSD implementation
    def _start_gpsd(self) -> bool:
        """Start GPSD connection"""
        try:
            import gpsd
            gpsd.connect(
                host=settings.gps.gpsd_host,
                port=settings.gps.gpsd_port
            )
            self._gpsd_session = gpsd
            self._is_running = True

            # Start update thread
            self._update_thread = threading.Thread(
                target=self._gpsd_update_loop,
                daemon=True
            )
            self._update_thread.start()

            logger.info(f"Connected to GPSD at {settings.gps.gpsd_host}:{settings.gps.gpsd_port}")
            return True

        except ImportError:
            logger.error("gpsd-py3 library not installed")
            return False
        except Exception as e:
            logger.error(f"Failed to connect to GPSD: {e}")
            return False

    def _gpsd_update_loop(self) -> None:
        """Background thread for GPSD updates"""
        while self._is_running:
            try:
                location = self._get_gpsd_location()
                if location:
                    with self._lock:
                        self._current_location = location
                    self._notify_callbacks(location)
                time.sleep(1.0)  # Update every second
            except Exception as e:
                logger.error(f"GPSD update error: {e}")
                time.sleep(5.0)

    def _get_gpsd_location(self) -> Optional[GPSLocation]:
        """Get current location from GPSD"""
        if not self._gpsd_session:
            return None

        try:
            packet = self._gpsd_session.get_current()

            if packet.mode >= 2:  # 2D or 3D fix
                return GPSLocation(
                    latitude=packet.lat,
                    longitude=packet.lon,
                    altitude=packet.alt if packet.mode >= 3 else None,
                    speed=packet.hspeed if hasattr(packet, 'hspeed') else None,
                    heading=packet.track if hasattr(packet, 'track') else None,
                    accuracy=packet.error.get('x', None) if hasattr(packet, 'error') else None,
                    fix_quality=packet.mode
                )
        except Exception as e:
            logger.debug(f"GPSD read error: {e}")

        return None

    # Mock GPS implementation
    def _start_mock(self) -> bool:
        """Start mock GPS"""
        self._is_running = True

        # Set default location if no route defined
        if not self._mock_route:
            self._current_location = GPSLocation(
                latitude=settings.gps.mock_default_lat,
                longitude=settings.gps.mock_default_lon,
                altitude=100.0,
                accuracy=5.0,
                fix_quality=1
            )

        # Start update thread
        self._update_thread = threading.Thread(
            target=self._mock_update_loop,
            daemon=True
        )
        self._update_thread.start()

        logger.info("Mock GPS started")
        return True

    def _mock_update_loop(self) -> None:
        """Background thread for mock GPS updates"""
        while self._is_running:
            location = self._get_mock_location()
            if location:
                with self._lock:
                    self._current_location = location
                self._notify_callbacks(location)
            time.sleep(1.0)

    def _get_mock_location(self) -> GPSLocation:
        """Get simulated GPS location"""
        if self._mock_route and len(self._mock_route) > 1:
            # Interpolate along route
            idx = self._mock_index % len(self._mock_route)
            next_idx = (idx + 1) % len(self._mock_route)

            lat1, lon1 = self._mock_route[idx]
            lat2, lon2 = self._mock_route[next_idx]

            # Simple linear interpolation
            t = (time.time() % 10) / 10  # 10 second segments
            lat = lat1 + (lat2 - lat1) * t
            lon = lon1 + (lon2 - lon1) * t

            return GPSLocation(
                latitude=lat,
                longitude=lon,
                altitude=100.0,
                accuracy=3.0,
                speed=self._mock_speed,
                fix_quality=1
            )
        elif self._current_location:
            # Add small random movement
            import random
            return GPSLocation(
                latitude=self._current_location.latitude + random.gauss(0, 0.00001),
                longitude=self._current_location.longitude + random.gauss(0, 0.00001),
                altitude=self._current_location.altitude,
                accuracy=5.0,
                speed=0.5,
                fix_quality=1
            )
        else:
            return GPSLocation(
                latitude=settings.gps.mock_default_lat,
                longitude=settings.gps.mock_default_lon,
                altitude=100.0,
                accuracy=5.0,
                fix_quality=1
            )

    def set_mock_route(self, waypoints: List[Tuple[float, float]],
                      speed: float = 1.0) -> None:
        """
        Set a route for mock GPS to follow.

        Args:
            waypoints: List of (latitude, longitude) tuples
            speed: Movement speed in m/s
        """
        self._mock_route = waypoints
        self._mock_index = 0
        self._mock_speed = speed
        logger.info(f"Mock GPS route set: {len(waypoints)} waypoints")

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


def calculate_grid_points(
    center_lat: float,
    center_lon: float,
    radius_m: float,
    spacing_m: float
) -> List[Tuple[float, float]]:
    """
    Calculate a grid of GPS points around a center location.

    Useful for generating survey waypoints.

    Args:
        center_lat: Center latitude
        center_lon: Center longitude
        radius_m: Radius in meters
        spacing_m: Grid spacing in meters

    Returns:
        List of (latitude, longitude) tuples
    """
    # Approximate degrees per meter at this latitude
    lat_deg_per_m = 1 / 111320
    lon_deg_per_m = 1 / (111320 * math.cos(math.radians(center_lat)))

    radius_lat = radius_m * lat_deg_per_m
    radius_lon = radius_m * lon_deg_per_m
    spacing_lat = spacing_m * lat_deg_per_m
    spacing_lon = spacing_m * lon_deg_per_m

    points = []
    lat = center_lat - radius_lat
    while lat <= center_lat + radius_lat:
        lon = center_lon - radius_lon
        while lon <= center_lon + radius_lon:
            # Check if point is within radius
            dist = math.sqrt(
                ((lat - center_lat) / lat_deg_per_m) ** 2 +
                ((lon - center_lon) / lon_deg_per_m) ** 2
            )
            if dist <= radius_m:
                points.append((lat, lon))
            lon += spacing_lon
        lat += spacing_lat

    return points


def format_coordinates(lat: float, lon: float, format_type: str = 'dms') -> str:
    """
    Format coordinates for display.

    Args:
        lat: Latitude
        lon: Longitude
        format_type: 'dms' (degrees/minutes/seconds), 'dm' (degrees/minutes), 'dd' (decimal degrees)

    Returns:
        Formatted coordinate string
    """
    def dd_to_dms(dd: float) -> Tuple[int, int, float]:
        d = int(dd)
        m = int((dd - d) * 60)
        s = (dd - d - m/60) * 3600
        return abs(d), abs(m), abs(s)

    if format_type == 'dd':
        return f"{lat:.6f}, {lon:.6f}"

    elif format_type == 'dm':
        lat_d, lat_m, _ = dd_to_dms(lat)
        lon_d, lon_m, _ = dd_to_dms(lon)
        lat_dir = 'N' if lat >= 0 else 'S'
        lon_dir = 'E' if lon >= 0 else 'W'
        return f"{lat_d}° {lat_m:.3f}' {lat_dir}, {lon_d}° {lon_m:.3f}' {lon_dir}"

    else:  # dms
        lat_d, lat_m, lat_s = dd_to_dms(lat)
        lon_d, lon_m, lon_s = dd_to_dms(lon)
        lat_dir = 'N' if lat >= 0 else 'S'
        lon_dir = 'E' if lon >= 0 else 'W'
        return f"{lat_d}° {lat_m}' {lat_s:.2f}\" {lat_dir}, {lon_d}° {lon_m}' {lon_s:.2f}\" {lon_dir}"
