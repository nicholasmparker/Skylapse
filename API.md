# Skylapse API Documentation

## Overview

Skylapse is a timelapse photography system consisting of two microservices that work together to capture, process, and generate stunning timelapse videos. The system uses a Raspberry Pi with a camera module for image capture, orchestrated by a backend service that handles scheduling and image processing.

### System Architecture

```
┌─────────────────────┐         ┌──────────────────────┐
│   Backend API       │◄───────►│   Pi Capture API     │
│   (Port 8082)       │         │   (Port 8080)        │
│                     │         │                      │
│ - Scheduling        │         │ - Camera Control     │
│ - Exposure Calc     │         │ - Image Capture      │
│ - Orchestration     │         │ - Profile Execution  │
│ - Timelapse Gen     │         │ - Image Storage      │
└─────────────────────┘         └──────────────────────┘
         │                                   │
         ▼                                   ▼
    [Timelapses]                       [Raw Images]
```

### Key Concepts

- **Schedules**: Time windows when captures occur (sunrise, daytime, sunset)
- **Profiles**: Camera setting configurations (a-g) for different shooting styles
- **Sessions**: Grouping of captures for a specific profile/date/schedule
- **Solar Calculations**: Automatic sunrise/sunset timing based on location
- **Live Orchestration**: Backend calculates and sends settings to Pi for each capture
- **Deployed Profiles**: Pre-compiled settings stored on Pi for autonomous operation

---

## Backend API (Port 8082)

**Base URL**: `http://localhost:8082` (development) or `http://your-server:8082` (production)

The Backend API is the brain of the system, responsible for scheduling captures, calculating optimal camera settings, coordinating with the Pi, and generating timelapse videos.

### System Information

#### GET `/`

Get basic system information and current status.

**Response**

```json
{
  "app": "Skylapse Backend",
  "status": "running",
  "location": {
    "latitude": 39.609573,
    "longitude": -105.314163,
    "timezone": "America/Denver",
    "name": "Colorado"
  },
  "sun_times": {
    "sunrise": "2025-10-01T06:42:15-06:00",
    "sunset": "2025-10-01T18:36:42-06:00"
  },
  "schedules": ["sunrise", "daytime", "sunset"]
}
```

**Example**

```bash
curl http://localhost:8082/
```

---

#### GET `/health`

Health check endpoint for monitoring and load balancers.

**Response**

```json
{
  "status": "ok",
  "timestamp": "2025-10-01T12:00:00.123456"
}
```

**Example**

```bash
curl http://localhost:8082/health
```

---

#### GET `/system`

Comprehensive system status - everything you need to know at a glance. This is the main status endpoint for dashboards and monitoring.

**Response**

```json
{
  "timestamp": "2025-10-01T12:00:00-06:00",
  "timezone": "America/Denver",
  "sun": {
    "sunrise": "2025-10-01T06:42:15-06:00",
    "sunset": "2025-10-01T18:36:42-06:00",
    "is_daytime": true,
    "current_phase": "day"
  },
  "location": {
    "latitude": 39.609573,
    "longitude": -105.314163,
    "timezone": "America/Denver",
    "name": "Colorado"
  },
  "schedules": {
    "active": [
      {
        "name": "daytime",
        "type": "time_of_day",
        "window": {
          "start": "09:00:00",
          "end": "15:00:00"
        },
        "interval_seconds": 30
      }
    ],
    "configured": ["sunrise", "daytime", "sunset"],
    "enabled_count": 2
  },
  "camera": {
    "host": "192.168.0.124",
    "port": 8080,
    "status": "online",
    "profiles_configured": ["a", "b", "c", "d", "e", "f", "g"]
  },
  "system": {
    "backend_version": "2.0.0",
    "mode": "development",
    "scheduler_running": true
  }
}
```

**Example**

```bash
curl http://localhost:8082/system
```

---

### Schedules

#### GET `/schedules`

Get all schedule configurations with calculated time windows for solar schedules.

**Response**

```json
{
  "sunrise": {
    "enabled": true,
    "offset_minutes": -30,
    "duration_minutes": 60,
    "interval_seconds": 2,
    "stack_images": true,
    "stack_count": 5,
    "calculated_window": {
      "start": "2025-10-01T06:12:15-06:00",
      "end": "2025-10-01T07:12:15-06:00"
    }
  },
  "daytime": {
    "enabled": false,
    "start_time": "09:00",
    "end_time": "15:00",
    "interval_seconds": 30,
    "stack_images": false
  },
  "sunset": {
    "enabled": true,
    "offset_minutes": -30,
    "duration_minutes": 60,
    "interval_seconds": 2,
    "stack_images": true,
    "stack_count": 5,
    "calculated_window": {
      "start": "2025-10-01T18:06:42-06:00",
      "end": "2025-10-01T19:06:42-06:00"
    }
  }
}
```

**Schedule Parameters**

- `enabled` (boolean): Whether schedule is active
- `offset_minutes` (number): Minutes before/after solar event (sunrise/sunset only)
- `duration_minutes` (number): How long to capture (solar schedules only)
- `start_time` (string): Start time in HH:MM format (daytime schedule only)
- `end_time` (string): End time in HH:MM format (daytime schedule only)
- `interval_seconds` (number): Seconds between captures
- `stack_images` (boolean): Whether to stack images
- `stack_count` (number): Number of images to stack

**Example**

```bash
curl http://localhost:8082/schedules
```

---

#### GET `/status`

Get current system status including active schedules and sun times.

**Response**

```json
{
  "current_time": "2025-10-01T12:00:00-06:00",
  "sun_times": {
    "sunrise": "2025-10-01T06:42:15-06:00",
    "sunset": "2025-10-01T18:36:42-06:00"
  },
  "is_daytime": true,
  "active_schedules": ["daytime"],
  "pi_host": "192.168.0.124"
}
```

**Example**

```bash
curl http://localhost:8082/status
```

---

### Profiles

#### GET `/profiles`

Get latest images for all 7 camera profiles with descriptions and image counts.

**Response**

```json
[
  {
    "profile": "a",
    "description": "Pure Auto (No Bias)",
    "image_url": "http://192.168.0.124:8080/images/profile-a/capture_20251001_120000.jpg",
    "timestamp": 1727798400000,
    "image_count": 150
  },
  {
    "profile": "d",
    "description": "Warm Dramatic",
    "image_url": "http://192.168.0.124:8080/images/profile-d/capture_20251001_120000.jpg",
    "timestamp": 1727798400000,
    "image_count": 150
  }
]
```

**Profile Descriptions**

- **Profile A**: Pure Auto (No Bias) - Baseline camera auto settings
- **Profile B**: Daylight WB Fixed - Fixed white balance for consistency
- **Profile C**: Conservative Adaptive - Mild adaptive adjustments
- **Profile D**: Warm Dramatic - 3-shot HDR bracket (-1, 0, +1 EV)
- **Profile E**: Balanced Adaptive - Moderate adaptive settings
- **Profile F**: Spot Metering (Mountains) - Focus on specific scene area
- **Profile G**: Adaptive EV + Balanced WB - Prevents overexposure

**Example**

```bash
curl http://localhost:8082/profiles
```

---

### Timelapses

#### GET `/timelapses`

List all available timelapse videos with metadata.

**Response**

```json
[
  {
    "name": "profile-a_20251001_sunset",
    "url": "/timelapses/profile-a_20251001_sunset.mp4",
    "size": "45.3 MB",
    "created": "2025-10-01T19:15:30.123456"
  },
  {
    "name": "profile-d_20251001_sunrise",
    "url": "/timelapses/profile-d_20251001_sunrise.mp4",
    "size": "52.1 MB",
    "created": "2025-10-01T07:30:15.654321"
  }
]
```

**Notes**

- Videos are sorted by creation time, newest first
- The `/timelapses/` URL is served by the backend's static file handler
- Timelapse generation is automatic when a schedule window ends

**Example**

```bash
curl http://localhost:8082/timelapses
```

---

### Dashboard

#### GET `/dashboard`

Web-based monitoring dashboard (HTML page).

**Response**: HTML page with live system status, recent captures, and timelapse previews

**Example**

```bash
# Open in browser
open http://localhost:8082/dashboard
```

---

## Pi Capture API (Port 8080)

**Base URL**: `http://pi-hostname:8080` (typically `http://192.168.0.124:8080`)

The Pi Capture API runs on the Raspberry Pi and provides camera control, image capture, and profile execution capabilities.

### Camera Control

#### POST `/capture`

Capture a photo with specified settings. Supports three operational modes:

1. **Explicit Settings Mode** (backward compatible)
2. **Deployed Profile Mode** (autonomous operation)
3. **Override Mode** (profile with test overrides)

**Request Body (Mode 1: Explicit Settings)**

```json
{
  "iso": 400,
  "shutter_speed": "1/500",
  "exposure_compensation": 0.0,
  "profile": "a",
  "awb_mode": 1,
  "wb_temp": null,
  "hdr_mode": 0,
  "bracket_count": 1,
  "bracket_ev": null,
  "ae_metering_mode": null
}
```

**Request Body (Mode 2: Deployed Profile)**

```json
{
  "use_deployed_profile": true,
  "schedule_type": "sunset",
  "profile": "a"
}
```

**Request Body (Mode 3: Override Mode)**

```json
{
  "use_deployed_profile": true,
  "schedule_type": "sunset",
  "profile": "a",
  "override": {
    "exposure_compensation": -0.5,
    "iso": 200
  }
}
```

**Parameters**

| Parameter               | Type    | Default   | Description                                            |
| ----------------------- | ------- | --------- | ------------------------------------------------------ |
| `iso`                   | integer | 0         | ISO sensitivity (0=auto, 100-3200)                     |
| `shutter_speed`         | string  | "1/500"   | Shutter speed (e.g., "1/1000", "1/250")                |
| `exposure_compensation` | float   | 0.0       | EV compensation (-2.0 to +2.0)                         |
| `profile`               | string  | "default" | Profile name (a-g) for folder organization             |
| `awb_mode`              | integer | 1         | White balance (0=auto, 1=daylight, 2=cloudy, 6=custom) |
| `wb_temp`               | integer | null      | Color temperature in Kelvin (for awb_mode=6)           |
| `hdr_mode`              | integer | 0         | HDR mode (0=off, 1=single exposure)                    |
| `bracket_count`         | integer | 1         | Number of shots (1, 3, or 5)                           |
| `bracket_ev`            | array   | null      | EV offsets for bracketing (e.g., [-1.0, 0.0, 1.0])     |
| `ae_metering_mode`      | integer | null      | Metering (0=CentreWeighted, 1=Spot, 2=Matrix)          |
| `use_deployed_profile`  | boolean | false     | Enable deployed profile execution                      |
| `schedule_type`         | string  | null      | Schedule name for profile lookup                       |
| `override`              | object  | null      | Override settings for testing                          |

**Response**

```json
{
  "status": "success",
  "image_path": "/home/pi/skylapse-images/profile-a/capture_20251001_120000.jpg",
  "message": "Capture successful"
}
```

**Error Responses**

```json
{
  "status": "error",
  "message": "Camera not ready - check service logs"
}
```

**Examples**

Explicit settings (manual exposure):

```bash
curl -X POST http://192.168.0.124:8080/capture \
  -H "Content-Type: application/json" \
  -d '{
    "iso": 400,
    "shutter_speed": "1/500",
    "exposure_compensation": -0.3,
    "profile": "a",
    "awb_mode": 1
  }'
```

Auto exposure mode:

```bash
curl -X POST http://192.168.0.124:8080/capture \
  -H "Content-Type: application/json" \
  -d '{
    "iso": 0,
    "exposure_compensation": 0.0,
    "profile": "a",
    "ae_metering_mode": 2
  }'
```

HDR bracketing (3 shots):

```bash
curl -X POST http://192.168.0.124:8080/capture \
  -H "Content-Type: application/json" \
  -d '{
    "iso": 400,
    "shutter_speed": "1/500",
    "profile": "d",
    "bracket_count": 3,
    "bracket_ev": [-1.0, 0.0, 1.0]
  }'
```

Deployed profile mode:

```bash
curl -X POST http://192.168.0.124:8080/capture \
  -H "Content-Type: application/json" \
  -d '{
    "use_deployed_profile": true,
    "schedule_type": "sunset",
    "profile": "g"
  }'
```

---

#### GET `/meter`

Meter the scene using camera's auto-exposure to get suggested settings.

**Response**

```json
{
  "lux": 800.0,
  "exposure_time_us": 2000,
  "analogue_gain": 4.0,
  "suggested_iso": 400,
  "suggested_shutter": "1/500"
}
```

**Fields**

- `lux`: Scene brightness in lux
- `exposure_time_us`: Auto-calculated exposure time in microseconds
- `analogue_gain`: Raw sensor gain (ISO = gain × 100)
- `suggested_iso`: Rounded ISO value (100, 200, 400, 800, 1600, 3200)
- `suggested_shutter`: Human-readable shutter speed

**Example**

```bash
curl http://192.168.0.124:8080/meter
```

**Use Case**: The backend calls this endpoint to understand scene brightness before calculating profile-specific exposure settings.

---

### Status & Health

#### GET `/status`

Get camera status and operational mode.

**Response (Live Orchestration Mode)**

```json
{
  "status": "online",
  "camera_model": "ArduCam IMX519",
  "camera_ready": true,
  "mock_mode": false,
  "operational_mode": "live_orchestration"
}
```

**Response (Deployed Profile Mode)**

```json
{
  "status": "online",
  "camera_model": "ArduCam IMX519",
  "camera_ready": true,
  "mock_mode": false,
  "deployed_profile": {
    "profile_id": "profile-g-v1",
    "version": "1.0.0",
    "deployed_at": "2025-10-01T10:00:00",
    "schedules": ["sunrise", "sunset"]
  },
  "operational_mode": "deployed_profile"
}
```

**Example**

```bash
curl http://192.168.0.124:8080/status
```

---

#### GET `/health`

Simple health check endpoint.

**Response**

```json
{
  "status": "ok"
}
```

**Example**

```bash
curl http://192.168.0.124:8080/health
```

---

### Images

#### GET `/latest-image`

Get the most recent captured image info, optionally filtered by profile.

**Query Parameters**

- `profile` (optional): Filter by profile name (a-g)

**Response**

```json
{
  "image_url": "/images/profile-a/capture_20251001_120000.jpg",
  "profile": "a",
  "timestamp": 1727798400000,
  "image_count": 150
}
```

**Examples**

```bash
# Latest image from any profile
curl http://192.168.0.124:8080/latest-image

# Latest image from profile 'a'
curl http://192.168.0.124:8080/latest-image?profile=a
```

---

#### GET `/images/profile-{profile}/latest.jpg`

Get the latest captured image file from a specific profile.

**Path Parameters**

- `profile`: Profile name (a-g)

**Response**: Image file (JPEG)

**Notes**

- For HDR bracketed captures, returns the middle exposure (bracket1)
- Returns 404 if no images exist for the profile

**Example**

```bash
# Download latest image from profile 'a'
curl http://192.168.0.124:8080/images/profile-a/latest.jpg -o latest.jpg

# Display in browser
open http://192.168.0.124:8080/images/profile-a/latest.jpg
```

---

#### GET `/images/profile-{profile}/info`

Get metadata about the latest image in a profile.

**Path Parameters**

- `profile`: Profile name (a-g)

**Response**

```json
{
  "filename": "capture_20251001_120000.jpg",
  "size": 4567890,
  "modified": "2025-10-01T12:00:00",
  "profile": "a"
}
```

**Example**

```bash
curl http://192.168.0.124:8080/images/profile-a/info
```

---

#### GET `/images/profile-{profile}/list`

List all images in a profile folder.

**Path Parameters**

- `profile`: Profile name (a-g)

**Response**

```json
{
  "profile": "a",
  "count": 150,
  "images": [
    {
      "filename": "capture_20251001_120000.jpg",
      "size_bytes": 4567890,
      "modified": "2025-10-01T12:00:00"
    },
    {
      "filename": "capture_20251001_115958.jpg",
      "size_bytes": 4523410,
      "modified": "2025-10-01T11:59:58"
    }
  ]
}
```

**Notes**

- Images are sorted by modification time, newest first
- Useful for building image galleries or monitoring capture progress

**Example**

```bash
curl http://192.168.0.124:8080/images/profile-a/list
```

---

### Profile Deployment

Profile deployment enables the Pi to operate autonomously without backend coordination. Profiles contain pre-compiled settings and lux lookup tables.

#### POST `/profile/deploy`

Deploy a profile snapshot from the backend.

**Request Body**

```json
{
  "profile_id": "profile-g-v1",
  "version": "1.0.0",
  "settings": {
    "base": {
      "iso": 0,
      "shutter_speed": "1/500",
      "exposure_compensation": 0.0,
      "awb_mode": 6,
      "hdr_mode": 0,
      "bracket_count": 1,
      "ae_metering_mode": 2
    },
    "adaptive_wb": {
      "enabled": true,
      "lux_table": {
        "10": 7500,
        "50": 6500,
        "100": 5500,
        "500": 5000,
        "1000": 4500,
        "5000": 4000
      }
    },
    "schedule_overrides": {
      "sunrise": {
        "exposure_compensation": -0.3
      },
      "sunset": {
        "exposure_compensation": -0.5
      }
    }
  },
  "schedules": ["sunrise", "sunset"],
  "deployed_at": "2025-10-01T10:00:00"
}
```

**Profile Structure**

- `profile_id`: Unique identifier for this profile
- `version`: Profile version (semantic versioning)
- `settings.base`: Base camera settings
- `settings.adaptive_wb`: White balance lookup table by lux
- `settings.schedule_overrides`: Schedule-specific setting adjustments
- `schedules`: List of schedules this profile applies to
- `deployed_at`: Deployment timestamp (ISO 8601)

**Response**

```json
{
  "status": "deployed",
  "profile_id": "profile-g-v1",
  "version": "1.0.0",
  "operational_mode": "deployed_profile"
}
```

**Example**

```bash
curl -X POST http://192.168.0.124:8080/profile/deploy \
  -H "Content-Type: application/json" \
  -d @profile.json
```

---

#### GET `/profile/current`

Get currently deployed profile information.

**Response (Profile Deployed)**

```json
{
  "status": "deployed",
  "operational_mode": "deployed_profile",
  "profile_id": "profile-g-v1",
  "version": "1.0.0",
  "deployed_at": "2025-10-01T10:00:00",
  "schedules": ["sunrise", "sunset"]
}
```

**Response (No Profile)**

```json
{
  "status": "no_profile",
  "operational_mode": "live_orchestration",
  "message": "No profile deployed - using live orchestration mode"
}
```

**Example**

```bash
curl http://192.168.0.124:8080/profile/current
```

---

#### DELETE `/profile/current`

Clear deployed profile and revert to live orchestration mode.

**Response**

```json
{
  "status": "cleared",
  "operational_mode": "live_orchestration",
  "message": "Profile cleared - reverted to live orchestration mode"
}
```

**Example**

```bash
curl -X DELETE http://192.168.0.124:8080/profile/current
```

---

## Common Workflows

### 1. Live Orchestration Capture (Backend → Pi)

This is the primary workflow where the backend orchestrates each capture.

```bash
# 1. Backend checks sun times and active schedules
curl http://localhost:8082/status

# 2. Backend meters the scene via Pi
curl http://192.168.0.124:8080/meter

# 3. Backend calculates optimal settings based on:
#    - Current schedule (sunrise/daytime/sunset)
#    - Profile (a-g)
#    - Scene brightness (lux)
#    - Time within schedule window

# 4. Backend sends capture command to Pi with calculated settings
curl -X POST http://192.168.0.124:8080/capture \
  -H "Content-Type: application/json" \
  -d '{
    "iso": 400,
    "shutter_speed": "1/500",
    "exposure_compensation": -0.3,
    "profile": "g",
    "awb_mode": 6,
    "wb_temp": 5000
  }'

# 5. Pi captures image and returns path
# 6. Backend downloads image and records metadata
# 7. Process repeats every interval_seconds (e.g., every 2 seconds during sunset)
```

### 2. Deployed Profile Capture (Autonomous Pi)

For autonomous operation without backend coordination.

```bash
# 1. Backend deploys profile to Pi
curl -X POST http://192.168.0.124:8080/profile/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "profile_id": "profile-g-sunset",
    "version": "1.0.0",
    "settings": { ... },
    "schedules": ["sunset"]
  }'

# 2. Pi operates autonomously using deployed profile
curl -X POST http://192.168.0.124:8080/capture \
  -H "Content-Type: application/json" \
  -d '{
    "use_deployed_profile": true,
    "schedule_type": "sunset",
    "profile": "g"
  }'

# Pi internally:
# - Meters scene (gets lux)
# - Looks up settings from deployed profile
# - Applies adaptive WB based on lux
# - Applies schedule-specific overrides
# - Captures image
```

### 3. Timelapse Generation

Automatic timelapse generation at schedule end.

```bash
# 1. Check available timelapses
curl http://localhost:8082/timelapses

# 2. Download a timelapse
curl http://localhost:8082/timelapses/profile-a_20251001_sunset.mp4 \
  -o sunset.mp4

# Automatic generation happens when:
# - Schedule window ends (e.g., sunset ends at 7:06 PM)
# - Backend marks session as complete
# - Timelapse job is enqueued in Redis queue
# - Processing worker generates video from images
```

### 4. Multi-Profile Capture Burst

Backend captures all profiles in rapid sequence.

```bash
# Every interval (e.g., 2 seconds during sunset), backend captures:
# - Profile A: Pure auto
# - Profile D: 3-shot HDR bracket
# - Profile G: Adaptive EV

# This creates 3 parallel timelapse sequences for comparison
# Total capture time: ~15 seconds for all profiles
```

### 5. Monitoring & Debugging

```bash
# Check overall system status
curl http://localhost:8082/system

# Check Pi camera status
curl http://192.168.0.124:8080/status

# View latest captures from all profiles
curl http://localhost:8082/profiles

# Check specific profile images
curl http://192.168.0.124:8080/images/profile-g/list

# Test metering
curl http://192.168.0.124:8080/meter
```

---

## Error Handling

### HTTP Status Codes

Both APIs use standard HTTP status codes:

- `200 OK` - Request successful
- `400 Bad Request` - Invalid parameters (validation error)
- `404 Not Found` - Resource not found (image, profile, etc.)
- `500 Internal Server Error` - Server error (camera failure, etc.)
- `503 Service Unavailable` - Camera not ready

### Error Response Format

```json
{
  "detail": "Error description here"
}
```

### Common Errors

**Camera Not Ready (503)**

```json
{
  "detail": "Camera not ready - check service logs"
}
```

**Invalid ISO (400)**

```json
{
  "detail": "ISO must be 0 (auto) or one of [100, 200, 400, 800, 1600, 3200]"
}
```

**Invalid EV Compensation (400)**

```json
{
  "detail": "Exposure compensation must be between -2.0 and +2.0"
}
```

**No Profile Deployed (400)**

```json
{
  "detail": "No profile deployed - cannot use profile execution mode. Deploy a profile first or use explicit settings."
}
```

**Image Not Found (404)**

```json
{
  "detail": "No images found in profile a"
}
```

---

## Authentication & Security

### Current Status

- **No authentication** - APIs are designed for local network use
- Both services run on internal network only
- Not exposed to public internet

### Production Recommendations

If exposing to public internet:

- Add API key authentication
- Use HTTPS/TLS encryption
- Implement rate limiting
- Use firewall rules to restrict access
- Consider VPN for remote access

---

## Rate Limiting

### Current Status

- **No rate limiting** implemented
- System is designed for scheduled, predictable traffic patterns

### Typical Load

- **Backend**: 1 request per profile per interval (e.g., 3 profiles × 1 req/2sec = 1.5 req/sec during active schedule)
- **Pi**: Same as backend (receives capture commands)
- **Peak load**: ~3 req/sec during multi-profile capture bursts

---

## API Versioning

### Current Version

- Backend API: v2.0.0
- Pi Capture API: v1.0.0

### Versioning Strategy

- APIs use implicit versioning (no /v1/ prefix)
- Breaking changes require major version bump
- Profile deployment includes version field for compatibility tracking

---

## Performance Considerations

### Backend API

- **Response times**: <100ms for status endpoints, <500ms for profile queries
- **Concurrency**: Async/await using FastAPI for non-blocking operations
- **Scheduler loop**: Runs every 30 seconds (configurable per schedule)

### Pi Capture API

- **Image capture**: 2-3 seconds (full resolution 16MP)
- **HDR bracketing**: 6-9 seconds (3 shots)
- **Image download**: ~1 second (4-5MB JPEG over local network)
- **Metering**: <100ms

### Optimization Tips

1. **Reduce image size**: Use smaller resolution if 16MP not needed
2. **Adjust intervals**: Longer intervals = less load
3. **Use deployed profiles**: Reduces backend → Pi round trips
4. **Local image storage**: Pi stores images, backend downloads in background

---

## Development & Testing

### Mock Mode

Pi supports mock camera mode for development without hardware:

```bash
# Enable mock mode
export MOCK_CAMERA=true
python pi/main.py
```

### Testing Endpoints

```bash
# Test backend health
curl http://localhost:8082/health

# Test Pi health
curl http://192.168.0.124:8080/health

# Test capture with mock camera
curl -X POST http://192.168.0.124:8080/capture \
  -H "Content-Type: application/json" \
  -d '{"iso": 400, "profile": "a"}'
```

### Docker Environment

```bash
# Start backend in Docker
docker-compose up backend

# Start all services
docker-compose up

# View logs
docker-compose logs -f backend
```

---

## API Client Examples

### Python Client

```python
import httpx
import asyncio

async def capture_sunset_sequence():
    """Capture a sunset sequence using Backend API."""

    # Check system status
    async with httpx.AsyncClient() as client:
        # Get current status
        status = await client.get("http://localhost:8082/status")
        print(f"Active schedules: {status.json()['active_schedules']}")

        # Check if sunset is active
        if "sunset" in status.json()['active_schedules']:
            # Get latest profiles
            profiles = await client.get("http://localhost:8082/profiles")

            for profile in profiles.json():
                print(f"Profile {profile['profile']}: {profile['image_count']} images")

        # List timelapses
        timelapses = await client.get("http://localhost:8082/timelapses")
        for video in timelapses.json():
            print(f"Timelapse: {video['name']} ({video['size']})")

asyncio.run(capture_sunset_sequence())
```

### JavaScript/Node.js Client

```javascript
const axios = require("axios");

async function getSystemStatus() {
  try {
    // Get comprehensive system status
    const response = await axios.get("http://localhost:8082/system");
    const system = response.data;

    console.log(`Current time: ${system.timestamp}`);
    console.log(`Sunrise: ${system.sun.sunrise}`);
    console.log(`Sunset: ${system.sun.sunset}`);
    console.log(
      `Active schedules: ${system.schedules.active
        .map((s) => s.name)
        .join(", ")}`,
    );
    console.log(`Camera status: ${system.camera.status}`);

    // Get latest images
    const profiles = await axios.get("http://localhost:8082/profiles");
    profiles.data.forEach((p) => {
      console.log(`${p.profile}: ${p.description} (${p.image_count} images)`);
    });
  } catch (error) {
    console.error("Error:", error.message);
  }
}

getSystemStatus();
```

### Bash Script

```bash
#!/bin/bash
# Monitor sunset capture progress

BACKEND="http://localhost:8082"
PI="http://192.168.0.124:8080"

# Check if sunset is active
STATUS=$(curl -s "$BACKEND/status")
if echo "$STATUS" | grep -q "sunset"; then
    echo "Sunset capture is active!"

    # Get latest image from profile G
    curl -s "$PI/images/profile-g/info" | jq .

    # Check image count
    COUNT=$(curl -s "$PI/images/profile-g/list" | jq '.count')
    echo "Captured $COUNT images so far"
else
    echo "Sunset capture not active"
fi
```

---

## Troubleshooting

### Backend Issues

**Scheduler not running**

```bash
# Check logs
docker-compose logs -f backend

# Look for: "Scheduler loop started"
```

**Cannot reach Pi**

```bash
# Test connectivity
curl http://192.168.0.124:8080/health

# Check Pi host in config
curl http://localhost:8082/status | jq '.pi_host'
```

### Pi Issues

**Camera not ready**

```bash
# Check camera status
curl http://192.168.0.124:8080/status

# SSH into Pi and check logs
ssh pi@192.168.0.124
journalctl -u skylapse-capture -f
```

**Images not appearing**

```bash
# Check image directory
curl http://192.168.0.124:8080/images/profile-a/list

# SSH and verify files
ssh pi@192.168.0.124
ls -lh ~/skylapse-images/profile-a/
```

### Profile Deployment Issues

**Profile not deploying**

```bash
# Check current profile status
curl http://192.168.0.124:8080/profile/current

# Clear and redeploy
curl -X DELETE http://192.168.0.124:8080/profile/current
curl -X POST http://192.168.0.124:8080/profile/deploy -d @profile.json
```

---

## Appendix

### Camera Settings Reference

**ISO Values**

- `0`: Full auto mode
- `100-3200`: Manual ISO in stops (100, 200, 400, 800, 1600, 3200)

**White Balance Modes**

- `0`: Auto
- `1`: Daylight (5500K)
- `2`: Cloudy (6500K)
- `6`: Custom (specify `wb_temp` in Kelvin)

**Metering Modes**

- `0`: Centre-weighted (default)
- `1`: Spot (focus on center)
- `2`: Matrix (evaluate entire scene)

**HDR Bracketing**

- `bracket_count: 1`: Single shot
- `bracket_count: 3`: 3-shot HDR (typical: [-1.0, 0.0, +1.0])
- `bracket_count: 5`: 5-shot HDR (extreme: [-2.0, -1.0, 0.0, +1.0, +2.0])

### Schedule Types Reference

**Solar Schedules** (calculated daily)

- `sunrise`: Based on astronomical sunrise time
- `sunset`: Based on astronomical sunset time

**Time-based Schedules**

- `daytime`: Fixed start/end times (e.g., 09:00-15:00)

### File Paths

**Backend (Docker)**

- Images: `/data/images/profile-{a-g}/`
- Timelapses: `/data/timelapses/`
- Config: `/app/config.json`

**Pi (Direct)**

- Images: `~/skylapse-images/profile-{a-g}/`
- Profile: `~/.skylapse/current_profile.json`
- Logs: `journalctl -u skylapse-capture`

### URL Patterns

**Image URLs** (served by Pi)

```
http://192.168.0.124:8080/images/profile-a/capture_20251001_120000.jpg
```

**Timelapse URLs** (served by Backend)

```
http://localhost:8082/timelapses/profile-a_20251001_sunset.mp4
```

---

## Support & Contributing

### Documentation

- Full project docs: `/Users/nicholasmparker/Projects/skylapse/README.md`
- Docker setup: `/Users/nicholasmparker/Projects/skylapse/DEPLOYMENT_AND_DOCKER.md`
- Camera details: `/Users/nicholasmparker/Projects/skylapse/pi/CAMERA_IMPLEMENTATION.md`

### Source Code

- Backend API: `/Users/nicholasmparker/Projects/skylapse/backend/main.py`
- Pi Capture API: `/Users/nicholasmparker/Projects/skylapse/pi/main.py`

### API Updates

This documentation reflects the current API implementation as of October 2025. For the latest changes, refer to the source code or git commit history.

---

**Built with ❤️ for beautiful timelapse photography**
