#!/bin/bash

# Skylapse Production Setup Script
# Usage: curl -fsSL https://raw.githubusercontent.com/nicholasmparker/Skylapse/main/scripts/setup-production.sh | bash

set -e

echo "🚀 Skylapse Production Setup"
echo "============================"
echo ""

# Check for Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Detect which docker compose command is available
# Prefer "docker compose" (plugin) over "docker-compose" (standalone)
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
    echo "✓ Using docker compose (plugin)"
elif command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
    echo "✓ Using docker-compose (standalone)"
else
    echo "❌ Docker Compose is not installed."
    echo "   Install with: sudo apt-get install docker-compose-plugin"
    exit 1
fi

# Create directory structure
echo "📁 Creating directory structure..."
mkdir -p data/images data/timelapses data/db backend

# Collect configuration
echo ""
echo "📝 Configuration"
echo "================"
echo ""

read -p "Pi hostname or IP [192.168.0.124]: " PI_HOST </dev/tty
PI_HOST=${PI_HOST:-192.168.0.124}

read -p "Pi port [8080]: " PI_PORT </dev/tty
PI_PORT=${PI_PORT:-8080}

read -p "Pi SSH username [nicholasmparker]: " PI_USER </dev/tty
PI_USER=${PI_USER:-nicholasmparker}

read -p "Pi source directory [~/skylapse-images/]: " PI_SOURCE </dev/tty
PI_SOURCE=${PI_SOURCE:-~/skylapse-images/}

read -p "Backend port [8082]: " BACKEND_PORT </dev/tty
BACKEND_PORT=${BACKEND_PORT:-8082}

read -p "Frontend port [3000]: " FRONTEND_PORT </dev/tty
FRONTEND_PORT=${FRONTEND_PORT:-3000}

read -p "Server IP or hostname (for BACKEND_URL and VITE_BACKEND_URL): " SERVER_HOST </dev/tty
if [ -z "$SERVER_HOST" ]; then
    SERVER_HOST="localhost"
fi

read -p "Transfer interval in minutes [5]: " TRANSFER_INTERVAL </dev/tty
TRANSFER_INTERVAL=${TRANSFER_INTERVAL:-5}

read -p "Delete images from Pi after N days [1]: " DELETE_AFTER_DAYS </dev/tty
DELETE_AFTER_DAYS=${DELETE_AFTER_DAYS:-1}

# Create .env file
echo ""
echo "📝 Creating .env file..."
cat > .env <<EOF
# Pi Connection
PI_HOST=${PI_HOST}
PI_PORT=${PI_PORT}
PI_USER=${PI_USER}
PI_SOURCE=${PI_SOURCE}

# Backend Configuration
BACKEND_PORT=${BACKEND_PORT}
BACKEND_URL=http://${SERVER_HOST}:${BACKEND_PORT}
BACKEND_NAME=production

# Frontend Configuration
FRONTEND_PORT=${FRONTEND_PORT}
VITE_BACKEND_URL=http://${SERVER_HOST}:${BACKEND_PORT}

# Transfer Service
TRANSFER_INTERVAL_MINUTES=${TRANSFER_INTERVAL}
DELETE_AFTER_DAYS=${DELETE_AFTER_DAYS}

# Volume Paths (optional, defaults to ./data/*)
# SKYLAPSE_IMAGES_PATH=/path/to/images
# SKYLAPSE_TIMELAPSES_PATH=/path/to/timelapses
# SKYLAPSE_DB_PATH=/path/to/db
EOF

# Create docker-compose.prod.yml
echo "📝 Creating docker-compose.prod.yml..."
cat > docker-compose.prod.yml <<'EOF'
version: "3.8"

services:
  backend:
    image: ghcr.io/nicholasmparker/skylapse/backend:main
    ports:
      - "${BACKEND_PORT:-8082}:8082"
    volumes:
      - ./backend/config.json:/app/config.json:ro
      - ${SKYLAPSE_IMAGES_PATH:-./data/images}:/data/images
      - ${SKYLAPSE_TIMELAPSES_PATH:-./data/timelapses}:/data/timelapses
      - ${SKYLAPSE_DB_PATH:-./data/db}:/data/db
    environment:
      - PI_HOST=${PI_HOST:-192.168.0.124}
      - PI_PORT=${PI_PORT:-8080}
      - BACKEND_URL=${BACKEND_URL:-http://localhost:8082}
      - REDIS_URL=redis://redis:6379
      - BACKEND_NAME=${BACKEND_NAME:-production}
    depends_on:
      - redis
    restart: unless-stopped

  transfer:
    image: ghcr.io/nicholasmparker/skylapse/backend:main
    command: python3 services/transfer.py
    network_mode: host
    volumes:
      - ${SKYLAPSE_IMAGES_PATH:-./data/images}:/data/images
      - ~/.ssh:/root/.ssh:ro
    environment:
      - PI_HOST=${PI_HOST:-192.168.0.124}
      - PI_USER=${PI_USER:-nicholasmparker}
      - PI_SOURCE=${PI_SOURCE:-~/skylapse-images/}
      - LOCAL_DEST=${LOCAL_DEST:-/data/images}
      - TRANSFER_INTERVAL_MINUTES=${TRANSFER_INTERVAL_MINUTES:-5}
      - DELETE_AFTER_DAYS=${DELETE_AFTER_DAYS:-1}
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    restart: unless-stopped

  worker:
    image: ghcr.io/nicholasmparker/skylapse/worker:main
    command: rq worker --url redis://redis:6379 timelapse
    volumes:
      - ${SKYLAPSE_IMAGES_PATH:-./data/images}:/data/images
      - ${SKYLAPSE_TIMELAPSES_PATH:-./data/timelapses}:/data/timelapses
      - ${SKYLAPSE_DB_PATH:-./data/db}:/data/db
    depends_on:
      - redis
      - backend
    restart: unless-stopped
    environment:
      - REDIS_URL=redis://redis:6379
    deploy:
      resources:
        limits:
          memory: 4G

  frontend:
    image: ghcr.io/nicholasmparker/skylapse/frontend:main
    ports:
      - "${FRONTEND_PORT:-3000}:3000"
    environment:
      - VITE_BACKEND_URL=${VITE_BACKEND_URL:-http://localhost:8082}
    depends_on:
      - backend
    restart: unless-stopped

volumes:
  redis-data:
EOF

# Create default backend config
echo "📝 Creating backend/config.json..."
cat > backend/config.json <<'EOF'
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
EOF

echo ""
echo "🔑 SSH Setup"
echo "============"
echo ""
echo "The transfer service needs SSH access to pull images from the Pi."
echo ""

if [ ! -f ~/.ssh/id_ed25519 ] && [ ! -f ~/.ssh/id_rsa ]; then
    read -p "No SSH key found. Generate one now? (y/n) " -n 1 -r REPLY </dev/tty
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        ssh-keygen -t ed25519 -C "skylapse-transfer" -f ~/.ssh/id_ed25519 -N ""
        echo "✅ SSH key generated"
    fi
fi

echo ""
echo "Copy your SSH key to the Pi with:"
echo "  ssh-copy-id ${PI_USER}@${PI_HOST}"
echo ""
echo "Then test the connection:"
echo "  ssh ${PI_USER}@${PI_HOST} 'ls ${PI_SOURCE}'"
echo ""

read -p "Press Enter to continue after setting up SSH access..." </dev/tty

# Pull images
echo ""
echo "📦 Pulling Docker images..."
$DOCKER_COMPOSE -f docker-compose.prod.yml pull

# Start services
echo ""
echo "🚀 Starting services..."
$DOCKER_COMPOSE -f docker-compose.prod.yml up -d

echo ""
echo "✅ Skylapse is now running!"
echo ""
echo "📊 Access points:"
echo "  Frontend: http://${SERVER_HOST}:${FRONTEND_PORT}"
echo "  Backend:  http://${SERVER_HOST}:${BACKEND_PORT}"
echo "  Health:   http://${SERVER_HOST}:${BACKEND_PORT}/health"
echo "  Status:   http://${SERVER_HOST}:${BACKEND_PORT}/status"
echo ""
echo "📝 Next steps:"
echo "  1. Edit backend/config.json to configure schedules"
echo "  2. Update location in backend/config.json"
echo "  3. Restart backend: docker compose -f docker-compose.prod.yml restart backend"
echo ""
echo "📋 Useful commands:"
echo "  View logs:    docker compose -f docker-compose.prod.yml logs -f"
echo "  Stop:         docker compose -f docker-compose.prod.yml down"
echo "  Update:       docker compose -f docker-compose.prod.yml pull && docker compose -f docker-compose.prod.yml up -d"
echo ""
echo "📖 Full documentation: https://github.com/nicholasmparker/skylapse"
