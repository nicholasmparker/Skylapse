# Frontend Configuration System

This document describes the unified configuration system for the Skylapse frontend application.

## Overview

The frontend now uses a **unified configuration system** that centralizes all environment management, following the same pattern as the backend services. This eliminates scattered `.env` files and provides intelligent defaults.

## Configuration Files

### Primary Configuration
- `src/config/unified-config.ts` - **Main configuration system**
- `src/config/environment.ts` - **Legacy compatibility layer**

### Environment Variables
- `.env.development` - **Development environment variables** (optional overrides)
- `.env.local` - **Local overrides** (gitignored, for personal settings)

## Usage

### Recommended (New Code)
```typescript
import { config, API_URL, WS_URL, location } from '../config/unified-config';

// Access structured configuration
const apiEndpoint = buildServiceURL(config.services.api, '/health');
const cameraEnabled = config.features.cameraPreview;
const coords = config.location;
```

### Legacy Compatibility (Existing Code)
```typescript
import { API_URL, WS_URL, CAPTURE_URL, LOCATION } from '../config/environment';

// Existing code continues to work unchanged
const healthCheck = `${API_URL}/health`;
```

## Environment Variables

All environment variables are **optional** with intelligent defaults:

### Service Endpoints
```bash
# Processing service (API + WebSocket)
VITE_PROCESSING_HOST=localhost          # Default: localhost (dev) / processing (prod)
VITE_PROCESSING_PORT=8081               # Default: 8081

# Capture service (hardware)
VITE_CAPTURE_HOST=helios.local          # Default: helios.local
VITE_CAPTURE_PORT=8080                  # Default: 8080
```

### Location Configuration
```bash
VITE_LOCATION_NAME="Park City, UT"      # Default: Park City, UT
VITE_LOCATION_LATITUDE=40.7608          # Default: 40.7608
VITE_LOCATION_LONGITUDE=-111.8910       # Default: -111.8910
VITE_LOCATION_TIMEZONE=America/Denver   # Default: America/Denver
```

### Feature Flags
```bash
VITE_OPENWEATHER_API_KEY=your_key       # Default: null (weather disabled)
VITE_ENABLE_REALTIME=true               # Default: true
VITE_ENABLE_CAMERA_PREVIEW=true         # Default: true
```

### UI Configuration
```bash
VITE_UI_THEME=auto                      # Default: auto (light/dark/auto)
VITE_UPDATE_INTERVAL_MS=5000            # Default: 5000ms
```

### Environment Detection
```bash
VITE_SKYLAPSE_ENV=development           # Default: auto-detected
```

## Default Behavior

The configuration system provides intelligent defaults without requiring any environment variables:

1. **Development**: Auto-detects localhost, uses HTTP, enables debug logging
2. **Production**: Uses Docker service names, HTTPS, minimal logging
3. **Location**: Defaults to Park City, UT coordinates
4. **Features**: All features enabled by default
5. **Services**: Smart host/port detection based on environment

## Debugging

In development mode, configuration is logged to console and exposed globally:

```javascript
// Browser console
console.log(window.SKYLAPSE_CONFIG);

// Configuration validation
window.SKYLAPSE_CONFIG.meta.configVersion; // "2.0.0"
window.SKYLAPSE_CONFIG.urls.api;           // Computed URLs
```

## Migration Guide

### From Environment Variables
- ✅ No changes needed - existing `.env` files continue to work
- ✅ Environment variables take precedence over defaults
- ✅ Add new variables as needed for customization

### From Direct Imports
```typescript
// OLD
const API_URL = 'http://localhost:8081';

// NEW
import { API_URL } from '../config/unified-config';
```

### From Scattered Config
```typescript
// OLD - Multiple config files
import { apiUrl } from '../api/config';
import { wsUrl } from '../websocket/config';
import { location } from '../location/config';

// NEW - Single unified config
import { config } from '../config/unified-config';
const { services, location } = config;
```

## Benefits

1. **Centralized**: Single source of truth for all configuration
2. **Environment Aware**: Intelligent defaults for dev/prod environments
3. **Type Safe**: Full TypeScript support with proper interfaces
4. **Backward Compatible**: Existing code continues to work
5. **Docker Ready**: Follows backend service configuration patterns
6. **Debuggable**: Clear logging and global exposure for troubleshooting

## Technical Details

- Follows same pattern as `processing/src/config.py` and `backend/src/config.py`
- Uses `import.meta.env` for Vite environment variable access
- Validates configuration at load time with helpful error messages
- Provides URL building utilities for service communication
- Exposes configuration globally for Playwright tests and debugging
