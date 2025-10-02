# Claude Code Memory - Skylapse Project

## 🚨 CRITICAL INFORMATION 🚨

**READ THIS FIRST. EVERY TIME.**

### Pi SSH Access

- **Username**: `nicholasmparker` (NOT `pi`)
- **Hostname**: `helios.local`
- **IP**: `192.168.0.124`
- **Use helper**: `./scripts/ssh-pi.sh` (recommended)

```bash
# ✅ CORRECT
ssh nicholasmparker@helios.local
./scripts/ssh-pi.sh "ls -l"

# ❌ WRONG - will fail
ssh pi@helios.local
```

## 🚨 CRITICAL: THIS IS A DOCKER APPLICATION 🚨

### Never Do These Things

- ❌ `npm install` or `npm run dev` on host
- ❌ `node` or `python` commands on host (except Pi deployment)
- ❌ Install packages locally
- ❌ Test against local servers

### Always Do These Things

- ✅ `docker-compose up frontend` → http://localhost:3000
- ✅ `docker-compose up backend` → http://localhost:8082
- ✅ `docker-compose up processing` → http://localhost:8081
- ✅ `docker-compose exec frontend npm install <package>` to add deps
- ✅ `docker-compose up --build` after dependency changes
- ✅ Run Playwright tests against Docker containers

### Three Environments

1. **Your Laptop (Dev)**: Everything in Docker except Pi code
2. **Raspberry Pi (Prod)**: Capture service runs directly (NOT Docker)
3. **Server (Prod)**: Backend/Frontend/Processing in Docker

### Deployment

```bash
# Deploy to Pi (capture service)
./scripts/deploy-pi.sh

# Deploy to server (backend/frontend)
./scripts/deploy-server.sh
```

### Quick Commands

```bash
# Development
docker-compose up                    # Start all services
docker-compose up --build frontend   # Rebuild frontend
docker-compose logs -f backend       # View logs
docker-compose exec backend bash     # Shell into container

# Testing
docker-compose up -d                 # Start in background
npx playwright test                  # Run tests against Docker

# Deployment
./scripts/deploy-pi.sh              # Deploy capture to Pi
./scripts/ssh-pi.sh                 # Access Pi (helper script)
ssh nicholasmparker@helios.local    # Access Pi (direct)
```

### Why Docker?

- **Consistency**: Same environment everywhere
- **Isolation**: No dependency conflicts
- **Hot reload**: Code changes auto-update in containers
- **Easy deployment**: Build once, run anywhere

### The One Exception

**Raspberry Pi capture service runs directly** (not Docker) because:

- Direct hardware access to camera is simpler
- Lower resource usage on Pi
- System service integration

See `DEPLOYMENT_AND_DOCKER.md` for complete details.

---

**🐳 DOCKER ALWAYS. NO EXCEPTIONS (except Pi). 🐳**
