# Camera Implementation Guide

## Current Implementation: ArduCam IMX519

**CRITICAL: System-Level Dependencies**

The ArduCam IMX519 requires:

- System-level `picamera2` (installed via apt, NOT pip)
- System-level `libcamera` drivers
- NEVER install picamera2 in a venv for this camera
- NEVER replace the system picamera2 installation

The camera initialization happens in `camera_factory.py` which detects the ArduCam and uses the system picamera2.

## Future Camera Support

To add support for different cameras:

1. **Create a new camera class** that implements the camera interface
2. **Update `camera_factory.py`** to detect and instantiate the new camera type
3. **Document camera-specific requirements** in this file

### Camera Interface

Each camera implementation should provide:

- `capture()` - Take a photo with specified settings
- `meter()` - Get current light metering (optional)
- `get_properties()` - Return camera model and capabilities
- `close()` - Clean up camera resources

### Example: Adding USB Camera Support

```python
class USBCamera:
    def __init__(self):
        # Uses opencv or v4l2, can install via pip
        import cv2
        self.camera = cv2.VideoCapture(0)

    def capture(self, settings):
        # Implement capture logic
        pass
```

## Factory Pattern

The `camera_factory.py` should detect which camera is connected and return the appropriate implementation. This allows the main service to work with any camera without knowing the details.
