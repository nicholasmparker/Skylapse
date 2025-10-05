# Production Deployment Guide

## Prerequisites

- Docker and Docker Compose installed
- Access to the Raspberry Pi via SSH
- GitHub Container Registry access (images are public)

## Quick Setup (Recommended)

Run the automated setup script:

```bash
curl -fsSL https://raw.githubusercontent.com/nicholasmparker/skylapse/main/scripts/setup-production.sh | bash
```

This will:

- Create directory structure
- Prompt for configuration (Pi host, ports, etc.)
- Generate `.env` and `docker-compose.prod.yml`
- Create default `backend/config.json`
- Guide you through SSH setup
- Pull images and start services

**Or** follow the manual setup below for more control.

## Manual Setup

### 1. Create Directory Structure

```bash
mkdir -p skylapse && cd skylapse
mkdir -p data/images data/timelapses data/db backend
```

### 2. Download Required Files

```bash
curl -O https://raw.githubusercontent.com/nicholasmparker/skylapse/main/docker-compose.prod.yml
curl -o backend/config.json https://raw.githubusercontent.com/nicholasmparker/skylapse/main/backend/config.json
```

### 3. Configure Environment

Create a `.env` file in the project root:

```bash
# Pi Connection
PI_HOST=192.168.0.124
PI_PORT=8080
PI_USER=nicholasmparker

# Backend Configuration
BACKEND_PORT=8082
BACKEND_URL=http://your-server-ip:8082
BACKEND_NAME=production  # For Pi coordination (optional)

# Frontend Configuration
FRONTEND_PORT=3000
VITE_BACKEND_URL=http://your-server-ip:8082

# Transfer Service (pulls images from Pi)
TRANSFER_INTERVAL_MINUTES=5
DELETE_AFTER_DAYS=1

# Volume Paths (optional, defaults to ./data/*)
SKYLAPSE_IMAGES_PATH=/path/to/images
SKYLAPSE_TIMELAPSES_PATH=/path/to/timelapses
SKYLAPSE_DB_PATH=/path/to/db
```

### 3a. Multi-Backend Coordination (Development Setup)

If you're running multiple backends (e.g., production + development) against the same Pi:

**On Pi** - Set which backend is allowed to trigger captures:

```bash
# SSH to Pi
ssh nicholasmparker@192.168.0.124

# Edit systemd service
sudo nano /etc/systemd/system/skylapse-capture.service

# Add this line under [Service]:
Environment="PRIMARY_BACKEND=production"

# Restart service
sudo systemctl daemon-reload
sudo systemctl restart skylapse-capture
```

**On Backends**:

- Production: `BACKEND_NAME=production` (matches Pi config - can capture)
- Development: `BACKEND_NAME=dev` (doesn't match - captures will be rejected)

To switch control, change `PRIMARY_BACKEND` on Pi and restart the service.

**Note:** If `PRIMARY_BACKEND` is not set on Pi, all backends can trigger captures (backward compatible).

### 4. Set Up SSH Access to Pi

The transfer service needs SSH access to the Pi to pull images:

```bash
# Generate SSH key if you don't have one
ssh-keygen -t ed25519 -C "skylapse-transfer"

# Copy to Pi
ssh-copy-id nicholasmparker@192.168.0.124

# Test connection
ssh nicholasmparker@192.168.0.124 "ls ~/skylapse-images/"
```

### 5. Pull Images and Start Services

```bash
# Pull latest images
docker-compose -f docker-compose.prod.yml pull

# Start all services
docker-compose -f docker-compose.prod.yml up -d
```

### 6. Verify Deployment

```bash
# Check all services are running
docker-compose -f docker-compose.prod.yml ps

# Check backend health
curl http://localhost:8082/health

# Check backend status
curl http://localhost:8082/status

# View logs
docker-compose -f docker-compose.prod.yml logs -f
```

## Service Overview

The production stack includes:

- **Backend** (port 8082): API server, schedule management, database
- **Frontend** (port 3000): React UI for viewing captures and timelapses
- **Worker**: Background job processor for timelapse generation
- **Redis**: Job queue for worker
- **Transfer**: Automated image sync from Pi every 5 minutes

## Updating Deployment

When new images are pushed to `main` branch, GitHub Actions automatically builds multi-arch images.

To update your deployment:

```bash
# Pull latest images
docker-compose -f docker-compose.prod.yml pull

# Restart services
docker-compose -f docker-compose.prod.yml up -d

# Verify update
docker-compose -f docker-compose.prod.yml logs backend --tail 50
```

## Data Persistence

All data is stored in bind-mounted volumes:

- `data/images/` - Captured images transferred from Pi
- `data/timelapses/` - Generated timelapse videos
- `data/db/` - SQLite database with capture sessions and metadata

These directories persist across container restarts and updates.

## Monitoring

### View Logs

```bash
# All services
docker-compose -f docker-compose.prod.yml logs -f

# Specific service
docker-compose -f docker-compose.prod.yml logs backend -f

# Last 50 lines
docker-compose -f docker-compose.prod.yml logs backend --tail 50
```

### Check Active Schedules

```bash
curl http://localhost:8082/status | python3 -m json.tool
```

### Monitor Transfer Service

```bash
docker-compose -f docker-compose.prod.yml logs transfer -f
```

## Troubleshooting

### Backend can't connect to Pi

1. Verify Pi is running: `ssh nicholasmparker@192.168.0.124`
2. Check Pi capture service: `ssh nicholasmparker@192.168.0.124 "sudo systemctl status skylapse-capture"`
3. Test Pi API: `curl http://192.168.0.124:8080/health`

### Transfer service can't sync images

1. Verify SSH access: `ssh nicholasmparker@192.168.0.124 "ls ~/skylapse-images/"`
2. Check transfer logs: `docker-compose -f docker-compose.prod.yml logs transfer`
3. Ensure Pi source directory exists and has images

### Worker not processing timelapse jobs

1. Check worker logs: `docker-compose -f docker-compose.prod.yml logs worker`
2. Verify Redis connection: `docker-compose -f docker-compose.prod.yml logs redis`
3. Check queue status: `curl http://localhost:8082/timelapses`

### Frontend can't reach backend

1. Verify `VITE_BACKEND_URL` environment variable is set correctly
2. Check CORS settings if accessing from different host
3. Verify backend is running: `curl http://localhost:8082/health`

## Architecture

```
┌─────────────────┐
│  Raspberry Pi   │
│  (Capture)      │◄──── Triggers captures
│  Port 8080      │      (Backend polls Pi)
└────────┬────────┘
         │
         │ SSH/rsync (Transfer service pulls images every 5 min)
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│  Production Server                                       │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌────────┐  ┌──────────┐ │
│  │ Backend  │  │ Frontend │  │ Worker │  │  Redis   │ │
│  │  :8082   │  │  :3000   │  │        │  │  :6379   │ │
│  └────┬─────┘  └────┬─────┘  └───┬────┘  └────┬─────┘ │
│       │             │            │            │        │
│       └─────────────┴────────────┴────────────┘        │
│                      │                                  │
│               ┌──────▼──────┐                          │
│               │   Volumes   │                          │
│               │  images/    │                          │
│               │  timelapses/│                          │
│               │  db/        │                          │
│               └─────────────┘                          │
└─────────────────────────────────────────────────────────┘
```

## Backup Recommendations

### Database Backup

```bash
# Backup SQLite database
sqlite3 data/db/skylapse.db ".backup data/db/skylapse_backup_$(date +%Y%m%d).db"
```

### Image Backup

```bash
# Sync to external storage
rsync -avz data/images/ /path/to/backup/images/
rsync -avz data/timelapses/ /path/to/backup/timelapses/
```

## Security Considerations

- Change default `PI_HOST` and `PI_PORT` in `.env`
- Use firewall rules to restrict access to ports 8082 and 3000
- Keep SSH keys secure with proper permissions (600)
- Regularly update Docker images with `docker-compose pull`
- Consider using reverse proxy (nginx/traefik) for SSL/TLS

## Performance Tuning

### Worker Memory Limit

Large timelapse generation can use significant RAM. Adjust in `docker-compose.prod.yml`:

```yaml
worker:
  deploy:
    resources:
      limits:
        memory: 4G # Increase if needed
```

### Transfer Interval

Adjust image sync frequency in `.env`:

```bash
TRANSFER_INTERVAL_MINUTES=5  # Reduce for more frequent syncing
```

### Image Retention

Control how long images stay on Pi after transfer:

```bash
DELETE_AFTER_DAYS=1  # Increase to keep images longer on Pi
```
