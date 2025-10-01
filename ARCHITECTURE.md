# Skylapse Architecture

**Version:** 2.0
**Last Updated:** 2025-10-01
**Status:** Evolution from Single-Camera to Multi-Camera System

---

## System Overview

Skylapse is a distributed timelapse photography system designed for professional landscape photography. The system coordinates multiple Raspberry Pi cameras to capture synchronized timelapses across different viewpoints.

### Core Principles

1. **Brain as Source of Truth** - All configuration, schedules, and profile logic originate in the Backend
2. **Smart Centralized, Dumb Distributed** - Intelligence lives in the Backend; Pis execute efficiently
3. **Resilient Production** - Profile deployment enables network-independent operation
4. **Flexible Development** - Testing workflows support rapid iteration on new cameras/seasons

---

## Service Boundaries

### Backend Service (The Brain)

**Location:** Docker container on development machine / server
**Port:** 8082
**Technology:** Python FastAPI

**Responsibilities:**

- ✅ **Source of truth** for all configuration (schedules, profiles, camera registry)
- ✅ **Schedule orchestration** (when captures should happen)
- ✅ **Exposure calculation logic** (adaptive WB curves, EV compensation strategies)
- ✅ **Solar calculations** (sunrise/sunset times, golden hour windows)
- ✅ **Multi-camera coordination** (parallel capture orchestration)
- ✅ **Profile compilation** (convert profile definitions into executable snapshots)
- ✅ **Testing workflows** (A/B testing, seasonal tuning)
- ✅ **Image aggregation** (future: collect images from all cameras)
- ✅ **Timelapse generation** (future: stitch images into videos)

**Does NOT:**

- ❌ Execute captures directly
- ❌ Store images (images live on Pis)
- ❌ Control hardware (camera operations on Pi)

### Pi Service (Camera/Capture)

**Location:** Raspberry Pi with ArduCam IMX519
**Port:** 8080
**Technology:** Python FastAPI + picamera2

**Responsibilities:**

- ✅ **Hardware control** (camera configuration, capture execution)
- ✅ **Real-time metering** (provide lux, suggested ISO/shutter to Backend)
- ✅ **Profile execution** (when deployed: calculate settings locally using profile snapshot)
- ✅ **Image storage** (local filesystem, organized by schedule/profile)
- ✅ **Status reporting** (health, deployed profile, disk usage)

**Does NOT:**

- ❌ Make scheduling decisions (Backend tells it when to capture)
- ❌ Define profiles (Backend pushes profile definitions)
- ❌ Coordinate with other Pis (Backend orchestrates)
- ❌ Process images (future: Processing service handles this)

### Processing Service (Future)

**Location:** Docker container with GPU access
**Port:** 8081
**Technology:** Python FastAPI + OpenCV/ffmpeg

**Responsibilities (Future):**

- ✅ Image processing (HDR merge, alignment, color grading)
- ✅ Video generation (stitch timelapses, apply effects)
- ✅ Image analysis (detect quality issues, exposure problems)

---

## Operational Modes

The system supports **three operational modes** to balance production resilience with development flexibility:

### Mode 1: Live Orchestration

**Use Case:** Development, testing, rapid iteration

**Flow:**

```
Backend → Pi: GET /meter (get current lux/metering)
Backend: Calculate settings using exposure.py logic
Backend → Pi: POST /capture {iso, shutter, ev_comp, metering_mode}
Pi: Execute capture with explicit settings
```

**Characteristics:**

- Full flexibility - Backend has complete control
- Requires network - Backend must reach Pi for every capture
- Current implementation (as of Sprint 4)

### Mode 2: Profile Deployment (Production)

**Use Case:** Production multi-camera, resilient operation

**Flow:**

```
Backend: Compile profile into snapshot (base settings + lux lookup table)
Backend → Pi: POST /profile/deploy {profile_snapshot}
Pi: Store profile locally, switch to autonomous mode

Later (scheduled capture):
Backend → Pi: POST /capture {schedule: "sunrise"}
Pi: Load deployed profile
Pi: GET /meter locally (own hardware)
Pi: Calculate settings using profile lux_table
Pi: Execute capture
```

**Characteristics:**

- Network-independent - Pi operates autonomously if Backend unreachable
- Fast - No metering round-trip, single HTTP call
- Resilient - Pi continues capturing during network issues

### Mode 3: Override Testing (Hybrid)

**Use Case:** A/B testing against production baseline, seasonal tuning

**Flow:**

```
Pi: Has deployed profile (production baseline)
Backend → Pi: POST /capture {override: {ev_comp: 0.9}, test_id: "spring_test"}
Pi: Use override settings for THIS capture only
Pi: Revert to deployed profile for next capture
```

**Characteristics:**

- Non-disruptive testing - Production profile remains active
- Quick iteration - No need to deploy/undeploy for experiments
- Comparable results - Test captures use same conditions as production

---

## Data Flow Architecture

### Schedule Execution (Multi-Camera)

```
┌─────────────────────────────────────────────────────────────┐
│ Backend Scheduler Loop (every 15-30s)                       │
│                                                              │
│ 1. Check time against all schedules                         │
│ 2. Determine which cameras should capture for this schedule │
│ 3. Build capture requests for each camera                   │
│ 4. Execute captures in parallel (asyncio.gather)            │
│ 5. Log aggregate results                                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ├─────────────┬─────────────┬─────────────┐
                              ▼             ▼             ▼             ▼
                        ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
                        │  Pi 1    │  │  Pi 2    │  │  Pi 3    │  │  Pi N    │
                        │ Mountain │  │  Valley  │  │ Overhead │  │   ...    │
                        │          │  │          │  │          │  │          │
                        │ Profile F│  │ Profile B│  │ Profile A│  │   ...    │
                        └──────────┘  └──────────┘  └──────────┘  └──────────┘
                              │             │             │             │
                              ▼             ▼             ▼             ▼
                        ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
                        │  Images  │  │  Images  │  │  Images  │  │  Images  │
                        │  /sunrise│  │  /sunrise│  │ /daytime │  │   ...    │
                        │  /daytime│  │  /sunset │  │          │  │          │
                        └──────────┘  └──────────┘  └──────────┘  └──────────┘
```

### Profile Deployment Flow

```
┌────────────────────────────────────────────────────────────────┐
│ Backend: Profile Definition (Source of Truth)                  │
│                                                                 │
│ {                                                               │
│   profile_id: "mountain_spot_winter_2025",                     │
│   metering_mode: 1,  # Spot                                    │
│   ev_compensation: 0.7,                                        │
│   awb_mode: 1,  # Daylight                                     │
│   adaptive_wb_curve: "balanced"                                │
│ }                                                               │
└────────────────────────────────────────────────────────────────┘
                              │
                              │ Compile profile
                              ▼
┌────────────────────────────────────────────────────────────────┐
│ Backend: Profile Snapshot (Executable)                         │
│                                                                 │
│ {                                                               │
│   profile_id: "mountain_spot_winter_2025",                     │
│   version: "1.0.0",                                            │
│   settings: {                                                   │
│     base: {metering_mode: 1, ev_compensation: 0.7, ...},      │
│     adaptive_wb: {                                             │
│       lux_table: [                                             │
│         [10000, 5500], [8000, 5500], [6000, 5450], ...        │
│       ]                                                         │
│     },                                                          │
│     schedule_overrides: {sunrise: {ev_compensation: 0.9}}     │
│   }                                                             │
│ }                                                               │
└────────────────────────────────────────────────────────────────┘
                              │
                              │ Deploy via API
                              ▼
┌────────────────────────────────────────────────────────────────┐
│ Pi: Stored Profile (Local Filesystem)                          │
│ /home/pi/.skylapse/current_profile.json                        │
│                                                                 │
│ Pi executes captures using this local profile without          │
│ requiring Backend for metering/calculation                     │
└────────────────────────────────────────────────────────────────┘
```

---

## API Contracts

### Backend → Pi Communication

#### Live Orchestration (Current)

```http
GET http://pi-mountain.local:8080/meter
→ {lux: 2500, suggested_iso: 400, suggested_shutter: "1/500"}

POST http://pi-mountain.local:8080/capture
{
  "iso": 400,
  "shutter_speed": "1/500",
  "exposure_compensation": 0.7,
  "awb_mode": 1,
  "ae_metering_mode": 1,
  "profile": "f",
  "schedule": "sunset"
}
→ {status: "success", image_path: "/home/pi/..."}
```

#### Profile Deployment (Future)

```http
POST http://pi-mountain.local:8080/profile/deploy
{
  "profile_id": "mountain_spot_winter_2025",
  "version": "1.0.0",
  "settings": {
    "base": {...},
    "adaptive_wb": {lux_table: [...]},
    "schedule_overrides": {...}
  }
}
→ {status: "deployed", profile_id: "mountain_spot_winter_2025"}

POST http://pi-mountain.local:8080/capture
{
  "use_deployed_profile": true,
  "schedule_type": "sunset"
}
→ {status: "success", image_path: "/home/pi/...", settings_used: {...}}
```

#### Override Testing (Future)

```http
POST http://pi-mountain.local:8080/capture
{
  "use_deployed_profile": true,
  "schedule_type": "sunset",
  "override": {
    "exposure_compensation": 0.9
  },
  "test_id": "spring_tuning_test_3"
}
→ Pi uses override for this capture, reverts to profile after
```

---

## Configuration Management

### Single Source of Truth: backend/config.json

```json
{
  "location": {
    "latitude": 39.609573,
    "longitude": -105.314163,
    "timezone": "America/Denver"
  },
  "schedules": {
    "sunrise": {
      "enabled": true,
      "offset_minutes": -30,
      "duration_minutes": 60,
      "interval_seconds": 15
    },
    "daytime": {
      "enabled": true,
      "start_time": "07:30",
      "end_time": "17:45",
      "interval_seconds": 30
    },
    "sunset": {
      "enabled": true,
      "offset_minutes": -30,
      "duration_minutes": 60,
      "interval_seconds": 15
    }
  },
  "cameras": {
    "mountain_view": {
      "host": "192.168.0.124",
      "port": 8080,
      "location": "north_ridge",
      "deployed_profile": "mountain_spot_winter_2025",
      "schedules": ["sunrise", "daytime", "sunset"]
    }
  }
}
```

**Key Principle:** Backend config.json is the **only** source of truth. Pis receive their configuration via API deployment, not config files.

---

## Current vs Future State

### Current State (Sprint 4 - Single Camera)

| Aspect           | Implementation                                   |
| ---------------- | ------------------------------------------------ |
| **Cameras**      | 1 Pi (mountain view)                             |
| **Profiles**     | 6 profiles (A-F) captured in burst every 15-30s  |
| **Mode**         | Live Orchestration only                          |
| **Metering**     | Backend requests meter data, calculates settings |
| **Capture Flow** | 2 HTTP calls (meter → capture)                   |
| **Resilience**   | Requires network for every capture               |

### Future State (Multi-Camera Production)

| Aspect           | Implementation                                           |
| ---------------- | -------------------------------------------------------- |
| **Cameras**      | 3+ Pis (mountain, valley, overhead, ...)                 |
| **Profiles**     | 1 profile per Pi (mountain=F, valley=B, overhead=A)      |
| **Mode**         | Profile Deployment (production) + Override Testing (dev) |
| **Metering**     | Pi meters locally, uses deployed profile logic           |
| **Capture Flow** | 1 HTTP call (capture with deployed profile)              |
| **Resilience**   | Network-independent, continues during outages            |

---

## Profile Definitions

Profiles define **strategic intent** for different scene types. Backend stores profile definitions, compiles them into executable snapshots, and deploys to Pis.

### Profile A: Center-Weighted Auto

- **Use Case:** General purpose, balanced exposure
- **Metering:** Center-weighted (focuses on middle of frame)
- **EV Compensation:** +0.3 (slight bias for foreground)
- **White Balance:** Auto

### Profile B: Daylight Fixed

- **Use Case:** Consistent color across timelapse
- **Metering:** Matrix (evaluates entire scene)
- **EV Compensation:** 0.0 (neutral)
- **White Balance:** Daylight (5500K fixed)

### Profile C: Conservative Adaptive

- **Use Case:** Protect highlights, subtle warmth
- **Metering:** Matrix
- **EV Compensation:** -0.3 (underexpose slightly)
- **White Balance:** Adaptive curve (conservative)

### Profile D: Warm Dramatic

- **Use Case:** Embrace golden tones, dramatic sunset
- **Metering:** Matrix
- **EV Compensation:** 0.0
- **White Balance:** Adaptive curve (warm)

### Profile E: Balanced Adaptive

- **Use Case:** Matches daylight when bright, natural warmth
- **Metering:** Matrix
- **EV Compensation:** 0.0
- **White Balance:** Adaptive curve (balanced)

### Profile F: Mountain Spot Metering ⭐

- **Use Case:** Mountain landscapes with bright sky (PRIMARY PRODUCTION PROFILE)
- **Metering:** Spot (center of frame where mountains are)
- **EV Compensation:** +0.7 (strong bias for darker mountains)
- **White Balance:** Daylight (5500K fixed)
- **Strategy:** Ignore bright sky, optimize for mountain detail

---

## Design Decisions & Rationale

### Why Keep Adaptive WB Curves in Backend?

**Decision:** Exposure calculation logic stays in Backend, deployed as lookup tables

**Rationale:**

- Curves are complex business logic (lux-based interpolation)
- Duplicating across 3+ Pis creates version drift risk
- Profile deployment "compiles" curves into executable lux_table
- Pi just interpolates from table (simple, fast, no logic duplication)

### Why Profile Deployment vs. Always Live?

**Decision:** Support both modes - live for dev, deployed for production

**Rationale:**

- **Resilience:** Network issues shouldn't stop production captures
- **Performance:** 1 HTTP call vs. 2 (eliminate metering round-trip)
- **Flexibility:** Testing mode still allows rapid iteration
- **Scalability:** 10 Pis × 3 captures/min = 30 requests/min to Backend (deployed) vs. 60 requests/min (live)

### Why Not Schedule Storage on Pi?

**Decision:** Backend owns all schedules, tells Pis when to capture

**Rationale:**

- **Single source of truth:** Schedule changes happen once (Backend config)
- **Coordination:** Backend can coordinate multi-camera synchronized captures
- **Solar calculations:** Backend has location data, calculates sunrise/sunset
- **Simplified Pi:** Pi is "dumb" executor, doesn't need schedule logic

### Why Allow Override Mode?

**Decision:** Deployed profile can be overridden per-capture for testing

**Rationale:**

- **Non-disruptive testing:** Don't need to undeploy production profile to test
- **A/B comparison:** Test new settings alongside production baseline
- **Seasonal tuning:** Quickly iterate on EV compensation as seasons change
- **Reversible:** Override is one-time, doesn't persist

---

## Future Enhancements

### Multi-Camera Coordination

- Camera registry in Backend config
- Parallel capture orchestration with asyncio.gather()
- Per-camera profile assignment

### Testing Workflows

- A/B testing API for comparing multiple profile variants
- Side-by-side image comparison UI
- Test result tracking and analytics

### Profile Management

- Web UI for profile creation and editing
- Profile versioning with semantic versioning
- Profile inheritance (seasonal variants extend base profiles)
- Rollback capability

### Image Processing Pipeline

- Processing service for HDR merge, alignment, color grading
- Automatic timelapse generation
- Image quality analysis and alerts

### Storage & Sync

- Automatic image sync from Pis to central storage
- Image deduplication and compression
- Retention policies (keep X days, archive older)

---

## Migration Path

### Phase 1: Document Current Architecture ✅

- Codify service boundaries
- Document API contracts
- Establish design principles

### Phase 2: Add Camera Registry (Next)

- Multi-camera configuration in Backend
- Parallel capture orchestration
- Per-camera status tracking

### Phase 3: Implement Profile Deployment

- Profile compilation logic in Backend
- Profile storage endpoint on Pi
- Profile execution logic on Pi

### Phase 4: Production Deployment

- Deploy profiles to Pis
- Switch to profile deployment mode
- Monitor and validate

### Phase 5: Testing Workflows

- A/B testing API
- Override testing support
- Comparison UI

---

## Monitoring & Operations

### Health Checks

**Backend:**

- `GET /health` → Scheduler status, last capture times
- `GET /status` → Active schedules, camera statuses
- `GET /cameras/{camera_id}/status` → Per-camera health

**Pi:**

- `GET /status` → Camera ready, deployed profile, disk usage
- Disk usage alerts (>80% full)
- Capture failure tracking

### Logging

**Backend:**

- Scheduler loop iterations
- Capture batch results (success/failure per camera)
- Profile deployment events

**Pi:**

- Profile execution logs (metering → calculation → capture)
- Capture success/failure with settings used
- Disk usage warnings

---

## References

- **API Architecture Review:** See QA agent comprehensive review above
- **Current Implementation:** backend/main.py, backend/exposure.py, pi/main.py
- **Configuration:** backend/config.json
- **Profile Logic:** backend/exposure.py:\_apply_profile_settings()

---

**Document Status:** Living document - update as architecture evolves
