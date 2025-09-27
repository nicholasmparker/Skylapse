# Camera System Design

## Overview

The camera system uses a clean abstraction layer that supports multiple camera types while preserving hardware-specific optimizations. This design enables easy camera swapping and future multi-camera support without compromising performance.

---

## Core Design Principles

### 1. Hardware Abstraction with Performance Preservation
**Problem**: Different cameras have vastly different capabilities and interfaces
**Solution**: Factory pattern with capability discovery and hardware-specific optimizations

### 2. Adaptive Intelligence
**Problem**: Mountain lighting conditions change dramatically throughout the day and seasons
**Solution**: Environmental sensing with learning-based optimization

### 3. Configuration-Driven Behavior
**Problem**: Camera-specific technical parameters shouldn't be hardcoded
**Solution**: YAML-based configuration system with runtime validation

---

## Camera Interface Architecture

### Factory Pattern Implementation

```python
# Simple usage - works with any supported camera
camera = await CameraFactory.auto_detect_camera()

# Feature-driven behavior
if camera.supports_capability(CameraCapability.HDR_BRACKETING):
    results = await camera.capture_sequence([
        CaptureSettings(exposure_time_us=1000),   # -2 EV
        CaptureSettings(exposure_time_us=4000),   # Base
        CaptureSettings(exposure_time_us=16000),  # +2 EV
    ])
```

### Capability Discovery System

**Supported Capabilities:**
- `AUTOFOCUS` - Automatic focus adjustment
- `MANUAL_FOCUS` - Precise focus control
- `HDR_BRACKETING` - Multiple exposure capture
- `FOCUS_STACKING` - Multiple focus point capture
- `RAW_CAPTURE` - Unprocessed sensor data
- `LIVE_PREVIEW` - Real-time image stream

**Example Usage:**
```python
# Adapt behavior based on camera capabilities
if camera.supports_capability(CameraCapability.FOCUS_STACKING):
    settings_list = create_focus_stack_sequence(scene_depth)
    results = await camera.capture_sequence(settings_list)
else:
    # Fallback to single optimal focus point
    settings = optimize_single_focus(scene_depth)
    result = await camera.capture_single(settings)
```

---

## Adaptive Camera Control

### Environmental Intelligence System

**Input Sources:**
- **Weather APIs**: Cloud cover, visibility, precipitation probability
- **Astronomical Data**: Sun position, golden hour timing, season
- **Real-time Sensors**: Ambient light, color temperature, atmospheric conditions
- **Image Analysis**: Focus quality, exposure accuracy, noise levels

### Optimization Strategies

#### Lighting Condition Adaptation
```python
# Golden Hour (sun elevation -6° to +6°)
if scene_classifier.is_golden_hour():
    settings.white_balance_k = min(measured_temp, 3200)  # Preserve warmth
    settings.exposure_compensation = +0.3  # Lift shadows
    if camera.supports_capability(CameraCapability.HDR_BRACKETING):
        settings.hdr_bracket_stops = [-2, -1, 0, +1, +2]

# Blue Hour (sun elevation -12° to -6°)
elif scene_classifier.is_blue_hour():
    settings.white_balance_k = max(measured_temp, 8500)  # Enhance blues
    settings.iso = min(800, camera_specs.iso_invariance_point)
    settings.exposure_time_us = min(2_000_000, camera_specs.max_exposure_us)
```

#### Weather-Aware Adjustments
```python
# Overcast conditions - lift shadows, boost contrast
if weather_data['cloud_cover'] > 70:
    settings.exposure_compensation += 0.7
    settings.contrast_boost = 0.2

# Stormy conditions - preserve highlights, capture drama
if weather_data['precipitation_prob'] > 60:
    settings.exposure_compensation -= 0.3
    settings.capture_interval_seconds = 2  # Faster for clouds
```

### Learning and Feedback System

**Quality Assessment:**
```python
quality_metrics = {
    'sharpness_score': analyze_focus_quality(image),
    'noise_level': measure_signal_to_noise(image),
    'exposure_accuracy': analyze_histogram(image),
    'color_accuracy': measure_color_cast(image),
}

# Store results for future optimization
learning_system.record_result(
    settings=capture_settings,
    conditions=environmental_snapshot,
    quality=quality_metrics
)
```

**Predictive Optimization:**
```python
# Use historical data for similar conditions
similar_conditions = quality_database.find_similar(
    current_conditions, similarity_threshold=0.8
)
if len(similar_conditions) > 10:
    optimal_settings = extract_best_settings(similar_conditions)
    return optimal_settings
```

---

## Technical Configuration System

### Configuration Hierarchy

**Essential Parameters** (Phase 1 implementation):
```yaml
# Bayer pattern and color processing
sensor:
  bayer_pattern: "RGGB"
  color_matrix_daylight: [[1.654, -0.532, -0.122], ...]

# Focus calibration for landscape photography
optical:
  hyperfocal_distance_mm: 1830
  focus_calibration_points:
    - [.inf, 0.0]      # Infinity focus
    - [2000.0, 0.05]   # 2km focus
    - [1000.0, 0.12]   # 1km focus
```

**Quality Parameters** (Phase 2 implementation):
```yaml
# Lens correction and noise optimization
processing:
  demosaic_algorithm: "DCB"          # Better detail preservation
  barrel_distortion_k1: -0.042      # Lens distortion correction
  spatial_nr_strength: 0.2          # Noise reduction tuning
```

### Configuration Loading System
```python
class CameraConfigManager:
    def __init__(self, config_dir: Path = Path("config/cameras")):
        self.configs = self._load_all_configs()

    def get_config_for_camera(self, camera_model: str):
        """Load configuration based on detected camera model"""
        return self.configs.get(camera_model, self._get_default_config())

    def update_config(self, camera_model: str, updates: Dict[str, Any]):
        """Update configuration and save to file"""
        self.configs[camera_model].update(updates)
        self._save_config(camera_model)
```

---

## Supported Camera Types

### Primary: Arducam IMX519
**Specifications:**
- 16MP resolution (4656×3496)
- Autofocus with precise control
- 10-bit ADC with excellent dynamic range
- Native ISO 100, usable to ISO 800

**Optimizations:**
- Calibrated color matrices for mountain lighting
- Focus calibration for landscape distances
- Thermal noise characterization for long exposures

### Alternative: Pi Camera Module v3/v2
**Specifications:**
- 12MP (v3) / 8MP (v2) resolution
- Fixed focus with electronic adjustment
- Good low-light performance

**Optimizations:**
- Different Bayer pattern handling
- Alternative focus strategies
- Color matrix adaptations

### Development: Mock Camera
**Purpose:** Testing and development without hardware
**Features:**
- Simulates all camera capabilities
- Configurable capture delays
- Generated test images with metadata

---

## Multi-Camera Readiness

### Current Single-Camera Design
```python
# Current controller handles one camera
controller = CameraController()
await controller.initialize_camera("arducam_imx519")
result = await controller.capture_optimized(conditions)
```

### Future Multi-Camera Extension
```python
# Future multi-camera controller (minimal changes needed)
controller = MultiCameraController()
await controller.add_camera("primary", "arducam_imx519", position="north")
await controller.add_camera("secondary", "pi_camera_v3", position="south")

# Synchronized capture across all cameras
results = await controller.capture_synchronized(conditions)
```

**Architecture Benefits:**
- Camera abstraction makes multi-camera extension straightforward
- Factory pattern supports heterogeneous camera types
- Configuration system scales to multiple camera configs
- Processing pipeline already handles multiple image inputs

---

## Integration with Processing Pipeline

### Metadata Enrichment
```python
@dataclass
class CaptureResult:
    file_paths: List[str]
    metadata: Dict[str, Any]          # Camera model, settings, conditions
    actual_settings: CaptureSettings  # What was actually applied
    capture_time_ms: float           # Performance monitoring
    quality_score: Optional[float]   # For learning system
```

### Processing Hints
```python
# Camera provides processing hints based on conditions
capture_result.processing_hints = {
    'use_noise_reduction': conditions['low_light'],
    'apply_hdr_processing': len(capture_result.file_paths) > 1,
    'focus_stack_blend': camera.last_capture_was_focus_stack(),
    'lens_corrections_needed': camera.requires_distortion_correction(),
}
```

---

## Performance and Reliability

### Performance Targets
- **Capture Latency**: <50ms (native deployment enables this)
- **Focus Acquisition**: <2s for landscape distances
- **Configuration Load**: <100ms on startup
- **Quality Assessment**: <500ms per image

### Error Handling and Recovery
```python
# Graceful degradation strategies
try:
    camera = await CameraFactory.auto_detect_camera()
except CameraInitializationError:
    # Fall back to mock camera for testing
    camera = await CameraFactory.create_camera("mock_camera")
    logger.warning("Using mock camera - no hardware detected")

# Capability-based fallbacks
if not camera.supports_capability(CameraCapability.AUTOFOCUS):
    # Use manual focus at hyperfocal distance
    settings.focus_distance_mm = camera_config.hyperfocal_distance_mm
```

This camera design provides a robust foundation for high-quality mountain timelapses while remaining flexible for future enhancements and additional camera support.
