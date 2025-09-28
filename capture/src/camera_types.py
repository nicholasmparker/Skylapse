"""Camera system type definitions and enums."""

import json
from dataclasses import asdict, dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, List, Optional


class CameraCapability(Enum):
    """Supported camera capabilities for feature detection."""

    AUTOFOCUS = auto()
    MANUAL_FOCUS = auto()
    HDR_BRACKETING = auto()
    FOCUS_STACKING = auto()
    RAW_CAPTURE = auto()
    LIVE_PREVIEW = auto()


@dataclass
class CaptureSettings:
    """Camera capture settings configuration."""

    # Exposure settings
    exposure_time_us: Optional[int] = None
    iso: Optional[int] = None
    exposure_compensation: float = 0.0

    # Focus settings
    focus_distance_mm: Optional[float] = None
    autofocus_enabled: bool = True

    # White balance
    white_balance_k: Optional[int] = None
    white_balance_mode: str = "auto"

    # Image quality
    quality: int = 95
    format: str = "JPEG"

    # Image orientation
    rotation_degrees: int = 0  # 0, 90, 180, 270 degrees

    # HDR bracketing
    hdr_bracket_stops: List[float] = field(default_factory=list)

    # Processing hints
    processing_hints: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CaptureResult:
    """Result of a camera capture operation."""

    file_paths: List[str]
    metadata: Dict[str, Any]
    actual_settings: CaptureSettings
    capture_time_ms: float
    quality_score: Optional[float] = None

    @property
    def primary_image_path(self) -> str:
        """Return the primary image path (first in the list)."""
        return self.file_paths[0] if self.file_paths else ""

    @property
    def is_sequence(self) -> bool:
        """Check if this is a multi-image sequence."""
        return len(self.file_paths) > 1


@dataclass
class CameraSpecs:
    """Camera hardware specifications."""

    model: str
    resolution_mp: float
    max_resolution: tuple[int, int]
    sensor_size_mm: tuple[float, float]
    focal_length_mm: float

    # Performance characteristics
    base_iso: int
    max_iso: int
    iso_invariance_point: int
    max_exposure_us: int

    # Focus capabilities
    focus_range_mm: tuple[float, float]
    hyperfocal_distance_mm: float

    # Supported capabilities
    capabilities: List[CameraCapability]


@dataclass
class EnvironmentalConditions:
    """Current environmental conditions for adaptive control."""

    # Weather data
    cloud_cover_pct: Optional[float] = None
    visibility_km: Optional[float] = None
    precipitation_prob_pct: Optional[float] = None
    wind_speed_kph: Optional[float] = None

    # Astronomical data
    sun_elevation_deg: Optional[float] = None
    sun_azimuth_deg: Optional[float] = None
    is_golden_hour: bool = False
    is_blue_hour: bool = False

    # Sensor data
    ambient_light_lux: Optional[float] = None
    color_temperature_k: Optional[int] = None
    temperature_c: Optional[float] = None

    # Scene analysis
    scene_brightness: Optional[float] = None
    focus_quality_score: Optional[float] = None


class CameraError(Exception):
    """Base exception for camera-related errors."""

    pass


class CameraInitializationError(CameraError):
    """Raised when camera initialization fails."""

    pass


class CaptureError(CameraError):
    """Raised when image capture fails."""

    pass


class FocusError(CameraError):
    """Raised when autofocus fails."""

    pass


class SkylapsJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for Skylapse dataclasses and types."""

    def default(self, obj):
        """Convert Skylapse objects to JSON-serializable format."""
        # Handle dataclasses
        if hasattr(obj, "__dataclass_fields__"):
            return asdict(obj)

        # Handle enums
        if isinstance(obj, Enum):
            return obj.value

        # Handle Path objects
        if isinstance(obj, Path):
            return str(obj)

        # Let the base class handle other types
        return super().default(obj)


def to_json(obj: Any, **kwargs) -> str:
    """Convert object to JSON string using Skylapse encoder."""
    return json.dumps(obj, cls=SkylapsJSONEncoder, **kwargs)


def to_dict(obj: Any) -> Dict[str, Any]:
    """Convert object to dictionary using Skylapse encoder logic."""
    if hasattr(obj, "__dataclass_fields__"):
        return asdict(obj)
    elif isinstance(obj, Enum):
        return obj.value
    elif isinstance(obj, Path):
        return str(obj)
    elif isinstance(obj, dict):
        return {k: to_dict(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [to_dict(item) for item in obj]
    else:
        return obj
