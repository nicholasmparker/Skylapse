# Skylapse

**Automated timelapse photography system with intelligent exposure profiles and database-driven video generation.**

![Status: Production](https://img.shields.io/badge/status-production-success)
![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue)
![Docker](https://img.shields.io/badge/docker-required-blue)

---

## What It Does

Skylapse captures stunning timelapses automatically using a Raspberry Pi and ArduCam IMX519 (16MP). The system:

- 🌅 **Schedules captures** for sunrise, daytime, and sunset with configurable intervals
- 🎨 **Tests 7 exposure profiles** simultaneously (A-G) to find the perfect look
- 🗄️ **Tracks everything** in SQLite - sessions, captures, metadata, image paths
- 🎬 **Generates timelapses** automatically when schedules end using Redis Queue workers
- 📊 **Monitors in real-time** via React web UI with live camera preview

**Current production profiles:** A (pure auto), D (warm adaptive), G (adaptive EV + balanced WB)

---

## System Architecture

```
┌─────────────┐
│  Raspberry  │ ──captures──▶ Local storage (/home/pi/skylapse-images/)
│     Pi      │               │
│  (Capture)  │               │
└─────────────┘               │
                              │
                              ▼
┌─────────────┐         ┌──────────────┐
│   Backend   │────────▶│   SQLite DB  │  Sessions, Captures, Metadata
│  Scheduler  │         └──────────────┘
│  Exposure   │               │
│  Calculator │               │
└─────────────┘               │
      │                       │
      │                       ▼
      │                 ┌──────────────┐
      │                 │ Redis Queue  │
      │                 └──────────────┘
      │                       │
      │                       ▼
      │                 ┌──────────────┐
      │                 │    Worker    │  Timelapse generation
      │                 └──────────────┘
      │                       │
      │                       ▼
      │                 Generated videos
      │
      ▼
┌─────────────┐
│   Frontend  │  React UI @ localhost:3000
│   (React)   │
└─────────────┘

┌─────────────┐
│  Transfer   │  Syncs images Pi → Backend (every 5 min)
│  Service    │
└─────────────┘
```

### Services

| Service      | Technology   | Port | Purpose                                         |
| ------------ | ------------ | ---- | ----------------------------------------------- |
| **Backend**  | FastAPI      | 8082 | Scheduler, exposure calculator, orchestration   |
| **Worker**   | Python RQ    | -    | Background timelapse generation                 |
| **Redis**    | Redis        | 6379 | Job queue for worker tasks                      |
| **Frontend** | React + Vite | 3000 | Web UI, live preview, session monitoring        |
| **Transfer** | Python       | -    | Auto-sync images from Pi to backend every 5 min |
| **Pi**       | FastAPI      | 8080 | Camera control, hardware interface (runs on Pi) |

---

## Key Features

### 🎯 7 Capture Profiles (A-G)

Each schedule captures **all 7 profiles** for A/B testing:

- **Profile A**: Pure auto - ISO=0, auto WB, no bias
- **Profile B**: Daylight WB - Fixed 5500K for consistency
- **Profile C**: Conservative adaptive - Cooler baseline, highlight protection
- **Profile D**: Warm dramatic - Rich golden tones, adaptive WB
- **Profile E**: Balanced adaptive - Daylight when bright, natural warmth
- **Profile F**: Auto + spot metering - Mountain focus with +0.7 EV bias
- **Profile G**: Adaptive EV + balanced WB - Lux-based EV curves

**Production profiles** (always enabled): A, D, G

### 🗄️ Database-Driven Architecture

SQLite database tracks:

- **Sessions**: Schedule runs with start/end times, status, profile
- **Captures**: Individual photos with ISO, shutter, EV, lux, file paths
- **Metadata**: Complete settings history for every image

When a schedule ends, the system:

1. Detects state change (was_active=True → is_active=False)
2. Queries database for exact image list
3. Enqueues timelapse job in Redis
4. Worker downloads images and generates video

### ⏰ Flexible Scheduling

Configure in `backend/config.json`:

```json
{
  "schedules": {
    "sunrise": {
      "enabled": true,
      "offset_minutes": -30,      // Start 30min before sunrise
      "duration_minutes": 60,     // Run for 1 hour
      "interval_seconds": 2,      // Capture every 2 seconds
      "stack_images": true,       // Enable HDR stacking
      "stack_count": 5            // 5 images per stack
    },
    "sunset": { ... },
    "daytime": { ... }
  }
}
```

### 🎬 Automated Timelapse Generation

- **Queue-based processing**: Redis Queue (RQ) for reliable background jobs
- **Database queries**: Worker pulls exact image list from SQLite
- **Automatic download**: Images synced from Pi during job execution
- **Profile-based videos**: Separate timelapse for each profile (A, D, G, etc.)

---

## Quick Start

### Prerequisites

- **Raspberry Pi** with ArduCam IMX519 (for capture)
- **Docker** (for backend/frontend/worker)
- **Python 3.11+** (for Pi deployment)

### Development Setup

```bash
# Clone repository
git clone https://github.com/nicholasmparker/Skylapse.git
cd Skylapse

# Start all services
docker-compose up

# Services available:
# - Frontend: http://localhost:3000
# - Backend: http://localhost:8082
# - Worker: Background processing (check logs: docker-compose logs worker -f)
```

### Deploy to Raspberry Pi

```bash
# Deploy capture service to Pi
./scripts/deploy-pi.sh

# SSH to verify
ssh pi@helios.local
systemctl status skylapse-capture
```

### Deploy to Server

```bash
# Deploy backend/frontend/worker to production server
./scripts/deploy-server.sh
```

---

## How It Works

### 1. Schedule Execution

Backend scheduler loop (every 15-30 seconds):

1. Check current time against all schedules
2. If schedule active → capture all profiles (A-G) in parallel
3. Save settings + metadata to SQLite
4. Download images from Pi to backend storage
5. Track session state for end-detection

### 2. Exposure Calculation

For each profile:

1. **Get metering data**: Backend requests `GET /meter` from Pi (lux, suggested ISO/shutter)
2. **Calculate settings**: Apply profile logic (WB curves, EV compensation, adaptive settings)
3. **Send capture command**: `POST /capture` with exact settings
4. **Store metadata**: Save complete settings to database

### 3. Timelapse Generation

When schedule ends:

1. **End detection**: Scheduler detects `was_active=True, is_active=False`
2. **Query database**: Get all captures for session (by session_id)
3. **Enqueue job**: Add timelapse task to Redis queue
4. **Worker processes**: Download images, generate video with ffmpeg
5. **Save output**: Store timelapse in `data/videos/`

---

## Configuration

### Location & Timezone

Edit `backend/config.json`:

```json
{
  "location": {
    "latitude": 39.609573,
    "longitude": -105.314163,
    "timezone": "America/Denver",
    "name": "Colorado"
  }
}
```

### Pi Connection

```json
{
  "pi": {
    "host": "192.168.0.124", // Pi IP or hostname (helios.local)
    "port": 8080,
    "timeout_seconds": 10
  }
}
```

### Storage & Processing

```json
{
  "storage": {
    "images_dir": "data/images",
    "videos_dir": "data/videos",
    "max_days_to_keep": 7
  },
  "processing": {
    "video_fps": 24,
    "video_codec": "libx264",
    "video_quality": "23"
  }
}
```

---

## Docker Architecture

**⚠️ CRITICAL: This is a Docker application**

- ✅ **All services run in Docker** (backend, frontend, worker, redis, transfer)
- ✅ **One exception**: Pi capture service runs directly on Raspberry Pi (hardware access)
- ✅ **Development**: `docker-compose up` starts everything
- ✅ **Testing**: Playwright tests run against Docker containers

```bash
# Add npm package to frontend
docker-compose exec frontend npm install <package>

# Rebuild after dependency changes
docker-compose up --build frontend

# View logs
docker-compose logs -f backend
docker-compose logs -f worker

# Shell into container
docker-compose exec backend bash
```

See [`CLAUDE.md`](CLAUDE.md) for critical Docker workflow reminders.

---

## Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture and technical design
- **[DEPLOYMENT_AND_DOCKER.md](DEPLOYMENT_AND_DOCKER.md)** - Development workflow and deployment
- **[HARDWARE.md](HARDWARE.md)** - Raspberry Pi and camera setup
- **[TESTING.md](TESTING.md)** - Test strategy and Playwright tests
- **[CLAUDE.md](CLAUDE.md)** - AI agent instructions (Docker workflow)

### Archived Documentation

Historical docs from earlier development phases: [`docs/archive/`](docs/archive/)

---

## Project Status

✅ **Production-ready** - October 2025

**Implemented:**

- ✅ SQLite database with Sessions and Captures tables
- ✅ Redis Queue (RQ) for background timelapse generation
- ✅ Schedule-end detection triggering automatic video generation
- ✅ 7 capture profiles with A/B testing (A, D, G in production)
- ✅ Database-driven image tracking and retrieval
- ✅ Automated image download from Pi during captures
- ✅ Live camera preview in web UI
- ✅ Transfer service for Pi → Backend sync (every 5 min)

**Future enhancements:**

- Multi-camera coordination (3+ Pis)
- Profile deployment mode (network-independent Pi operation)
- Advanced image processing (HDR merge, alignment, color grading)
- Web UI for profile creation and editing

---

## Contributing

Pull requests welcome! Please:

1. Test with Docker (`docker-compose up`)
2. Run Playwright tests (`npx playwright test`)
3. Follow existing code style (black, isort, prettier via pre-commit hooks)

---

## License

MIT © Nicholas Parker

---

## Acknowledgments

Built with:

- [FastAPI](https://fastapi.tiangolo.com/) - Backend API framework
- [Picamera2](https://github.com/raspberrypi/picamera2) - Raspberry Pi camera interface
- [React](https://react.dev/) + [Vite](https://vitejs.dev/) - Frontend
- [Redis Queue (RQ)](https://python-rq.org/) - Background job processing
- [FFmpeg](https://ffmpeg.org/) - Video generation
