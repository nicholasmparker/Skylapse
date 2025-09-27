# QA Recommendations: Development Environment Setup

**Date**: September 26, 2025
**QA Engineer**: Jordan Martinez
**Topic**: Camera Development Environment Best Practices

---

## 🎯 **Current State Analysis**

### **✅ What We Have (Good Foundation)**

1. **Mock Camera Implementation**: Well-designed `MockCamera` class with realistic behavior
2. **Camera Factory Pattern**: Auto-detection system with fallback capabilities
3. **Configuration System**: Proper mock camera configuration in YAML
4. **Test Infrastructure**: Comprehensive test suite with mock camera support

### **❌ What's Missing (Development Gaps)**

1. **Development Mode Configuration**: `mock_camera_enabled: false` in system config
2. **Auto-Detection Priority**: No clear dev vs production camera selection
3. **Development Workflow**: No documented process for local development
4. **Mock Data Quality**: Limited realistic image generation

---

## 🔧 **Recommended Development Environment Setup**

### **1. Development Configuration Override**

Create a development-specific configuration:

```yaml
# config/system/development.yaml
development:
  mock_camera_enabled: true
  debug_logging: true
  development_mode: true

# Override production settings for dev
storage:
  capture_buffer_path: "./dev_buffer"
  max_buffer_size_gb: 1  # Smaller for dev

monitoring:
  log_level: "DEBUG"
  log_file: "./logs/dev_capture.log"
```

### **2. Environment-Based Camera Selection**

**Recommended Auto-Detection Priority:**
```python
# In CameraFactory.auto_detect_camera()
async def auto_detect_camera(cls, config_dir: Optional[str] = None) -> CameraInterface:
    """Auto-detect camera with development environment awareness."""

    # 1. Check if development mode is enabled
    system_config = SystemConfigManager().get_config()
    if system_config.get('development', {}).get('mock_camera_enabled', False):
        logger.info("Development mode: Using mock camera")
        return cls.create_camera('mock_camera', mock_config)

    # 2. Try to detect real hardware (Pi camera, USB cameras)
    for camera_type in ['arducam_imx519', 'pi_camera', 'usb_camera']:
        try:
            camera = cls.create_camera(camera_type, config)
            await camera.initialize()
            logger.info(f"Hardware detected: {camera_type}")
            return camera
        except CameraInitializationError:
            continue

    # 3. Fallback to mock camera if no hardware found
    logger.warning("No hardware cameras detected, falling back to mock camera")
    return cls.create_camera('mock_camera', mock_config)
```

### **3. Development Workflow Commands**

**Recommended Development Commands:**
```bash
# Start development server with mock camera
export SKYLAPSE_ENV=development
python3 -m src.capture_service --config=config/system/development.yaml

# Run tests with mock camera (current behavior)
python3 -m pytest tests/ -v

# Run hardware tests (skip on dev machine)
python3 -m pytest tests/ -m "not hardware" -v

# Run only mock camera tests
python3 -m pytest tests/test_mock_camera.py -v

# Test camera auto-detection
python3 -c "
import asyncio
from src.camera_interface import CameraFactory
async def test():
    camera = await CameraFactory.auto_detect_camera()
    print(f'Detected: {camera.specs.model}')
asyncio.run(test())
"
```

---

## 📋 **Enhanced Mock Camera Capabilities**

### **Current Mock Camera Features** ✅
- Configurable capture delay
- Failure simulation
- Basic image generation
- Realistic metadata
- HDR bracketing support

### **Recommended Enhancements** 💡

#### **1. Realistic Image Generation**
```python
# Enhanced mock image generation
def _generate_realistic_image(self, settings: CaptureSettings) -> bytes:
    """Generate more realistic test images."""
    # Different image content based on time of day
    if conditions and conditions.is_golden_hour:
        return self._generate_golden_hour_image()
    elif conditions and conditions.is_blue_hour:
        return self._generate_blue_hour_image()
    else:
        return self._generate_daylight_image()
```

#### **2. Environmental Response Simulation**
```python
# Mock camera responds to environmental conditions
async def optimize_settings_for_conditions(self, conditions: EnvironmentalConditions) -> CaptureSettings:
    """Simulate realistic camera optimization."""
    settings = CaptureSettings()

    # Simulate realistic ISO/exposure adjustments
    if conditions.ambient_light_lux < 100:  # Low light
        settings.iso = 800
        settings.exposure_time_us = 1000000  # 1 second
    elif conditions.is_golden_hour:
        settings.iso = 200
        settings.exposure_time_us = 250000   # 1/4 second

    return settings
```

#### **3. Hardware Failure Simulation**
```python
# Simulate realistic hardware issues
class MockCameraFailures:
    FOCUS_FAILURE = "focus_timeout"
    EXPOSURE_FAILURE = "overexposed"
    STORAGE_FAILURE = "disk_full"
    THERMAL_FAILURE = "overheating"
```

---

## 🚀 **Development Environment Best Practices**

### **For Development Team**

#### **1. Local Development Setup**
```bash
# Clone and setup
git clone <repo>
cd skylapse/capture

# Install dependencies
pip3 install -r requirements.txt

# Create development config
cp config/system/system.yaml config/system/development.yaml
# Edit development.yaml: mock_camera_enabled: true

# Start development server
export SKYLAPSE_ENV=development
python3 -m src.capture_service
```

#### **2. Testing Workflow**
```bash
# Test mock camera functionality
python3 -m pytest tests/test_mock_camera.py -v

# Test camera controller with mock
python3 -m pytest tests/test_camera_controller.py -v

# Test full system with mock camera
python3 -m pytest tests/ -m "not hardware" -v

# Before claiming completion, run ALL tests
python3 -m pytest tests/ -v --tb=short
```

#### **3. Hardware Integration Testing**
```bash
# On development machine (mock camera)
python3 -m pytest tests/ -m "not hardware" -v

# On Pi hardware (real camera)
ssh pi@helios
python3 -m pytest tests/ -m hardware -v
python3 -m pytest tests/test_performance_benchmarks.py -v
```

### **For QA Validation**

#### **1. Development Environment Validation**
- Verify mock camera auto-detection works
- Confirm development configuration overrides
- Test realistic failure scenarios
- Validate performance benchmarking with mock data

#### **2. Hardware Environment Validation**
- Deploy to helios Pi for real hardware testing
- Measure actual performance vs mock performance
- Validate environmental condition responses
- Test failure recovery with real hardware

---

## 📊 **Configuration Management Strategy**

### **Environment-Specific Configs**

```
config/
├── system/
│   ├── system.yaml           # Production config
│   ├── development.yaml      # Development overrides
│   └── testing.yaml          # Test-specific settings
├── cameras/
│   ├── arducam_imx519.yaml   # Real camera config
│   ├── mock_camera.yaml      # Mock camera config
│   └── usb_camera.yaml       # USB camera fallback
└── schedule/
    └── schedule_rules.yaml   # Capture scheduling
```

### **Environment Detection**
```python
# Automatic environment detection
def get_environment() -> str:
    """Detect current environment."""
    if os.getenv('SKYLAPSE_ENV'):
        return os.getenv('SKYLAPSE_ENV')
    elif Path('/opt/skylapse').exists():
        return 'production'
    elif 'pytest' in sys.modules:
        return 'testing'
    else:
        return 'development'
```

---

## 🎯 **Quality Assurance Benefits**

### **Why This Approach Works**

1. **Consistent Development**: All developers use same mock camera behavior
2. **Faster Iteration**: No hardware required for most development
3. **Reliable Testing**: Mock camera provides predictable test results
4. **Hardware Validation**: Clear separation between dev and hardware testing
5. **Production Ready**: Seamless transition from mock to real camera

### **QA Validation Points**

- ✅ Mock camera behaves realistically
- ✅ Auto-detection works in all environments
- ✅ Configuration overrides work correctly
- ✅ Performance benchmarks work with mock data
- ✅ Hardware deployment works seamlessly

---

## 🚀 **Implementation Priority**

### **Phase 1: Immediate (Today)**
1. **Update system config**: Enable `mock_camera_enabled: true` for development
2. **Test auto-detection**: Verify mock camera is selected automatically
3. **Document workflow**: Clear dev environment setup instructions

### **Phase 2: This Week**
1. **Enhanced mock camera**: More realistic image generation
2. **Environment detection**: Automatic dev vs production mode
3. **Configuration management**: Environment-specific config files

### **Phase 3: Future**
1. **Advanced simulation**: Hardware failure scenarios
2. **Performance modeling**: Mock camera matches real camera timing
3. **Integration testing**: Seamless dev-to-hardware workflow

---

## 💡 **Immediate Action Items**

### **For Development Team**
```bash
# Quick fix for current development
# Edit config/system/system.yaml
development:
  mock_camera_enabled: true  # Change from false to true
  debug_logging: true
  development_mode: true

# Test the change
python3 -c "
import asyncio
from src.camera_interface import CameraFactory
async def test():
    camera = await CameraFactory.auto_detect_camera()
    print(f'Camera type: {type(camera).__name__}')
    print(f'Camera model: {camera.specs.model}')
asyncio.run(test())
"
```

### **Expected Output**
```
Camera type: MockCamera
Camera model: Mock Camera v1.0
```

**This simple change will enable proper development environment testing while maintaining production hardware capability!** 🔧✅

---

*QA Development Environment Recommendations by Jordan Martinez on September 26, 2025*
