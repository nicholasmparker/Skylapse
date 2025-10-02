# Skylapse: Super Simple Architecture

## Core Goal

Capture beautiful sunrise, daytime, and sunset timelapses with automatic exposure adjustments and image stacking.

## Three Components

### 1. Raspberry Pi (Edge Device)

**ONE job**: Take photos when told to

```python
# capture/main.py
@app.post("/capture")
async def capture_photo(settings: CaptureSettings):
    # Adjust camera settings (ISO, shutter, exposure)
    camera.configure(settings)

    # Take photo
    image_path = camera.capture()

    # Upload to backend
    upload_to_backend(image_path)

    return {"status": "success", "path": image_path}
```

**That's it.** No scheduling logic. No intelligence. Just captures.

---

### 2. Backend API (Brain)

**Does everything else**:

#### A. Schedule Management (3 simple schedules)

```python
SCHEDULES = {
    "sunrise": {
        "start": "sunrise - 30min",
        "end": "sunrise + 30min",
        "interval": "30 seconds"
    },
    "daytime": {
        "start": "9am",
        "end": "3pm",
        "interval": "5 minutes"
    },
    "sunset": {
        "start": "sunset - 30min",
        "end": "sunset + 30min",
        "interval": "30 seconds"
    }
}
```

#### B. Scheduler Loop

```python
# Run every 30 seconds
async def scheduler_tick():
    current_time = now()
    sun_times = get_sun_times(LAT, LON)  # Calculate sunrise/sunset

    for schedule_name, schedule in SCHEDULES.items():
        if should_capture(current_time, schedule, sun_times):
            # Calculate best camera settings for current light
            settings = calculate_exposure(current_time, schedule_name)

            # Tell Pi to capture
            await pi.capture(settings)
```

#### C. Smart Exposure Calculator

```python
def calculate_exposure(time, schedule_type):
    """Adjust camera settings based on time of day"""

    if schedule_type == "sunrise":
        # Fast shutter, high ISO during rapid light changes
        return {"iso": 800, "shutter": "1/1000", "ev": +0.7}

    elif schedule_type == "daytime":
        # Standard settings for bright light
        return {"iso": 100, "shutter": "1/500", "ev": 0}

    elif schedule_type == "sunset":
        # Longer exposure as light fades
        return {"iso": 400, "shutter": "1/250", "ev": +0.3}
```

#### D. Image Processing

```python
# When images arrive, process them
async def process_images(schedule_name, date):
    images = get_images_for_schedule(schedule_name, date)

    # Stack images for noise reduction (sunrise/sunset only)
    if schedule_name in ["sunrise", "sunset"]:
        stacked = stack_images(images, num_frames=5)
        save_stacked(stacked)

    # Generate timelapse video
    video_path = create_video(images, fps=24)

    return video_path
```

---

### 3. Frontend (Simple UI)

**Three buttons. Three videos.**

```
┌─────────────────────────────────┐
│     Today's Timelapses          │
├─────────────────────────────────┤
│                                 │
│  🌅 Sunrise (6:23am - 6:53am)  │
│     [▶ Play Video]              │
│                                 │
│  ☀️ Daytime (9:00am - 3:00pm)  │
│     [▶ Play Video]              │
│                                 │
│  🌇 Sunset (5:47pm - 6:17pm)   │
│     [▶ Play Video]              │
│                                 │
└─────────────────────────────────┘
```

**Settings page**:

```
┌─────────────────────────────────┐
│     Settings                    │
├─────────────────────────────────┤
│  Location: [Lat/Lon]            │
│  Timezone: [America/New_York]   │
│                                 │
│  Sunrise Interval: [30s]        │
│  Daytime Interval: [5min]       │
│  Sunset Interval: [30s]         │
│                                 │
│  Enable Stacking: [✓]           │
│  Frames to Stack: [5]           │
│                                 │
│  [Save Settings]                │
└─────────────────────────────────┘
```

---

## Data Flow

```
1. Backend Scheduler (every 30s)
   ↓
2. Check: "Should I capture now?"
   ↓
3. Calculate exposure settings
   ↓
4. HTTP POST → Raspberry Pi
   ↓
5. Pi captures photo
   ↓
6. Pi uploads to backend
   ↓
7. Backend stores image
   ↓
8. End of day: Process & stack images
   ↓
9. Generate timelapse videos
   ↓
10. Frontend displays videos
```

---

## File Structure

```
skylapse/
├── pi/
│   ├── main.py              # Simple capture server
│   └── camera.py            # Camera control
│
├── backend/
│   ├── main.py              # FastAPI app
│   ├── scheduler.py         # Schedule loop
│   ├── exposure.py          # Smart exposure calculator
│   ├── processor.py         # Image stacking & video gen
│   └── data/
│       ├── images/          # Raw images
│       └── videos/          # Generated timelapses
│
└── frontend/
    ├── src/
    │   ├── App.tsx          # Three video players
    │   └── Settings.tsx     # Location & intervals
    └── package.json
```

---

## Why This Is Simple

1. **No complex scheduling**: Just 3 hardcoded schedules
2. **No database**: Files on disk
3. **No queues**: Direct HTTP calls
4. **No auth** (for v1): Local network only
5. **No multi-camera**: One Pi, one camera
6. **No manual captures**: Auto-only

---

## Why This Will Work

1. **Brain-Edge separation**: Backend makes decisions, Pi executes
2. **Smart exposure**: Settings adjust to light conditions automatically
3. **Image stacking**: High quality sunrise/sunset shots
4. **Simple UI**: See today's timelapses instantly
5. **Expandable**: Can add features later without rewrite

---

## First Steps to Build

### Step 1: Raspberry Pi Capture Server (1 hour)

- Simple Flask/FastAPI server
- One endpoint: `POST /capture`
- Uses picamera2 library
- Returns image path

### Step 2: Backend Scheduler (2 hours)

- Calculate sunrise/sunset times (use `astral` library)
- Simple loop that runs every 30 seconds
- Check if current time matches any schedule
- HTTP POST to Pi with camera settings

### Step 3: Smart Exposure (1 hour)

- Function that returns camera settings based on:
  - Schedule type (sunrise/daytime/sunset)
  - Current time
  - Distance from sunrise/sunset
- Start with hardcoded values, tune later

### Step 4: Image Processing (3 hours)

- End-of-day job (runs at midnight)
- Stack images using OpenCV/PIL
- Generate video using ffmpeg
- Save to `backend/data/videos/`

### Step 5: Simple Frontend (2 hours)

- React app with 3 video players
- Fetch videos from backend API
- Display sunrise/sunset times
- Basic settings page

---

## Settings That Actually Matter

```python
SETTINGS = {
    "location": {
        "lat": 40.7128,
        "lon": -74.0060,
        "timezone": "America/New_York"
    },
    "schedules": {
        "sunrise": {"interval_seconds": 30, "duration_minutes": 60},
        "daytime": {"interval_seconds": 300, "duration_hours": 6},
        "sunset": {"interval_seconds": 30, "duration_minutes": 60}
    },
    "processing": {
        "enable_stacking": True,
        "stack_frame_count": 5,
        "video_fps": 24
    }
}
```

---

## What We're NOT Building (Yet)

- ❌ User accounts
- ❌ Cloud storage
- ❌ Mobile app
- ❌ Manual captures
- ❌ Multiple cameras
- ❌ Weather integration
- ❌ Custom schedules
- ❌ Live preview
- ❌ Social sharing
- ❌ Advanced editing

**Just sunrise, daytime, and sunset timelapses. That's it.**

---

## Success = This Scenario

1. User wakes up at 7am
2. Opens `http://localhost:3000`
3. Sees **"Sunrise 6:23am - 6:53am"**
4. Clicks play
5. Watches beautiful 30-second timelapse of sunrise
6. Smiles

**That's the entire product.**

---

## Tech Stack (Minimal)

- **Pi**: Python 3.11 + FastAPI + picamera2
- **Backend**: Python 3.11 + FastAPI + astral + OpenCV
- **Frontend**: React + TypeScript + Video.js
- **Storage**: Local filesystem
- **Deployment**: Docker Compose (3 containers)

---

## Timeline

- **Week 1**: Pi capture server + Backend scheduler working
- **Week 2**: Smart exposure + Image stacking
- **Week 3**: Video generation + Frontend
- **Week 4**: Polish + Deploy

**Total: 1 month to working product**

---

## Next Action

Delete everything. Start with:

```bash
mkdir skylapse-v2
cd skylapse-v2
mkdir pi backend frontend
echo "Let's build this right."
```
