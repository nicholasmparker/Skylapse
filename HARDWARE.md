# Skylapse Hardware Configuration

## Raspberry Pi

**Hostname**: `helios.local`
**Username**: `nicholasmparker`
**SSH Access**: `ssh nicholasmparker@helios.local`

## Camera

**Model**: Arducam IMX519
**Sensor**: Sony IMX519 (16 Megapixels)
**Interface**: MIPI CSI-2
**Tuning File**: `/usr/share/libcamera/ipa/rpi/vc4/imx519.json`

### Camera Capabilities

```
Resolution: 16MP (4656 x 3496)
Sensor Size: 1/2.534" (6.46mm diagonal)
Pixel Size: 1.22μm × 1.22μm
```

### Exposure Controls

```python
AnalogueGain: 1.0 to 16.0 (ISO 100 to 1600)
ExposureTime: 1μs to 66,666μs (1μs to 66ms, ~1/15s max)
ExposureValue: -8.0 to +8.0 stops
HdrMode: 0-4 (Off, SingleExposure, MultiExposure, Night, Unknown)
Brightness: -1.0 to +1.0
```

### Focus & White Balance

```python
AfMode: 0-2 (Manual, Auto, Continuous)
LensPosition: 0.0 to 32.0
AwbMode: 0-7 (Auto, Daylight, Cloudy, etc.)
ColourGains: 0.0 to 32.0
ColourTemperature: 100K to 100,000K
```

### Image Quality

```python
Sharpness: 0.0 to 16.0
Contrast: 0.0 to 32.0
Saturation: 0.0 to 32.0
NoiseReductionMode: 0-4
```

## libcamera Version

```
libcamera v0.5.2+125-69c6546d-dirty
Compiled: 2025-09-12T07:28:55BST
```

## Device Paths

```
Camera: /base/soc/i2c0mux/i2c@1/imx519@1a
Unicam: /dev/media3
ISP: /dev/media0
```

## Deployment

```bash
# Deploy capture service
./scripts/deploy-capture.sh helios.local nicholasmparker

# Check camera status
ssh nicholasmparker@helios.local "python3 -c 'from picamera2 import Picamera2; print(Picamera2().camera_properties)'"

# View service logs
ssh nicholasmparker@helios.local "sudo journalctl -u skylapse-capture -f"
```

## Performance Characteristics

**Maximum Frame Rate**: ~30 FPS (for video)
**Still Capture Time**: ~200-500ms (depending on settings)
**Startup Time**: ~2 seconds (camera initialization)
**Power Consumption**: ~2.5W (camera module)

## Known Limitations

1. **Max Exposure**: 66ms (~1/15s) - not suitable for astrophotography
2. **Rolling Shutter**: CMOS sensor has rolling shutter (not global)
3. **Heat Sensitivity**: Sensor can heat up during extended use
4. **Focus**: Manual focus only (AF may not be available)

## Optimal Settings for Timelapse

See `EXPOSURE_STRATEGY.md` for detailed exposure recommendations.

**General Guidelines**:

- ISO 100-800 for best quality (avoid 1600 if possible)
- Shutter 1/250s to 1/1000s during golden hour
- Use HDR Mode 1 (SingleExposure) for dynamic range
- Keep camera running (don't stop/start between frames)

## Testing Commands

```bash
# Test camera detection
ssh nicholasmparker@helios.local "python3 -c 'from picamera2 import Picamera2; Picamera2()'"

# Capture test image
ssh nicholasmparker@helios.local "python3 << EOF
from picamera2 import Picamera2
cam = Picamera2()
cam.start()
cam.capture_file('/tmp/test.jpg')
cam.stop()
print('Captured: /tmp/test.jpg')
EOF"

# Check image
scp nicholasmparker@helios.local:/tmp/test.jpg ./test.jpg && open test.jpg
```

## Troubleshooting

### Camera Not Detected

```bash
# Check ribbon cable connection
# Ensure camera is enabled in raspi-config
ssh nicholasmparker@helios.local "sudo raspi-config"
# Interface Options → Camera → Enable
```

### Permission Issues

```bash
# Add user to video group
ssh nicholasmparker@helios.local "sudo usermod -a -G video nicholasmparker"
```

### Performance Issues

```bash
# Check temperature
ssh nicholasmparker@helios.local "vcgencmd measure_temp"

# Check throttling
ssh nicholasmparker@helios.local "vcgencmd get_throttled"
```

## Future Hardware Upgrades

**Potential Improvements**:

1. **IMX477** (12MP HQ Camera) - Better low-light performance
2. **Active cooling** - Prevent thermal throttling during long captures
3. **C/CS lens mount** - Interchangeable lenses for different FOV
4. **PoE HAT** - Power over Ethernet for remote installations
5. **RTC module** - Accurate timekeeping without network

## Links

- [Arducam IMX519 Documentation](https://docs.arducam.com/Raspberry-Pi-Camera/Native-camera/16MP-IMX519/)
- [picamera2 Manual](https://datasheets.raspberrypi.com/camera/picamera2-manual.pdf)
- [libcamera Documentation](https://libcamera.org/api-html/)
