# AI Assistant Guide - Skylapse Project

**Critical information for AI agents working on this project.**

---

## 🚨 CRITICAL: SSH & Pi Access

**Pi Username**: `nicholasmparker` (NOT `pi`)
**Pi Hostname**: `helios.local`
**Pi IP**: `192.168.0.124`

### Correct SSH Commands

```bash
# SSH into Pi
ssh nicholasmparker@helios.local

# Run command on Pi
ssh nicholasmparker@helios.local "command here"

# Copy files to Pi
scp file.txt nicholasmparker@helios.local:~/path/

# Use the helper script (recommended)
./scripts/ssh-pi.sh "command here"
```

### Wrong Commands (DO NOT USE)

```bash
# ❌ WRONG - will fail
ssh pi@helios.local

# ❌ WRONG - will fail
ssh pi@192.168.0.124
```

---

## 📁 Important File Paths

### On Pi (helios.local)

```bash
# Images
~/skylapse-images/profile-{a,b,c,d,e,f,g}/

# Service logs
journalctl -u skylapse-capture -f

# Service control
sudo systemctl status skylapse-capture
sudo systemctl restart skylapse-capture
```

### On Development Machine (Docker)

```bash
# Images (downloaded from Pi)
data/images/profile-{a,b,c,d,e,f,g}/

# Videos (generated timelapses)
data/videos/

# Database
data/db/skylapse.db

# Config
backend/config.json
```

---

## 🐳 Docker Workflow

**ALWAYS use Docker for development - NEVER run node/python/npm directly on host.**

```bash
# Start services
docker-compose up

# View logs
docker-compose logs -f backend
docker-compose logs -f worker

# Shell into container
docker-compose exec backend bash

# Add npm package to frontend
docker-compose exec frontend npm install <package>

# Rebuild after dependencies change
docker-compose up --build frontend
```

---

## 🌅 Sunrise/Sunset Schedule

### Current Schedule Configuration

From `backend/config.json`:

```json
{
  "schedules": {
    "sunrise": {
      "enabled": true,
      "offset_minutes": -30, // Start 30min before sunrise
      "duration_minutes": 60, // Run for 1 hour
      "interval_seconds": 2 // Capture every 2 seconds
    },
    "sunset": {
      "enabled": true,
      "offset_minutes": -30,
      "duration_minutes": 60,
      "interval_seconds": 2
    }
  }
}
```

### How It Works

1. **Backend calculates** sunrise/sunset times daily based on location
2. **Scheduler checks** every 2 seconds if schedule should be active
3. **When active**: Captures all 3 production profiles (A, D, G) in parallel
4. **When ends**: Detects state change and enqueues timelapse job
5. **Worker processes**: Downloads images and generates videos

### Checking if Schedule Ran

```bash
# Check backend logs for sunrise activity
docker-compose logs backend --since 12h | grep sunrise

# Check if images were captured this morning (06:29-07:29 local time)
ssh nicholasmparker@helios.local "ls -lh ~/skylapse-images/profile-a/ | grep 'Oct  2 0[67]:'"

# Check database for sessions
docker-compose exec backend python3 -c "
from database import SessionDatabase
import sqlite3
conn = sqlite3.connect('/data/db/skylapse.db')
cursor = conn.execute('SELECT * FROM sessions WHERE date(start_time, \"unixepoch\", \"localtime\") = date(\"now\", \"localtime\")')
for row in cursor: print(row)
"
```

---

## 🎨 Production Profiles

**Always enabled for A/B testing:**

- **Profile A**: Pure auto (ISO=0, no bias) - Baseline
- **Profile D**: Warm dramatic (adaptive WB) - Rich colors
- **Profile G**: Adaptive EV + balanced WB - Prevents overexposure

All other profiles (B, C, E, F) are experimental/testing only.

---

## 🔍 Debugging Common Issues

### Sunrise Didn't Capture

1. **Check backend container was running**:

   ```bash
   docker-compose ps backend
   ```

2. **Check logs for sunrise window**:

   ```bash
   docker-compose logs backend --since 12h | grep -E "(sunrise.*active|Capturing)"
   ```

3. **Verify schedule is enabled**:

   ```bash
   cat backend/config.json | grep -A 10 sunrise
   ```

4. **Check Pi connectivity**:
   ```bash
   curl http://192.168.0.124:8080/health
   ```

### No Timelapses Generated

1. **Check worker logs**:

   ```bash
   docker-compose logs worker --since 6h
   ```

2. **Check Redis queue**:

   ```bash
   docker-compose exec backend python3 -c "
   from redis import Redis
   from rq import Queue
   redis_conn = Redis.from_url('redis://redis:6379')
   q = Queue('timelapse', connection=redis_conn)
   print(f'Jobs in queue: {len(q)}')
   print(f'Failed jobs: {len(q.failed_job_registry)}')
   "
   ```

3. **Check if session ended properly**:
   ```bash
   docker-compose logs backend | grep "Schedule ended"
   ```

---

## 🚀 Deployment

### Deploy to Pi

```bash
# From project root
./scripts/deploy-pi.sh

# Or manually
cd pi
ssh nicholasmparker@helios.local "mkdir -p ~/skylapse-capture"
scp *.py requirements.txt nicholasmparker@helios.local:~/skylapse-capture/
ssh nicholasmparker@helios.local "cd ~/skylapse-capture && pip3 install -r requirements.txt"
ssh nicholasmparker@helios.local "sudo systemctl restart skylapse-capture"
```

### Check Deployment

```bash
# SSH and check service
ssh nicholasmparker@helios.local
journalctl -u skylapse-capture -f

# Test capture endpoint
curl -X POST http://helios.local:8080/capture \
  -H "Content-Type: application/json" \
  -d '{"iso": 0, "profile": "a"}'
```

---

## 📊 Database Queries

```bash
# Recent sessions
docker-compose exec backend python3 -c "
import sqlite3
conn = sqlite3.connect('/data/db/skylapse.db')
cursor = conn.execute('SELECT id, schedule_type, profile, status, datetime(start_time, \"unixepoch\", \"localtime\") as start, capture_count FROM sessions ORDER BY start_time DESC LIMIT 10')
for row in cursor: print(row)
"

# Today's captures count
docker-compose exec backend python3 -c "
import sqlite3
conn = sqlite3.connect('/data/db/skylapse.db')
cursor = conn.execute('SELECT COUNT(*) FROM captures WHERE date(timestamp, \"unixepoch\", \"localtime\") = date(\"now\", \"localtime\")')
print(f'Captures today: {cursor.fetchone()[0]}')
"
```

---

## 🔧 Quick Fixes

### Restart Everything

```bash
docker-compose down
docker-compose up -d
```

### Clear Database (nuclear option)

```bash
rm data/db/skylapse.db
docker-compose restart backend worker
```

### Force Manual Capture (for testing)

```bash
curl -X POST http://192.168.0.124:8080/capture \
  -H "Content-Type: application/json" \
  -d '{
    "iso": 0,
    "exposure_compensation": 0.0,
    "profile": "a"
  }'
```

---

## 📝 Git Workflow

```bash
# Create feature branch
git checkout -b feature/description

# Commit with detailed message
git commit -m "type(scope): description

Detailed explanation...

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# Push and create PR
git push -u origin feature/description
```

---

## 🎯 Common Mistakes to Avoid

1. ❌ Using `ssh pi@helios.local` instead of `ssh nicholasmparker@helios.local`
2. ❌ Running `npm install` on host instead of `docker-compose exec frontend npm install`
3. ❌ Forgetting to rebuild Docker after dependency changes
4. ❌ Not checking if backend container was running during sunrise window
5. ❌ Assuming sunrise is at the same time every day (it changes!)
6. ❌ Using relative file paths instead of absolute in Docker commands

---

## 📚 Documentation Index

- **API.md** - Complete API reference for Backend and Pi services
- **ARCHITECTURE.md** - System architecture and design decisions
- **DEPLOYMENT_AND_DOCKER.md** - Docker workflow and deployment
- **HARDWARE.md** - Raspberry Pi and camera setup
- **TESTING.md** - Test strategy and Playwright tests
- **CLAUDE.md** - Docker workflow reminders (critical!)

---

**Last Updated**: October 2, 2025
