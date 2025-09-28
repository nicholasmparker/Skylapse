# Skylapse Real-Time Backend - Production Deployment Guide

**Professional Mountain Timelapse Camera System**
**Production-Ready Real-Time Architecture**

## 🚀 Overview

This deployment replaces the broken Socket.IO implementation with a production-ready real-time backend featuring:

- **JWT Authentication** - Secure WebSocket connections from day one
- **Docker Service Discovery** - Proper container networking (no localhost dependencies)
- **Bulletproof Error Handling** - Graceful degradation for remote mountain deployments
- **Professional Logging** - Structured monitoring and health checks
- **Auto-Reconnection** - Resilient connections that survive network interruptions
- **Resource Monitoring** - Memory/CPU limits and health checks

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │───▶│  Real-time      │───▶│   Processing    │
│   Dashboard     │    │  Backend        │    │   Service       │
│   (React)       │    │  (WebSocket)    │    │   (Python)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │              ┌─────────────────┐              │
         └─────────────▶│   Integration   │◀─────────────┘
                        │   Layer         │
                        └─────────────────┘
```

### Key Components

1. **WebSocket Server** (`backend/src/realtime_server.py`)
   - JWT authentication for all connections
   - Channel-based subscriptions (dashboard, alerts, etc.)
   - Connection health monitoring with automatic cleanup
   - CORS and security headers

2. **Frontend Client** (`frontend/src/hooks/useRealTimeData.ts`)
   - Native WebSocket implementation (replaced Socket.IO)
   - Automatic reconnection with exponential backoff
   - Offline-first patterns with data caching
   - Authentication token management

3. **Integration Layer** (`backend/src/integration.py`)
   - Connects existing processing backend to new real-time server
   - Event broadcasting for system status, progress updates
   - HTTP-based broadcasting API

4. **Docker Configuration**
   - Service discovery using container names
   - Resource limits and health checks
   - Security hardening (no-new-privileges, non-root users)

## 🔧 Quick Start

### 1. Deploy Production System

```bash
# Clone and navigate to project
cd /Users/nicholasmparker/Projects/skylapse

# Deploy with auto-configuration
./scripts/deploy-production.sh

# Or deploy specific components
./scripts/deploy-production.sh deploy
```

### 2. Verify Deployment

```bash
# Run comprehensive test suite
./scripts/test-deployment.sh

# Or run specific tests
./scripts/test-deployment.sh health      # Health checks
./scripts/test-deployment.sh auth       # Authentication
./scripts/test-deployment.sh websocket  # WebSocket functionality
./scripts/test-deployment.sh network    # Container networking
./scripts/test-deployment.sh load       # Load testing
```

### 3. Access Services

- **Frontend Dashboard**: http://localhost:3000
- **Real-time WebSocket**: ws://localhost:8082/ws
- **Health Endpoints**:
  - Real-time: http://localhost:8082/health
  - Frontend: http://localhost:3000/health
  - Stats: http://localhost:8082/stats

## 🔐 Authentication

### JWT Token Management

The system uses JWT tokens for WebSocket authentication:

```bash
# Generate a test token
curl -X POST http://localhost:8082/auth/token \
  -H "Content-Type: application/json" \
  -d '{"user_id": "mountain_operator", "permissions": ["dashboard:read", "camera:control"]}'
```

### WebSocket Connection Flow

1. Client connects to `/ws` endpoint
2. Server waits for authentication message within 10 seconds
3. Client sends: `{"type": "auth", "token": "jwt_token_here"}`
4. Server validates token and responds with `auth_success` or `auth_error`
5. Authenticated clients can subscribe to channels

## 📊 Monitoring & Debugging

### Connection Statistics

```bash
# Get real-time connection stats
curl http://localhost:8082/stats
```

### Log Management

```bash
# View all service logs
docker-compose -f docker-compose.production.yml logs -f

# View specific service logs
docker-compose -f docker-compose.production.yml logs -f realtime-backend
docker-compose -f docker-compose.production.yml logs -f frontend

# Follow logs with timestamps
docker-compose -f docker-compose.production.yml logs -f -t realtime-backend
```

### Health Checks

```bash
# Check service health
curl http://localhost:8082/health
curl http://localhost:3000/health

# Check container health
docker ps --filter "health=healthy"
```

## 🛠️ Development & Testing

### Local Development

```bash
# Start development environment
docker-compose -f frontend/docker-compose.yml up frontend-dev

# Start real-time backend for development
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python src/realtime_server.py
```

### Integration Testing

The test suite validates:
- Service health endpoints
- JWT authentication flow
- WebSocket connection and messaging
- Container networking
- Resource usage limits
- Error handling and recovery
- Production-ready features (CORS, security headers)
- Load testing with multiple concurrent connections

## 🚨 Troubleshooting

### Common Issues

1. **Connection Refused Errors**
   ```bash
   # Check if services are running
   docker ps

   # Check service logs
   docker-compose -f docker-compose.production.yml logs realtime-backend
   ```

2. **Authentication Failures**
   ```bash
   # Verify JWT secret is set
   echo $JWT_SECRET

   # Generate new token
   curl -X POST http://localhost:8082/auth/token \
     -H "Content-Type: application/json" \
     -d '{"user_id": "test", "permissions": ["dashboard:read"]}'
   ```

3. **WebSocket Connection Issues**
   ```bash
   # Test WebSocket connection
   python3 -c "
   import asyncio
   import websockets
   import json

   async def test():
       async with websockets.connect('ws://localhost:8082/ws') as ws:
           await ws.send(json.dumps({'type': 'auth', 'token': 'test_token'}))
           response = await ws.recv()
           print(response)

   asyncio.run(test())
   "
   ```

4. **Container Networking Problems**
   ```bash
   # Test container-to-container connectivity
   docker exec skylapse-frontend curl -f http://realtime-backend:8082/health
   ```

### Performance Tuning

1. **Resource Limits**: Adjust CPU/memory limits in `docker-compose.production.yml`
2. **Connection Limits**: Modify `MAX_CONNECTIONS_PER_USER` in real-time backend
3. **Cache Duration**: Tune `CACHE_DURATION` settings in frontend client
4. **Heartbeat Interval**: Adjust WebSocket heartbeat in backend configuration

## 🔄 Migration from Socket.IO

### Key Changes

1. **Protocol**: Socket.IO → Native WebSocket + JSON
2. **Authentication**: None → JWT tokens required
3. **Networking**: localhost → Docker service names
4. **Error Handling**: Basic → Comprehensive with retry logic
5. **Monitoring**: Minimal → Production health checks and metrics

### Migration Checklist

- [ ] Remove Socket.IO dependencies from frontend
- [ ] Update environment variables for service discovery
- [ ] Implement JWT authentication in clients
- [ ] Update event handling code for new message format
- [ ] Test all real-time features
- [ ] Validate error handling and reconnection
- [ ] Performance test with expected load

## 📚 API Reference

### WebSocket Messages

#### Authentication
```json
// Client → Server
{"type": "auth", "token": "jwt_token"}

// Server → Client (Success)
{"type": "auth_success", "connection_id": "uuid", "user_id": "user"}

// Server → Client (Error)
{"type": "auth_error", "error": "Invalid token"}
```

#### Subscriptions
```json
// Client → Server
{"type": "subscribe", "channel": "dashboard"}

// Server → Client
{"type": "subscription_result", "channel": "dashboard", "success": true}
```

#### Dashboard Events
```json
// Server → Client
{
  "type": "dashboard_event",
  "event": "system.status",
  "data": {...},
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### HTTP Endpoints

- `GET /health` - Health check
- `GET /stats` - Connection statistics
- `POST /auth/token` - Generate JWT token
- `POST /broadcast` - Broadcast message to channel (internal)

## 🏭 Production Deployment

### Environment Variables

Create `.env` file:
```bash
JWT_SECRET=your_production_jwt_secret_here
POSTGRES_PASSWORD=secure_database_password
GRAFANA_PASSWORD=monitoring_dashboard_password
CAMERA_ID=mountain_camera_01
LOCATION_LAT=45.0
LOCATION_LON=-110.0
TIMEZONE=America/Denver
DATA_PATH=/data/skylapse
```

### Security Considerations

1. **Change default JWT secret** in production
2. **Use HTTPS/WSS** in production (configure reverse proxy)
3. **Set up proper firewall rules** for mountain deployments
4. **Regular security updates** for base images
5. **Monitor resource usage** and set alerts

### Backup & Recovery

1. **Database backups**: PostgreSQL data in `postgres_data` volume
2. **Image data**: Raw/processed data in bind-mounted volumes
3. **Configuration**: Environment files and Docker Compose configuration
4. **Monitoring**: Prometheus metrics and Grafana dashboards

---

**Built for Mountain Resilience** 🏔️
*Engineered to handle the harsh conditions and network challenges of remote mountain camera installations.*
