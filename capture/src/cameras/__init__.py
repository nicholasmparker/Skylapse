"""Camera implementations module."""

from .arducam_imx519 import ArducamIMX519Camera
from .mock_camera import MockCamera


# Register all camera implementations with the factory
def register_cameras():
    """Register all available camera implementations with the factory."""
    from ..camera_interface import CameraFactory

    # Register real cameras first (higher priority in auto-detection)
    CameraFactory.register_camera("arducam_imx519", ArducamIMX519Camera)

    # Register mock camera (fallback)
    CameraFactory.register_camera("mock_camera", MockCamera)

    # Future camera registrations will go here:
    # CameraFactory.register_camera('pi_camera_v3', PiCameraV3)
    # CameraFactory.register_camera('pi_camera_v2', PiCameraV2)


# Auto-register cameras when module is imported
register_cameras()

__all__ = ["MockCamera", "ArducamIMX519Camera", "register_cameras"]
