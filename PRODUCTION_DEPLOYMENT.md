# Skylapse Production Deployment Guide

## Architecture Overview

This production-ready deployment replaces the broken Socket.IO implementation with a bulletproof real-time architecture designed for harsh mountain environments and enterprise-scale deployments.

### Key Improvements

✅ **NO LOCALHOST URLS** - Proper container service discovery
✅ **JWT Authentication** - Secure from day one
✅ **SSE Primary Transport** - Optimal for mountain connectivity
✅ **WebSocket Fallback** - Bidirectional commands when needed
✅ **Long Polling Emergency** - Works in extreme conditions
✅ **Offline-First Patterns** - Graceful degradation
✅ **Container Networking** - Professional isolation
✅ **Load Balancing** - Enterprise-ready scaling

## Quick Start

1. **Clone and Configure**
   ```bash
   cd /Users/nicholasmparker/Projects/skylapse
   cp .env.production .env
   # Edit .env with your specific values
   ```

2. **Deploy Production Stack**
   ```bash
   docker-compose -f docker-compose.production.yml up -d
   ```

3. **Verify Health**
   ```bash
   curl http://localhost/health
   ```

## Architecture Components

### Transport Layer Hierarchy

```
Primary:    SSE (Server-Sent Events)     ← Optimal for mountain deployments
Fallback:   WebSocket                    ← For bidirectional commands
Emergency:  Long Polling                 ← Extreme connectivity conditions
Offline:    IndexedDB Cache              ← Works without connection
```

### Service Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     Gateway     │────│    Frontend     │────│  Real-time      │
│   (Nginx)       │    │   (React)       │    │   Backend       │
│ - Load Balance  │    │ - Dashboard     │    │ - SSE Server    │
│ - SSL Term      │    │ - Offline First │    │ - JWT Auth      │
│ - Rate Limit    │    │ - Connection    │    │ - Event Broker  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                        │                        │
         └────────────────────────┼────────────────────────┘
                                 │
         ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
         │   Processing    │    │    Capture      │    │     Redis       │
         │   (Python)      │    │   (Python)      │    │  (Message Bus)  │
         │ - Timelapse     │    │ - Camera Ctrl   │    │ - Event Stream  │
         │ - Gallery       │    │ - Scheduling    │    │ - Session Store │
         │ - REST API      │    │ - Storage       │    │ - Cache Layer   │
         └─────────────────┘    └─────────────────┘    └─────────────────┘
                │                        │                        │
                └────────────────────────┼────────────────────────┘
                                        │
                                ┌─────────────────┐
                                │   PostgreSQL    │
                                │   (Database)    │
                                │ - System State  │
                                │ - Capture Meta  │
                                │ - User Sessions │
                                └─────────────────┘
```

### Network Security

- **Frontend Network**: Public-facing services only
- **Backend Network**: Internal services with no external access
- **Service Discovery**: DNS-based container communication
- **Zero Trust**: All inter-service communication is authenticated

## Configuration

### Environment Variables

```bash
# Core Configuration
VERSION=1.0.0-production
CAMERA_ID=camera-01
SKYLAPSE_DOMAIN=your-mountain-site.com

# Security (CHANGE THESE!)
JWT_SECRET=your-super-secure-jwt-secret-minimum-32-characters
POSTGRES_PASSWORD=your-secure-database-password

# Location Settings
LOCATION_LAT=45.0        # Your mountain latitude
LOCATION_LON=-110.0      # Your mountain longitude
TIMEZONE=America/Denver  # Local timezone

# Data Storage
DATA_PATH=/data/skylapse # Host path for persistent data
```

### SSL/TLS Setup (Recommended)

1. **Obtain SSL Certificate**
   ```bash
   # Using Let's Encrypt
   certbot certonly --webroot -w /var/www/html -d your-mountain-site.com
   ```

2. **Configure SSL in Nginx**
   - Uncomment HTTPS server block in `/nginx/nginx.conf`
   - Update certificate paths in environment

3. **Update Frontend URLs**
   ```bash
   VITE_API_BASE_URL=https://your-mountain-site.com/api
   VITE_SSE_URL=https://your-mountain-site.com/events
   VITE_WS_URL=wss://your-mountain-site.com/ws
   ```

## Real-Time Event Protocol

### Event Schema

```typescript
interface SkylapsEvent {
  id: string;              // UUID for deduplication
  type: EventType;         // Strongly typed event categories
  timestamp: string;       // ISO 8601 UTC
  camera_id: string;       // Source camera identifier
  sequence_number: number; // For ordering/missing detection
  data: EventData;         // Type-specific payload
  priority: 'low' | 'normal' | 'high' | 'critical';
  ttl?: number;           // Time-to-live in seconds
}
```

### Event Types

```typescript
enum EventType {
  // System Events
  SYSTEM_STATUS = 'system.status',
  SYSTEM_ERROR = 'system.error',
  SYSTEM_WARNING = 'system.warning',

  // Capture Events
  CAPTURE_STARTED = 'capture.started',
  CAPTURE_PROGRESS = 'capture.progress',
  CAPTURE_COMPLETED = 'capture.completed',
  CAPTURE_FAILED = 'capture.failed',

  // Environmental Events
  ENVIRONMENTAL_UPDATE = 'environmental.update',
  WEATHER_ALERT = 'weather.alert',

  // Resource Events
  RESOURCE_UPDATE = 'resource.update',
  STORAGE_WARNING = 'storage.warning',

  // Connection Events
  CONNECTION_QUALITY = 'connection.quality',
  HEARTBEAT = 'heartbeat'
}
```

## Multi-Camera Scaling

### Horizontal Scaling Pattern

```bash
# Deploy additional camera pods
CAMERA_ID=camera-02 docker-compose -f docker-compose.production.yml up -d

# Load balancer automatically distributes connections
# Each camera pod is completely isolated
# Shared services (Redis, PostgreSQL) handle coordination
```

### Camera Discovery

```bash
# Cameras register themselves on startup
# Central event bus coordinates between cameras
# Dashboard can aggregate data from all cameras
# Failover automatically handled by load balancer
```

## Monitoring & Alerting

### Health Checks

All services include comprehensive health checks:

```bash
# Check overall system health
curl http://localhost/health

# Check individual services
docker-compose -f docker-compose.production.yml ps
```

### Metrics Collection (Optional)

Enable monitoring stack:

```bash
# Add to .env
COMPOSE_PROFILES=monitoring

# Deploy with monitoring
docker-compose -f docker-compose.production.yml --profile monitoring up -d

# Access dashboards
# Prometheus: http://localhost:9090
# Grafana: http://localhost:3001 (admin/your-password)
```

### Log Management

```bash
# View aggregated logs
docker-compose -f docker-compose.production.yml logs -f

# Service-specific logs
docker-compose -f docker-compose.production.yml logs -f realtime-backend
docker-compose -f docker-compose.production.yml logs -f frontend
```

## Backup & Disaster Recovery

### Data Backup

```bash
# Database backup
docker exec skylapse-postgres pg_dump -U postgres skylapse > backup_$(date +%Y%m%d).sql

# Image data backup
tar -czf images_backup_$(date +%Y%m%d).tar.gz /data/skylapse/

# Configuration backup
tar -czf config_backup_$(date +%Y%m%d).tar.gz .env nginx/ monitoring/
```

### Disaster Recovery

```bash
# 1. Deploy fresh system
docker-compose -f docker-compose.production.yml up -d

# 2. Restore database
docker exec -i skylapse-postgres psql -U postgres skylapse < backup_20241001.sql

# 3. Restore image data
tar -xzf images_backup_20241001.tar.gz -C /

# 4. Verify system health
curl http://localhost/health
```

## Troubleshooting

### Connection Issues

```bash
# Check real-time connection
curl -N http://localhost/events
# Should stream heartbeat events

# Check WebSocket fallback
wscat -c ws://localhost/ws
# Should receive connection acknowledgment
```

### Performance Issues

```bash
# Check resource usage
docker stats

# Monitor connection quality
# Dashboard shows connection state and latency

# Check event queue
docker exec skylapse-redis redis-cli info
```

### Common Issues

1. **Camera Access**: Ensure host devices are properly mapped
2. **Storage Space**: Monitor disk usage on host system
3. **Network Connectivity**: Verify container DNS resolution
4. **SSL Issues**: Check certificate validity and nginx config

## Security Considerations

### Production Hardening

- [ ] Change all default passwords
- [ ] Enable SSL/TLS encryption
- [ ] Configure firewall rules
- [ ] Set up log monitoring
- [ ] Enable fail2ban for attack prevention
- [ ] Regular security updates

### Network Security

- [ ] Backend network is internal-only
- [ ] Rate limiting configured
- [ ] Security headers enabled
- [ ] JWT tokens properly secured
- [ ] Database access restricted

## Performance Tuning

### Mountain Deployment Optimizations

- **Connection Timeouts**: Tuned for high-latency networks
- **Retry Logic**: Exponential backoff with jitter
- **Caching Strategy**: Aggressive caching for offline resilience
- **Resource Limits**: Optimized for embedded systems

### Scaling Recommendations

- **Small Installation**: 2GB RAM, 2 CPU cores
- **Multiple Cameras**: 4GB RAM, 4 CPU cores
- **Enterprise Deployment**: 8GB+ RAM, 8+ CPU cores

## Support & Maintenance

### Regular Maintenance

```bash
# Update system
docker-compose -f docker-compose.production.yml pull
docker-compose -f docker-compose.production.yml up -d

# Clean old images
docker system prune -f

# Rotate logs
docker-compose -f docker-compose.production.yml logs --since 24h > recent.log
```

### Emergency Procedures

```bash
# Emergency restart
docker-compose -f docker-compose.production.yml restart

# Reset to last known good state
docker-compose -f docker-compose.production.yml down
docker-compose -f docker-compose.production.yml up -d

# Emergency offline mode
# Frontend automatically switches to cached data
```

---

## Architecture Validation

✅ **Zero localhost URLs** - All services use container names
✅ **Production authentication** - JWT-based security from day one
✅ **Container networking** - Proper service discovery and isolation
✅ **Graceful degradation** - Works offline with cached data
✅ **Professional error handling** - Comprehensive retry and fallback logic
✅ **Multi-camera ready** - Horizontal scaling architecture
✅ **Mountain-optimized** - Designed for harsh connectivity conditions

This architecture is production-ready for enterprise mountain camera deployments.
