# Skylapse Docker Architecture
**Unified Container Orchestration for Mountain Timelapse Camera System**

## Overview

This document describes the redesigned Docker Compose architecture that solves the critical networking issues plaguing the Skylapse project. The new unified approach consolidates fragmented services into a single, coherent architecture that ensures proper service discovery and browser accessibility.

## Previous Problems Solved

### 1. Fragmented Compose Files
**Problem**: Two separate `docker-compose.yml` files created isolated networks
- `/processing/docker-compose.yml` - Processing backend only
- `/frontend/docker-compose.yml` - Frontend with complex environment configs

**Solution**: Single unified `docker-compose.yml` at project root with proper service dependencies

### 2. Browser Service Discovery Issues
**Problem**: Frontend using Docker service names that browsers cannot resolve
```yaml
# ❌ BROKEN - Browser can't resolve Docker service names
VITE_API_URL=http://processing:8081
VITE_WS_URL=ws://realtime-backend:8082
```

**Solution**: Use localhost URLs for browser accessibility
```yaml
# ✅ WORKING - Browser can resolve localhost
VITE_API_URL=http://localhost:8081
VITE_WS_URL=ws://localhost:8081
```

### 3. Environment Variable Chaos
**Problem**: Inconsistent variable naming and scattered configuration
- Mix of `REACT_APP_*` and `VITE_*` variables
- Production vs development configs were unclear
- Variables pointing to unreachable services

**Solution**: Standardized `VITE_*` variables with clear development/production profiles

## Architecture Design Principles

### 1. Single Network Topology
All services connect to a single bridge network (`skylapse-network`) with proper DNS resolution:
```yaml
networks:
  skylapse-network:
    driver: bridge
    name: skylapse-network
    ipam:
      config:
        - subnet: 172.20.0.0/24
```

### 2. Profile-Based Deployment
Clear separation of concerns using Docker Compose profiles:
- **`development`**: Hot-reload frontend, minimal services
- **`production`**: Optimized builds, full services including database
- **`capture`**: Includes camera hardware services
- **`monitoring`**: Adds Prometheus and Grafana

### 3. Browser-First Service Discovery
Critical architectural decision: **The browser is the client, not the container network**

Services must be accessible via `localhost` from the host machine because:
- Browsers cannot resolve Docker service names
- WebSocket connections must be accessible from browser context
- API calls originate from browser, not from within containers

### 4. Port Exposure Strategy
All primary services expose ports to host for direct browser access:
```yaml
ports:
  - "8081:8081"  # Processing API + WebSocket
  - "3000:3000"  # Frontend
  - "8080:8080"  # Capture API (when available)
```

## Service Architecture

### Processing Service (`processing`)
- **Image**: `skylapse/processing:latest`
- **Port**: 8081 (API + Socket.IO WebSocket)
- **Role**: Core backend processing with real-time WebSocket communication
- **Dependencies**: Redis (message broker)
- **Profiles**: `development`, `production`

### Frontend Services

#### Production Frontend (`frontend`)
- **Image**: `skylapse/frontend:latest` (Nginx-served static build)
- **Port**: 3000
- **Profile**: `production`

#### Development Frontend (`frontend-dev`)
- **Image**: `skylapse/frontend:dev` (Vite dev server)
- **Ports**: 3000 (app), 3001 (HMR)
- **Features**: Hot module reload, source mapping
- **Profile**: `development`

### Capture Service (`capture`)
- **Image**: `skylapse/capture:latest`
- **Port**: 8080
- **Hardware**: Requires camera and sensor device access
- **Profile**: `capture`, `development`, `production`

### Infrastructure Services

#### Redis (`redis`)
- **Purpose**: Message broker and caching
- **Port**: 6379
- **Profiles**: `development`, `production`

#### PostgreSQL (`postgres`)
- **Purpose**: Production database
- **Port**: 5432
- **Profile**: `production` only

## Environment Variables Strategy

### Core Configuration
```bash
# Project
VERSION=latest
SKYLAPSE_ENV=development
CAMERA_ID=camera-01

# Frontend (Browser-accessible URLs)
VITE_API_URL=http://localhost:8081
VITE_WS_URL=ws://localhost:8081
VITE_CAPTURE_URL=http://helios.local:8080

# Backend
DATABASE_URL=postgresql://user:pass@postgres:5432/skylapse
REDIS_URL=redis://redis:6379
```

### Development vs Production

#### Development
- Uses SQLite or minimal PostgreSQL
- Frontend with hot reload
- Simplified logging
- Direct localhost URLs

#### Production
- Full PostgreSQL database
- Optimized static frontend
- Comprehensive logging and monitoring
- Same localhost URLs (browser accessibility)

## Deployment Scenarios

### Development Workflow
```bash
# Start development environment
./skylapse-compose.sh dev

# Services started:
# - frontend-dev (hot reload)
# - processing (API + WebSocket)
# - redis (message broker)
```

### Production Deployment
```bash
# Start production environment
./skylapse-compose.sh prod

# Services started:
# - frontend (optimized build)
# - processing (API + WebSocket)
# - postgres (database)
# - redis (message broker)
```

### With Hardware Capture
```bash
# Start with camera services
./skylapse-compose.sh capture

# Additional services:
# - capture (camera hardware access)
```

### With Monitoring
```bash
# Start with monitoring stack
./skylapse-compose.sh monitoring

# Additional services:
# - prometheus (metrics)
# - grafana (dashboards)
```

## Volume Management

### Data Persistence
```yaml
volumes:
  raw_data:          # Camera raw images
  processed_data:    # Processed timelapses
  postgres_data:     # Database persistence
  redis_data:        # Cache persistence
```

### Development Optimization
```yaml
volumes:
  frontend_node_modules:  # Preserve installed packages
  # Hot reload mounts for source code
```

## Health Checks and Monitoring

All services include comprehensive health checks:
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8081/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 15s
```

## Security Considerations

### Network Isolation
- Backend database and Redis are isolated within Docker network
- Only necessary ports exposed to host
- Service-to-service communication via internal DNS

### Resource Limits
```yaml
deploy:
  resources:
    limits:
      memory: 256M
      cpus: '0.5'
    reservations:
      memory: 128M
      cpus: '0.1'
```

## Migration from Old Architecture

### 1. Remove Old Compose Files
- Delete `/processing/docker-compose.yml`
- Delete `/frontend/docker-compose.yml`

### 2. Update Environment Files
- Copy `.env.example` to `.env`
- Update URLs to use `localhost` instead of service names

### 3. Run Migration
```bash
# Stop old services
docker-compose down --remove-orphans

# Start new unified architecture
./skylapse-compose.sh dev
```

## Troubleshooting

### Common Issues

#### 1. "Cannot resolve service name" in browser
**Problem**: Frontend trying to reach `http://processing:8081`
**Solution**: Use `http://localhost:8081` in environment variables

#### 2. WebSocket connection fails
**Problem**: Using `http://` scheme for WebSocket URL
**Solution**: Use `ws://localhost:8081` for WebSocket connections

#### 3. Services can't communicate
**Problem**: Services on different networks
**Solution**: All services use single `skylapse-network`

### Debug Commands
```bash
# Check service status
./skylapse-compose.sh status

# View logs
./skylapse-compose.sh logs processing

# Check health
./skylapse-compose.sh health

# Network inspection
docker network inspect skylapse-network
```

## Benefits of New Architecture

1. **Unified Management**: Single compose file for all services
2. **Clear Profiles**: Distinct development and production configurations
3. **Browser Compatibility**: Proper service discovery for web clients
4. **Simplified Networking**: Single network with DNS resolution
5. **Easy Deployment**: Simple scripts for different scenarios
6. **Better Debugging**: Centralized logging and health checks
7. **Scalable Foundation**: Ready for production deployment

## Future Enhancements

1. **Load Balancing**: Add Nginx reverse proxy for production
2. **SSL Termination**: HTTPS support for production deployment
3. **Service Mesh**: Consider Traefik for advanced routing
4. **CI/CD Integration**: Docker image builds and deployment automation
5. **Backup Strategy**: Automated data backup and recovery

---

This architecture provides a robust foundation for the Skylapse mountain timelapse camera system, solving the critical networking issues while establishing patterns for future scalability.
