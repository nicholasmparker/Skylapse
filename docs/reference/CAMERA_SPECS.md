# Camera Technical Specifications Reference

This document contains detailed technical specifications and configuration parameters for supported cameras.

---

## Arducam IMX519 16MP Autofocus Camera

### Sensor Specifications
```yaml
sensor:
  model: "Sony IMX519"
  resolution: [4656, 3496]           # 16.3 MP
  sensor_size_mm: [7.564, 5.476]     # 1/2.5" format
  pixel_size_um: 1.55
  bayer_pattern: "RGGB"
  bit_depth: 10                      # 10-bit ADC
  quantum_efficiency: 0.82           # 82% peak QE at 525nm
  full_well_capacity: 4700           # electrons per pixel
  read_noise_electrons: 1.6          # Very low read noise
  dark_current_e_per_sec: 0.01       # Excellent dark current
```

### Performance Characteristics
```yaml
performance:
  max_fps: 30.0
  min_exposure_us: 100
  max_exposure_us: 10_000_000        # 10 seconds
  base_iso: 100                      # Native ISO (lowest noise)
  iso_invariance_point: 800          # Good up to ISO 800
  iso_range: [100, 1600]
  gain_map:
    100: 1.0
    200: 2.0
    400: 4.0
    800: 8.0
    1600: 16.0
```

### Optical Configuration
```yaml
optical:
  focal_length_mm: 4.28              # 35mm equiv: ~27mm
  aperture_range: [2.8, 2.8]         # Fixed f/2.8
  focus_range_mm: [100.0, .inf]
  hyperfocal_distance_mm: 1830       # At f/2.8
  infinity_focus_position: 0.0       # Lens position (0.0-1.0)

  # Calibrated focus positions for landscape distances
  focus_calibration_points:
    - [.inf, 0.0]                    # Infinity
    - [5000.0, 0.02]                 # 5km
    - [2000.0, 0.05]                 # 2km
    - [1000.0, 0.12]                 # 1km
    - [500.0, 0.25]                  # 500m
    - [200.0, 0.65]                  # 200m (minimum focus)
```

### Lens Correction Parameters
```yaml
distortion:
  # Barrel distortion coefficients (calibrated)
  barrel_k1: -0.042
  barrel_k2: 0.018
  barrel_k3: -0.003

  # Tangential distortion
  tangential_p1: 0.001
  tangential_p2: -0.002

vignetting:
  # Vignetting correction coefficients
  center: [0.5, 0.5]                 # Optical center
  k1: -0.12
  k2: 0.08
  k3: -0.02

chromatic_aberration:
  # Lateral chromatic aberration (minimal on IMX519)
  red_coefficients: [0.002, -0.001]
  blue_coefficients: [-0.003, 0.002]
```

### Color Processing
```yaml
color:
  # Color correction matrices (3x3) for different illuminants
  color_matrix_daylight:
    - [1.654, -0.532, -0.122]
    - [-0.328, 1.487, -0.159]
    - [-0.098, -0.412, 1.510]

  color_matrix_tungsten:
    - [1.321, -0.234, -0.087]
    - [-0.445, 1.623, -0.178]
    - [-0.123, -0.567, 1.690]

  color_matrix_flash:
    - [1.543, -0.421, -0.122]
    - [-0.367, 1.521, -0.154]
    - [-0.089, -0.387, 1.476]

  # White balance coefficients for different lighting
  wb_daylight: [1.0, 1.0, 1.0]       # Neutral
  wb_tungsten: [0.65, 1.0, 1.8]      # Warm correction
  wb_auto_range: [2500, 8000]        # Auto WB Kelvin range
```

### Processing Pipeline Configuration
```yaml
processing:
  # Demosaicing settings
  demosaic_algorithm: "DCB"          # DCB best for landscape detail
  demosaic_quality: "quality"        # vs "fast" or "balanced"

  # Noise reduction (conservative for landscape detail)
  spatial_nr_strength: 0.2           # 0.0-1.0
  temporal_nr_strength: 0.4          # For multi-frame stacking
  chroma_nr_strength: 0.3            # Color noise reduction

  # Sharpening (subtle for natural look)
  unsharp_mask_amount: 0.4
  unsharp_mask_radius: 1.2
  unsharp_mask_threshold: 3.0

  # Thermal characteristics
  dark_frame_scaling: true           # Enable dark frame subtraction
  thermal_noise_coefficient: 0.001   # Temperature dependency
```

---

## Raspberry Pi Camera Module v3

### Sensor Specifications
```yaml
sensor:
  model: "Sony IMX708"
  resolution: [4608, 2592]           # 11.9 MP (16:9) or [4608, 3456] (4:3)
  sensor_size_mm: [7.4, 5.6]         # 1/2.43" format
  pixel_size_um: 1.4
  bayer_pattern: "BGGR"              # Note: Different from IMX519
  bit_depth: 12                      # 12-bit ADC
  quantum_efficiency: 0.80
  full_well_capacity: 5100
  read_noise_electrons: 2.1
```

### Performance Characteristics
```yaml
performance:
  max_fps: 120                       # At lower resolutions
  min_exposure_us: 50
  max_exposure_us: 16_000_000        # 16 seconds
  base_iso: 100
  iso_invariance_point: 400          # Lower than IMX519
  iso_range: [100, 1600]
```

### Optical Configuration
```yaml
optical:
  focal_length_mm: 2.75              # 35mm equiv: ~15mm (wider)
  aperture_range: [2.8, 2.8]         # Fixed f/2.8
  focus_range_mm: [100.0, .inf]      # Manual focus adjustment
  hyperfocal_distance_mm: 1200       # Shorter due to wider lens
```

### Color Processing
```yaml
color:
  # Different color matrices due to different sensor characteristics
  color_matrix_daylight:
    - [1.601, -0.502, -0.099]
    - [-0.315, 1.456, -0.141]
    - [-0.087, -0.394, 1.481]

  # White balance coefficients
  wb_daylight: [1.0, 1.0, 1.0]
  wb_tungsten: [0.62, 1.0, 1.85]
  wb_auto_range: [2500, 8000]
```

---

## USB Camera (Generic)

### Fallback Specifications
```yaml
sensor:
  model: "Generic USB"
  resolution: [1920, 1080]           # Assume 1080p
  bayer_pattern: "YUYV"              # Most common USB format
  bit_depth: 8                       # Standard for USB cameras
```

### Performance Characteristics
```yaml
performance:
  max_fps: 30
  min_exposure_us: 1000              # Limited control
  max_exposure_us: 100_000           # ~1/10s max
  iso_range: [100, 400]              # Limited range
```

### Processing Configuration
```yaml
processing:
  demosaic_algorithm: "bilinear"     # Faster for lower quality
  spatial_nr_strength: 0.5          # Higher NR for USB cameras
  unsharp_mask_amount: 0.6           # More sharpening needed
```

---

## Mock Camera (Testing)

### Simulated Specifications
```yaml
sensor:
  model: "Mock Camera"
  resolution: [4656, 3496]           # Simulate IMX519
  bayer_pattern: "RGGB"
  all_capabilities: true             # Supports all features
```

### Testing Configuration
```yaml
simulation:
  capture_delay_ms: 50               # Configurable delay
  focus_delay_ms: 1000               # Simulate focus time
  generate_test_patterns: true       # Create test images
  simulate_failures: false           # For error testing
```

---

## Configuration Loading Examples

### Python Configuration Loading
```python
import yaml
from pathlib import Path

def load_camera_config(camera_model: str) -> dict:
    """Load camera configuration from YAML file"""
    config_path = Path(f"config/cameras/{camera_model}.yaml")

    if not config_path.exists():
        raise FileNotFoundError(f"No config for camera: {camera_model}")

    with open(config_path) as f:
        return yaml.safe_load(f)

# Usage
imx519_config = load_camera_config("arducam_imx519")
sensor_specs = imx519_config['sensor']
optical_specs = imx519_config['optical']
```

### Runtime Configuration Updates
```python
def update_camera_config(camera_model: str, section: str, updates: dict):
    """Update camera configuration parameters"""
    config = load_camera_config(camera_model)
    config[section].update(updates)

    # Validate updates
    if section == 'sensor' and 'iso_range' in updates:
        iso_min, iso_max = updates['iso_range']
        if iso_min < 50 or iso_max > 6400:
            raise ValueError("ISO range outside valid limits")

    # Save updated configuration
    config_path = Path(f"config/cameras/{camera_model}.yaml")
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)

# Example: Update noise reduction strength
update_camera_config("arducam_imx519", "processing", {
    "spatial_nr_strength": 0.3
})
```

---

## Calibration Procedures

### Focus Calibration
1. **Setup**: Mount camera with clear view to distant objects (>2km)
2. **Capture Series**: Take images at different lens positions (0.0 to 1.0 in 0.1 steps)
3. **Analysis**: Measure sharpness using contrast detection or MTF analysis
4. **Mapping**: Create distance-to-position mapping for landscape distances

### Color Matrix Calibration
1. **Target Setup**: Use ColorChecker or similar calibrated target
2. **Lighting Conditions**: Capture under daylight, tungsten, and flash
3. **Analysis**: Calculate color transformation matrices using raw RGB values
4. **Validation**: Verify color accuracy with test images

### Lens Distortion Calibration
1. **Pattern Capture**: Photograph checkerboard pattern at various positions
2. **Analysis**: Use OpenCV calibration functions to extract coefficients
3. **Validation**: Apply correction and verify straight lines remain straight

This reference provides the technical foundation for camera-specific optimizations and quality tuning.