# Skylapse Real-Time Frontend Architecture

## 🏔️ Production-Ready Real-Time Dashboard

This document outlines the **bulletproof real-time frontend client** built for the Skylapse mountain timelapse camera system. Designed for reliable operation in remote mountain environments with intermittent connectivity.

## 🚀 Architecture Overview

### Core Components

1. **Authentication Context** (`src/contexts/AuthContext.tsx`)
   - Secure JWT token management
   - Automatic token refresh
   - Session persistence across browser restarts
   - Production-ready error handling

2. **Connection State Management** (`src/hooks/useConnectionState.ts`)
   - Native WebSocket connections (replaced broken Socket.IO)
   - Exponential backoff retry logic (1s → 30s max)
   - Connection quality monitoring with ping/pong
   - Offline/online state detection

3. **Real-Time Client Service** (`src/services/RealTimeClient.ts`)
   - Secure authenticated WebSocket connections
   - Event subscription management
   - Production configuration for Docker networks
   - Mountain deployment optimizations

4. **Error Boundaries** (`src/components/ErrorBoundary.tsx`)
   - Application-level error handling
   - Feature-level graceful degradation
   - Component-level error isolation
   - User-friendly error reporting

5. **Connection Status UI** (`src/components/ConnectionStatus.tsx`)
   - Real-time connection indicators
   - Signal strength visualization
   - Offline banners and notifications
   - Detailed connection diagnostics

## 🔧 Technical Implementation

### Docker Container Networking

**Production Configuration:**
```typescript
// Automatic Docker service name resolution
const getDefaultWSURL = () => {
  const isDev = window.location.hostname === 'localhost';
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = isDev ? 'localhost:8082' : 'realtime-backend:8082';
  return `${protocol}//${host}`;
};
```

**Environment Variables:**
```bash
# Production (Docker Compose)
VITE_API_URL=http://processing:8081
VITE_WS_URL=ws://realtime-backend:8082
VITE_CAPTURE_URL=http://helios.local:8080

# Development
VITE_API_URL=http://localhost:8081
VITE_WS_URL=ws://localhost:8082
VITE_CAPTURE_URL=http://localhost:8080
```

### Authentication Flow

1. **Login Request** → JWT tokens received
2. **Token Storage** → Secure localStorage with expiration
3. **WebSocket Auth** → Token sent with connection
4. **Auto Refresh** → Proactive token renewal (5min before expiry)
5. **Session Restore** → Automatic login on app restart

### Offline-First Patterns

```typescript
interface DataCache {
  systemStatus: { data: SystemStatus | null; timestamp: number };
  environmentalData: { data: EnvironmentalData | null; timestamp: number };
  recentCaptures: { data: TimelapseSequence[]; timestamp: number };
}

// Cache durations optimized for mountain deployments
const CACHE_DURATION = {
  systemStatus: 30000,      // 30 seconds
  environmentalData: 300000, // 5 minutes
  recentCaptures: 60000,    // 1 minute
};
```

### Error Handling Strategy

```typescript
// Three-tier error boundary system
<ApplicationErrorBoundary>     // App crashes
  <AuthProvider>
    <DashboardErrorBoundary>   // Feature failures
      <RealTimeErrorBoundary>  // Component errors
        <SystemDashboard />
      </RealTimeErrorBoundary>
    </DashboardErrorBoundary>
  </AuthProvider>
</ApplicationErrorBoundary>
```

## 🔄 Real-Time Data Flow

### WebSocket Event Handling

```typescript
// Secure event subscription with authentication
client.connect(accessToken).then(() => {
  client.subscribeToEvent('system.status');
  client.subscribeToEvent('capture.progress');
  client.subscribeToEvent('resource.update');
  client.subscribeToEvent('capture.complete');
});
```

### Connection Quality Monitoring

- **Excellent**: < 100ms ping, stable connection
- **Good**: < 300ms ping, occasional hiccups
- **Fair**: < 1000ms ping, noticeable delays
- **Poor**: > 1000ms ping, frequent disconnections
- **Offline**: No network or WebSocket connection

### Exponential Backoff

```typescript
const getReconnectDelay = (attempt: number) => {
  const delay = 1000 * Math.pow(2, attempt); // 1s, 2s, 4s, 8s...
  return Math.min(delay, 30000); // Max 30 seconds
};
```

## 🏔️ Mountain Deployment Optimizations

### Extended Timeouts
- **Connection Timeout**: 15s (vs 10s standard)
- **Ping Interval**: 45s (reduced bandwidth usage)
- **Health Check**: 2 minutes
- **Max Reconnect Attempts**: 15 (vs 10 standard)

### Bandwidth Conservation
- Compressed message format
- Reduced ping frequency
- Efficient data caching
- Smart polling fallbacks

### Resilience Features
- **Graceful Degradation**: Dashboard works without real-time
- **Cache Fallbacks**: Show last known data when offline
- **Progressive Enhancement**: Features unlock as connectivity improves
- **User Feedback**: Clear connection status at all times

## 🔐 Security Considerations

### JWT Authentication
- **Access Token**: Short-lived (15 min)
- **Refresh Token**: Long-lived (7 days)
- **Automatic Rotation**: Before expiration
- **Secure Storage**: HttpOnly cookies in production

### WebSocket Security
- **Token-based Auth**: Included in connection headers
- **CSRF Protection**: Origin validation
- **Rate Limiting**: Server-side implementation
- **Encryption**: WSS in production

## 📊 Monitoring & Diagnostics

### Built-in Health Checks
- Network connectivity status
- WebSocket connection state
- Authentication token validity
- Data freshness indicators
- Error occurrence tracking

### Debug Information
- Connection attempt history
- Ping/pong response times
- Cache hit/miss ratios
- Error boundary triggers
- Authentication events

## 🚀 Production Deployment

### Docker Compose Integration

```yaml
services:
  frontend:
    environment:
      - VITE_API_URL=http://processing:8081
      - VITE_WS_URL=ws://realtime-backend:8082
      - VITE_CAPTURE_URL=http://helios.local:8080
    networks:
      - skylapse
```

### Health Check Endpoint

```bash
# Container health verification
GET /health
# Returns: {"status": "healthy", "timestamp": "2024-01-01T00:00:00Z"}
```

## 🧪 Testing Strategy

### Connection Resilience Tests
- Network interruption simulation
- Server restart scenarios
- Authentication token expiration
- WebSocket reconnection logic

### Error Boundary Tests
- Component crash simulation
- API failure scenarios
- Invalid data handling
- Network timeout conditions

## 📈 Performance Metrics

### Optimizations Implemented
- **React.memo**: Prevent unnecessary re-renders
- **useMemo/useCallback**: Optimize hook dependencies
- **Lazy Loading**: Code splitting for better startup
- **Data Windowing**: Limit real-time metrics (100 samples)
- **Cache Management**: Efficient memory usage

### Expected Performance
- **Initial Load**: < 2s on 3G connection
- **Real-time Latency**: < 100ms in good conditions
- **Memory Usage**: < 50MB baseline
- **CPU Usage**: < 5% during normal operation

## 🔄 Migration from Broken Implementation

### What Was Fixed
❌ **Before**: Socket.IO with localhost URLs
✅ **After**: Native WebSocket with Docker service names

❌ **Before**: Commented-out authentication
✅ **After**: Production-ready JWT authentication

❌ **Before**: Basic error console logging
✅ **After**: Comprehensive error boundaries

❌ **Before**: No offline handling
✅ **After**: Offline-first with caching

❌ **Before**: Simple reconnection
✅ **After**: Exponential backoff with limits

## 🎯 Key Benefits

1. **Reliability**: Works in poor mountain connectivity
2. **Security**: Proper authentication from day one
3. **Maintainability**: Clean architecture with error boundaries
4. **Performance**: Optimized for remote deployments
5. **User Experience**: Clear feedback on connection status
6. **Scalability**: Modular design for future features

---

**Built for the mountains. Tested in the real world. Production ready.**
