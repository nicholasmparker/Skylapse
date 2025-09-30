# Skylapse

**Automatic sunrise, daytime, and sunset timelapses with smart exposure and image stacking.**

## What This Does

Three simple timelapses, captured automatically every day:
- 🌅 **Sunrise** - 30 second intervals, 1 hour duration
- ☀️ **Daytime** - 5 minute intervals, 6 hours duration
- 🌇 **Sunset** - 30 second intervals, 1 hour duration

Camera settings adjust automatically to light conditions. Sunrise and sunset images are stacked for higher quality.

## Architecture

Three components:
1. **Raspberry Pi** - Captures photos when commanded
2. **Backend** - Brain that schedules, calculates exposure, processes images
3. **Frontend** - Simple UI to watch today's timelapses

See [`SIMPLE_ARCHITECTURE.md`](SIMPLE_ARCHITECTURE.md) for complete details.

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

- **[SIMPLE_ARCHITECTURE.md](SIMPLE_ARCHITECTURE.md)** - System design and implementation plan
- **[DEPLOYMENT_AND_DOCKER.md](DEPLOYMENT_AND_DOCKER.md)** - Development workflow and deployment
- **[LESSONS_LEARNED.md](LESSONS_LEARNED.md)** - What went wrong and why we started over
- **[CLAUDE.md](CLAUDE.md)** - Critical reminders for AI agents (Docker workflow)

## Development Status

🚧 **Fresh start** - Old complex codebase archived, rebuilding with simplicity first.

See `../skylapse-archive/` for previous implementation.

## License

MIT