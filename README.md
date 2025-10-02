# Skylapse

**Automated timelapse photography system with intelligent exposure profiles and metadata tracking.**

## What This Does

Captures and generates beautiful timelapses automatically:

- 🌅 **Sunrise** - 2 second intervals, 1 hour duration
- ☀️ **Daytime** - Custom time windows
- 🌇 **Sunset** - 2 second intervals, 1 hour duration

Features multiple capture profiles (A-G) optimized for different lighting conditions. Production profiles (A, D, G) capture every session for comparison.

## Current Features

- **6 Capture Profiles** - Auto, Daylight WB, Conservative, Warm Dramatic, Balanced, Spot Metering
- **SQLite Database** - Session and capture metadata tracking
- **Automated Timelapses** - Schedule-end detection triggers background video generation
- **Image Stacking** - HDR bracket support (Profile D)
- **Live Preview** - Real-time camera feed in web UI
- **Background Processing** - Redis Queue workers handle video generation

## Architecture

Five components:

1. **Raspberry Pi** - Captures photos via ArduCam IMX519 (16MP)
2. **Backend** - Scheduler, exposure calculator, API server
3. **Worker** - Background job processor for timelapse generation
4. **Frontend** - React web UI for monitoring and control
5. **Transfer Service** - Automatic image sync from Pi to backend

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for complete technical details.

## Quick Start

**Requirements:**

- Raspberry Pi with camera (for capture)
- Docker (for backend/frontend development)

**Development:**

```bash
# Start all services
docker-compose up

# Frontend: http://localhost:3000
# Backend: http://localhost:8082
```

**Deploy:**

```bash
# Deploy capture service to Pi
./scripts/deploy-pi.sh

# Deploy backend/frontend
./scripts/deploy-server.sh
```

## Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture and technical design
- **[DEPLOYMENT_AND_DOCKER.md](DEPLOYMENT_AND_DOCKER.md)** - Development workflow and deployment
- **[HARDWARE.md](HARDWARE.md)** - Raspberry Pi and camera setup
- **[CLAUDE.md](CLAUDE.md)** - Critical reminders for AI agents (Docker workflow)
- **[TESTING.md](TESTING.md)** - Test strategy and Playwright tests

Historical documentation available in [`docs/archive/`](docs/archive/)

## Development Status

✅ **Production-ready** - Automated timelapse system with database tracking and background processing.

## License

MIT
