# Deployment & Docker Workflow

## Critical Rule #1: THIS IS A DOCKER APPLICATION

**NEVER run `npm install`, `npm run dev`, or `node` commands directly.**

All development happens inside Docker containers.

---

## The Three Environments

### 1. Your Laptop (Development)
- **Backend**: `docker-compose up backend` → http://localhost:8082
- **Frontend**: `docker-compose up frontend` → http://localhost:3000
- **Processing**: `docker-compose up processing` → http://localhost:8081

### 2. Raspberry Pi (Production)
- **Capture Service**: Runs directly on Pi (not Docker) at `helios.local:8080`
- Access via SSH: `ssh pi@helios.local`

### 3. Backend Server (Production - if separate)
- **Backend + Processing**: Docker containers on server
- **Frontend**: Docker container on server

---

## Docker Compose Architecture

```yaml
# docker-compose.yml
services:
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    volumes:
      - ./frontend/src:/app/src  # Live reload during dev
    environment:
      - VITE_BACKEND_URL=http://localhost:8082
      - VITE_PROCESSING_URL=http://localhost:8081

  backend:
    build: ./backend
    ports:
      - "8082:8082"
    volumes:
      - ./backend/src:/app/src
      - ./backend/data:/app/data  # Persistent storage
    environment:
      - PI_HOST=helios.local
      - PI_PORT=8080

  processing:
    build: ./processing
    ports:
      - "8081:8081"
    volumes:
      - ./processing/src:/app/src
      - ./backend/data:/app/data  # Shared image storage
```

---

## Development Workflow

### Starting Development
```bash
# Start all services
docker-compose up

# Or start individually
docker-compose up frontend
docker-compose up backend
docker-compose up processing

# Rebuild after dependency changes
docker-compose up --build frontend
```

### Making Code Changes
- Edit files in `./frontend/src`, `./backend/src`, `./processing/src`
- Changes auto-reload thanks to volume mounts
- **NO need to restart containers** (except for config changes)

### Installing New Dependencies

**Frontend** (add npm package):
```bash
# DON'T DO: npm install <package>
# DO THIS:
docker-compose exec frontend npm install <package>

# Then rebuild
docker-compose up --build frontend
```

**Backend/Processing** (add Python package):
```bash
# Update requirements.txt
echo "new-package==1.0.0" >> backend/requirements.txt

# Rebuild
docker-compose up --build backend
```

### Running Tests

**Frontend tests**:
```bash
# Playwright tests MUST run against Docker containers
docker-compose up frontend backend processing -d
npx playwright test
```

**Backend tests**:
```bash
docker-compose exec backend pytest
```

---

## Raspberry Pi Deployment

### Why NOT Docker on Pi?
- Hardware access (camera) is simpler without Docker
- Lower resource usage
- Direct system integration

### Deployment Script
```bash
#!/bin/bash
# scripts/deploy-pi.sh

# Build on laptop (faster)
cd pi
zip -r capture-service.zip . -x "*.pyc" -x "__pycache__/*"

# Transfer to Pi
scp capture-service.zip pi@helios.local:/home/pi/

# SSH and deploy
ssh pi@helios.local << 'EOF'
  cd /home/pi
  unzip -o capture-service.zip -d capture-service
  cd capture-service

  # Install dependencies
  pip3 install -r requirements.txt

  # Restart service
  sudo systemctl restart capture-service
EOF

echo "✅ Deployed to Raspberry Pi"
```

### Pi Service Setup (One-time)
```bash
# On the Pi
sudo nano /etc/systemd/system/capture-service.service
```

```ini
[Unit]
Description=Skylapse Capture Service
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/capture-service
ExecStart=/usr/bin/python3 main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable capture-service
sudo systemctl start capture-service
```

---

## Backend/Frontend Deployment

### Option 1: Docker Compose on Server (Simplest)

```bash
# scripts/deploy-server.sh

# Copy entire project to server
rsync -avz --exclude 'node_modules' --exclude '__pycache__' \
  ./ user@server:/home/user/skylapse/

# SSH and deploy
ssh user@server << 'EOF'
  cd /home/user/skylapse
  docker-compose down
  docker-compose up -d --build
EOF

echo "✅ Deployed to server"
```

### Option 2: Individual Container Deployment

```bash
# Build and push to registry
docker build -t skylapse-frontend:latest ./frontend
docker push skylapse-frontend:latest

docker build -t skylapse-backend:latest ./backend
docker push skylapse-backend:latest

# On server: pull and run
ssh user@server << 'EOF'
  docker pull skylapse-frontend:latest
  docker pull skylapse-backend:latest
  docker-compose up -d
EOF
```

---

## Environment Configuration

### Development (.env.development)
```bash
# Backend
PI_HOST=helios.local
PI_PORT=8080
DATA_DIR=/app/data

# Frontend
VITE_BACKEND_URL=http://localhost:8082
VITE_PROCESSING_URL=http://localhost:8081
```

### Production (.env.production)
```bash
# Backend
PI_HOST=helios.local
PI_PORT=8080
DATA_DIR=/data

# Frontend
VITE_BACKEND_URL=https://api.skylapse.com
VITE_PROCESSING_URL=https://processing.skylapse.com
```

---

## Common Mistakes & Fixes

### ❌ Mistake: Running `npm run dev` locally
```bash
# DON'T DO THIS
cd frontend
npm run dev  # ❌ Wrong!
```

### ✅ Fix: Use Docker
```bash
docker-compose up frontend  # ✅ Correct!
```

---

### ❌ Mistake: Installing packages locally
```bash
cd frontend
npm install react-query  # ❌ Wrong!
```

### ✅ Fix: Install inside container
```bash
docker-compose exec frontend npm install react-query  # ✅ Correct!
docker-compose up --build frontend  # Rebuild
```

---

### ❌ Mistake: Forgetting to rebuild after dependency changes
```bash
# Added new package to requirements.txt
docker-compose up backend  # ❌ Won't see new package!
```

### ✅ Fix: Rebuild
```bash
docker-compose up --build backend  # ✅ Correct!
```

---

### ❌ Mistake: Testing against local dev server
```bash
npm run dev &  # Started outside Docker
npx playwright test  # ❌ Testing wrong thing!
```

### ✅ Fix: Test against Docker
```bash
docker-compose up -d  # Start Docker services
npx playwright test  # ✅ Testing actual containers!
```

---

## Quick Reference

### Daily Development Commands
```bash
# Start everything
docker-compose up

# Start with rebuild
docker-compose up --build

# Stop everything
docker-compose down

# View logs
docker-compose logs -f frontend
docker-compose logs -f backend

# Shell into container
docker-compose exec frontend sh
docker-compose exec backend bash

# Restart single service
docker-compose restart backend
```

### Deployment Commands
```bash
# Deploy to Pi
./scripts/deploy-pi.sh

# Deploy to server
./scripts/deploy-server.sh

# Check Pi status
ssh pi@helios.local "systemctl status capture-service"

# View Pi logs
ssh pi@helios.local "journalctl -u capture-service -f"
```

---

## File Structure

```
skylapse/
├── docker-compose.yml           # Orchestrates all services
├── .env.development             # Dev environment vars
├── .env.production              # Prod environment vars
│
├── frontend/
│   ├── Dockerfile               # Frontend container config
│   ├── package.json
│   └── src/                     # Hot-reloads in Docker
│
├── backend/
│   ├── Dockerfile               # Backend container config
│   ├── requirements.txt
│   ├── src/                     # Hot-reloads in Docker
│   └── data/                    # Persistent storage (volume mount)
│
├── processing/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── src/
│
├── pi/
│   ├── main.py                  # Runs directly on Pi (no Docker)
│   ├── camera.py
│   └── requirements.txt
│
└── scripts/
    ├── deploy-pi.sh             # Deploy capture service to Pi
    └── deploy-server.sh         # Deploy backend/frontend to server
```

---

## How to Remember Docker

### Add to CLAUDE.md (Project Instructions)
```markdown
# 🐳 THIS IS A DOCKER APPLICATION

**ALWAYS use Docker for development and deployment:**
- Frontend: `docker-compose up frontend`
- Backend: `docker-compose up backend`
- Processing: `docker-compose up processing`

**NEVER run npm/node/python commands directly on host.**

**Tests run against Docker containers at localhost:3000**
```

### Pre-commit Hook Reminder
```bash
# .git/hooks/pre-commit
#!/bin/bash

if docker-compose ps | grep -q "frontend.*Up"; then
  echo "✅ Docker containers are running"
else
  echo "⚠️  Docker containers not running!"
  echo "   Run: docker-compose up -d"
  exit 1
fi
```

### VS Code Settings
```json
// .vscode/settings.json
{
  "files.exclude": {
    "**/node_modules": true
  },
  "search.exclude": {
    "**/node_modules": true
  },
  "tasks.version": "2.0.0",
  "tasks.tasks": [
    {
      "label": "Start Docker Services",
      "type": "shell",
      "command": "docker-compose up -d",
      "problemMatcher": []
    }
  ]
}
```

### Shell Aliases
```bash
# Add to ~/.bashrc or ~/.zshrc
alias dcup='docker-compose up'
alias dcdown='docker-compose down'
alias dcbuild='docker-compose up --build'
alias dclogs='docker-compose logs -f'
alias deploy-pi='./scripts/deploy-pi.sh'
alias deploy-server='./scripts/deploy-server.sh'
```

---

## Deployment Checklist

### Before Deploying to Pi
- [ ] Test capture endpoint locally
- [ ] Verify camera hardware access works
- [ ] Check systemd service config
- [ ] Test manual capture on Pi

### Before Deploying Backend/Frontend
- [ ] Run all tests with Docker services
- [ ] Check environment variables
- [ ] Verify volume mounts for data persistence
- [ ] Test Pi → Backend → Frontend flow
- [ ] Confirm image storage paths

### After Deployment
- [ ] Check all services are running (`docker-compose ps`)
- [ ] Verify logs have no errors (`docker-compose logs`)
- [ ] Test capture from frontend
- [ ] Confirm images saved to correct location
- [ ] Check video generation works

---

## Success Metrics

**You're doing it right when:**
- ✅ You never type `npm install` or `npm run dev` on host
- ✅ All tests pass against Docker containers
- ✅ Pi deployment takes < 2 minutes
- ✅ Server deployment takes < 5 minutes
- ✅ You can develop without thinking about Docker

**You're doing it wrong when:**
- ❌ You install packages locally
- ❌ Tests fail because wrong URL
- ❌ "Works on my machine" but not in Docker
- ❌ Deployment is manual and error-prone

---

## Next: Update CLAUDE.md

Add this to the top of `CLAUDE.md`:

```markdown
# 🐳 CRITICAL: THIS IS A DOCKER APPLICATION

**ALL development happens in Docker containers.**

- Frontend: `docker-compose up frontend` → http://localhost:3000
- Backend: `docker-compose up backend` → http://localhost:8082
- Processing: `docker-compose up processing` → http://localhost:8081

**NEVER** run `npm`, `node`, or `python` commands on host.
**ALWAYS** use `docker-compose exec` for container commands.

Tests run against Docker containers. Deploy with scripts:
- Pi: `./scripts/deploy-pi.sh`
- Server: `./scripts/deploy-server.sh`
```