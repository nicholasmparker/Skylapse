# Skylapse Production Deployment Guide

Complete guide for deploying Skylapse to production servers and Raspberry Pi.

## Quick Start

### Deploy to dagon.local (Primary Server)

```bash
# On dagon.local
ssh nicholasmparker@dagon.local
mkdir -p ~/skylapse && cd ~/skylapse

# Download setup script and run
curl -fsSL https://raw.githubusercontent.com/nicholasmparker/skylapse/main/setup.sh | bash
```

When prompted:
- **Pi hostname**: `helios.local` (or `192.168.0.124`)
- **Server IP**: `192.168.0.51` (dagon's IP)
- **Backend name**: `dagon` (IMPORTANT: This must match what you deploy to Pi!)

### Deploy to Raspberry Pi

```bash
# From your laptop (with repo cloned)
cd ~/Projects/skylapse
./scripts/deploy-capture.sh helios.local nicholasmparker dagon
```

**CRITICAL**: The third parameter `dagon` must match the `BACKEND_NAME` in dagon's `.env` file!

---

## Architecture Overview

```
┌─────────────────┐
│  Raspberry Pi   │  Camera capture service
│  (helios.local) │  Port 8080
└────────┬────────┘
         │ Triggered captures
         │ Image storage: ~/skylapse-images/
         │
         ▼
┌─────────────────┐
│  Server (dagon) │  Backend, Frontend, Worker, Redis, Transfer
│  192.168.0.51   │  Ports: 8082 (backend), 3000 (frontend), 6379 (redis)
└─────────────────┘
         │ SSH transfer every 5 minutes
         │ Images: /data/images/
         │ Timelapses: /data/timelapses/
```

## Components

### Server Services (Docker)
- **Backend** (port 8082): Scheduler, API, capture coordination
- **Frontend** (port 3000): Web UI for monitoring and timelapse generation
- **Worker**: Background timelapse processing (RQ)
- **Redis** (port 6379): Task queue
- **Transfer**: SSH-based image sync from Pi every 5 minutes

### Raspberry Pi Service (systemd)
- **Capture Service** (port 8080): Camera control and image capture
- Runs directly on Pi (not Docker) for camera access
- Stores images in `~/skylapse-images/`

---

## Detailed Setup Instructions

### 1. Server Setup (dagon.local)

#### Initial Setup

```bash
ssh nicholasmparker@dagon.local
mkdir -p ~/skylapse && cd ~/skylapse

# Run setup script (interactive)
curl -fsSL https://raw.githubusercontent.com/nicholasmparker/skylapse/main/setup.sh | bash
```

The setup script will:
1. Create directory structure (`data/images`, `data/timelapses`, `data/db`, `backend`)
2. Prompt for configuration (Pi host, ports, server IP)
3. Create `.env` file with your settings
4. Download `docker-compose.prod.yml`
5. Create default `backend/config.json`
6. Guide you through SSH key setup
7. Pull and start Docker containers

#### Configuration Values

When running the setup script, use these values for dagon:

```
Pi hostname: helios.local (or 192.168.0.124)
Pi port: 8080
Pi SSH username: nicholasmparker
Pi source directory: ~/skylapse-images/
Backend port: 8082
Frontend port: 3000
Server IP: 192.168.0.51 (dagon's IP - use IP, not hostname, for frontend access)
Transfer interval: 5 (minutes)
Delete after: 1 (days)
```

#### Manual Configuration (Optional)

If you prefer to configure manually instead of using the setup script:

**Create `.env` file:**
```bash
cat > .env <<EOF
# Pi Connection
PI_HOST=helios.local
PI_PORT=8080
PI_USER=nicholasmparker
PI_SOURCE=~/skylapse-images/

# Backend Configuration
BACKEND_PORT=8082
BACKEND_URL=http://192.168.0.51:8082
BACKEND_NAME=dagon

# Frontend Configuration
FRONTEND_PORT=3000
VITE_BACKEND_URL=http://192.168.0.51:8082

# Transfer Service
TRANSFER_INTERVAL_MINUTES=5
DELETE_AFTER_DAYS=1
EOF
```

**Download files:**
```bash
curl -O https://raw.githubusercontent.com/nicholasmparker/skylapse/main/docker-compose.prod.yml
mkdir -p backend
curl -o backend/config.json https://raw.githubusercontent.com/nicholasmparker/skylapse/main/backend/config.json
```

#### SSH Setup for Transfer Service

The transfer service needs passwordless SSH access to pull images from the Pi:

```bash
# Generate SSH key if you don't have one
ssh-keygen -t ed25519 -C "skylapse-transfer"

# Copy key to Pi
ssh-copy-id nicholasmparker@helios.local

# Test connection
ssh nicholasmparker@helios.local 'ls ~/skylapse-images'
```

#### Start Services

```bash
# Pull latest images
docker-compose -f docker-compose.prod.yml pull

# Start all services
docker-compose -f docker-compose.prod.yml up -d

# Check status
docker-compose -f docker-compose.prod.yml ps
```

#### Verify Deployment

```bash
# Check backend health
curl http://localhost:8082/health

# Check status
curl http://localhost:8082/status

# View logs
docker-compose -f docker-compose.prod.yml logs -f backend
```

Access points:
- Frontend: http://192.168.0.51:3000
- Backend API: http://192.168.0.51:8082
- Backend Health: http://192.168.0.51:8082/health
- Backend Status: http://192.168.0.51:8082/status

### 2. Raspberry Pi Setup

#### Deploy Capture Service

From your development machine (with the repo cloned):

```bash
cd ~/Projects/skylapse
./scripts/deploy-capture.sh helios.local nicholasmparker dagon
```

**CRITICAL**: The third parameter is the `PRIMARY_BACKEND` name. It MUST match the `BACKEND_NAME` in your server's `.env` file!

The script will:
1. Check Pi connectivity
2. Copy capture service code to Pi
3. Install dependencies (picamera2, FastAPI, etc.)
4. Configure GPU memory for full resolution captures (may require reboot)
5. Create systemd service with `PRIMARY_BACKEND=dagon`
6. Start the service

#### Verify Pi Deployment

```bash
# Check service status
ssh nicholasmparker@helios.local 'sudo systemctl status skylapse-capture'

# View logs
ssh nicholasmparker@helios.local 'sudo journalctl -u skylapse-capture -f'

# Test capture endpoint
curl http://helios.local:8080/status
```

#### GPU Reboot (if needed)

If the deployment script indicates a reboot is required:

```bash
ssh nicholasmparker@helios.local 'sudo reboot'
```

Wait ~30 seconds, then verify:
```bash
curl http://helios.local:8080/status
```

---

## Backend Coordination

The Pi only accepts capture commands from the configured `PRIMARY_BACKEND`. This prevents multiple backends from conflicting.

**How it works:**

1. **Server side** (dagon): Set `BACKEND_NAME=dagon` in `.env`
2. **Pi side** (helios): Deploy with `PRIMARY_BACKEND=dagon`
3. **Authorization**: Pi checks that incoming `backend_name` matches `PRIMARY_BACKEND`

**Example:**
```bash
# Server .env
BACKEND_NAME=dagon

# Pi deployment
./scripts/deploy-capture.sh helios.local nicholasmparker dagon

# Pi service env
Environment="PRIMARY_BACKEND=dagon"
```

If backends don't match, you'll see:
```
❌ Backend not authorized: only 'dagon' can trigger captures
```

### Switching Primary Backend

To switch from one backend to another:

```bash
# Deploy to Pi with new backend name
./scripts/deploy-capture.sh helios.local nicholasmparker new-backend-name

# Update server .env
# Change BACKEND_NAME=new-backend-name

# Restart server backend
docker-compose -f docker-compose.prod.yml restart backend
```

---

## Configuration Files

### Server: `.env`

Created by setup script or manually. Controls all Docker services.

Key variables:
- `BACKEND_NAME`: Name of this backend (e.g., "dagon", "production")
- `PI_HOST`: Pi hostname or IP
- `BACKEND_URL`: Full URL for backend API (used by backend itself)
- `VITE_BACKEND_URL`: Full URL for frontend to connect to backend

### Server: `backend/config.json`

Schedules, location, and Pi connection settings.

```json
{
  "schedules": {
    "sunrise": {
      "enabled": true,
      "type": "solar_relative",
      "anchor": "sunrise",
      "offset_minutes": -30,
      "duration_minutes": 60,
      "interval_seconds": 5,
      "profile": "D"
    },
    "sunset": {
      "enabled": true,
      "type": "solar_relative",
      "anchor": "sunset",
      "offset_minutes": -30,
      "duration_minutes": 60,
      "interval_seconds": 5,
      "profile": "D"
    },
    "all_day": {
      "enabled": true,
      "type": "time_of_day",
      "start_time": "06:30",
      "end_time": "21:30",
      "interval_seconds": 5,
      "profile": "A"
    }
  },
  "location": {
    "latitude": 39.6333,
    "longitude": -105.3167,
    "timezone": "America/Denver"
  },
  "pi": {
    "host": "192.168.0.124",
    "port": 8080,
    "timeout_seconds": 10
  }
}
```

**Update location** for accurate sunrise/sunset times.

**After editing**, restart backend:
```bash
docker-compose -f docker-compose.prod.yml restart backend
```

### Pi: systemd service

Located at `/etc/systemd/system/skylapse-capture.service`

Contains:
```
Environment="PRIMARY_BACKEND=dagon"
```

---

## Common Operations

### View Logs

```bash
# All services
docker-compose -f docker-compose.prod.yml logs -f

# Specific service
docker-compose -f docker-compose.prod.yml logs -f backend
docker-compose -f docker-compose.prod.yml logs -f transfer
docker-compose -f docker-compose.prod.yml logs -f worker

# Pi logs
ssh nicholasmparker@helios.local 'sudo journalctl -u skylapse-capture -f'
```

### Restart Services

```bash
# Restart all
docker-compose -f docker-compose.prod.yml restart

# Restart specific service
docker-compose -f docker-compose.prod.yml restart backend

# Restart Pi service
ssh nicholasmparker@helios.local 'sudo systemctl restart skylapse-capture'
```

### Update Deployment

```bash
# On server (dagon)
cd ~/skylapse
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d

# On Pi
cd ~/Projects/skylapse  # On your laptop
./scripts/deploy-capture.sh helios.local nicholasmparker dagon
```

### Stop Services

```bash
# Server
docker-compose -f docker-compose.prod.yml down

# Pi
ssh nicholasmparker@helios.local 'sudo systemctl stop skylapse-capture'
```

### Check Image Transfer

```bash
# On server
ls -lh ~/skylapse/data/images/
docker-compose -f docker-compose.prod.yml logs transfer

# On Pi
ssh nicholasmparker@helios.local 'ls -lh ~/skylapse-images/'
```

---

## Troubleshooting

### Backend not triggering captures

**Symptoms:** Backend scheduler runs, but no captures happen

**Check:**
1. Pi service is running: `ssh helios 'sudo systemctl status skylapse-capture'`
2. Backend can reach Pi: `curl http://helios.local:8080/status`
3. Backend name matches: Check `.env` `BACKEND_NAME` vs Pi `PRIMARY_BACKEND`

**Solution:**
```bash
# Verify backend name in .env
cat .env | grep BACKEND_NAME

# Verify Pi PRIMARY_BACKEND
ssh helios.local 'sudo systemctl show skylapse-capture | grep PRIMARY_BACKEND'

# If they don't match, redeploy to Pi
./scripts/deploy-capture.sh helios.local nicholasmparker dagon
```

### Images not transferring

**Symptoms:** Pi is capturing but images aren't showing up on server

**Check:**
1. Transfer service logs: `docker-compose -f docker-compose.prod.yml logs transfer`
2. SSH access: `ssh nicholasmparker@helios.local 'ls ~/skylapse-images'`
3. Disk space on server: `df -h`

**Common issues:**
- SSH key not set up: `ssh-copy-id nicholasmparker@helios.local`
- Wrong path: Check `PI_SOURCE` in `.env` matches actual Pi image directory
- Network issues: Check Pi is reachable

### Frontend can't connect to backend

**Symptoms:** Frontend loads but shows "Cannot connect to backend"

**Check:**
1. Backend is running: `curl http://192.168.0.51:8082/health`
2. CORS is configured: Backend logs should show no CORS errors
3. `VITE_BACKEND_URL` in `.env` is correct

**Solution:**
```bash
# Verify VITE_BACKEND_URL
cat .env | grep VITE_BACKEND_URL

# Should be: http://192.168.0.51:8082
# NOT: http://localhost:8082

# If wrong, update .env and restart
docker-compose -f docker-compose.prod.yml restart frontend
```

### Pi camera not working

**Symptoms:** Pi service starts but captures fail with camera errors

**Check:**
1. GPU memory: `ssh helios.local 'vcgencmd get_mem gpu'` should show ≥256MB
2. Camera detected: `ssh helios.local 'libcamera-hello --list-cameras'`
3. Pi logs: `ssh helios.local 'sudo journalctl -u skylapse-capture -f'`

**Solution for GPU memory:**
```bash
# Should show 256MB or more
ssh helios.local 'vcgencmd get_mem gpu'

# If less, reboot required after deploy-capture.sh sets it
ssh helios.local 'sudo reboot'
```

---

## Multiple Environments

You can run multiple backends (dev, staging, production) but **only one can be primary**.

### Example: Dev on laptop, Production on dagon

**Laptop (dev backend):**
```bash
# .env
BACKEND_NAME=dev
# Don't set as PRIMARY_BACKEND on Pi
```

**dagon (production backend):**
```bash
# .env
BACKEND_NAME=dagon

# Deploy to Pi as primary
./scripts/deploy-capture.sh helios.local nicholasmparker dagon
```

The Pi will only accept captures from `dagon`. Your laptop's dev backend can read status but can't trigger captures.

---

## Security Notes

- **SSH keys**: Transfer service needs read-only access to Pi images
- **No authentication**: Backend API has no auth (use firewall/VPN for production)
- **CORS**: Frontend allows all origins for local network access

---

## Reference

### Environment Variables

| Variable | Example | Description |
|----------|---------|-------------|
| `PI_HOST` | `helios.local` | Pi hostname or IP |
| `PI_PORT` | `8080` | Pi capture service port |
| `PI_USER` | `nicholasmparker` | SSH user for transfer |
| `PI_SOURCE` | `~/skylapse-images/` | Image directory on Pi |
| `BACKEND_PORT` | `8082` | Backend API port |
| `BACKEND_URL` | `http://192.168.0.51:8082` | Backend URL (for backend itself) |
| `BACKEND_NAME` | `dagon` | Name of this backend instance |
| `FRONTEND_PORT` | `3000` | Frontend port |
| `VITE_BACKEND_URL` | `http://192.168.0.51:8082` | Backend URL (for frontend) |
| `TRANSFER_INTERVAL_MINUTES` | `5` | Transfer interval |
| `DELETE_AFTER_DAYS` | `1` | Keep images on Pi for N days |

### Docker Services

| Service | Port | Description |
|---------|------|-------------|
| backend | 8082 | API, scheduler, capture coordination |
| frontend | 3000 | Web UI |
| worker | - | Background timelapse processing |
| redis | 6379 | Task queue |
| transfer | - | SSH sync from Pi |

### Useful Commands

```bash
# Server status
curl http://192.168.0.51:8082/status | jq

# Pi status
curl http://helios.local:8080/status | jq

# Trigger manual capture (for testing)
curl -X POST http://helios.local:8080/capture \
  -H "Content-Type: application/json" \
  -d '{"profile": "A", "backend_name": "dagon"}'

# Check schedule
curl http://192.168.0.51:8082/status | jq .active_schedules

# View images
ls -lh ~/skylapse/data/images/profile-a/ | tail -20
```
