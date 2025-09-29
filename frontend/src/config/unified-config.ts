/**
 * Unified Environment Configuration
 * Professional Mountain Timelapse Camera System
 *
 * Centralizes all frontend configuration with environment variable support
 * and intelligent defaults following backend service pattern
 */

interface LocationConfig {
  latitude: number;
  longitude: number;
  name: string;
  timezone: string;
}

interface ServiceEndpoint {
  host: string;
  port: number;
  protocol: 'http' | 'https';
}

interface FrontendConfig {
  environment: string;
  services: {
    api: ServiceEndpoint;
    websocket: ServiceEndpoint;
    capture: ServiceEndpoint;
  };
  location: LocationConfig;
  features: {
    weatherAPI: string | null;
    realTimeUpdates: boolean;
    cameraPreview: boolean;
  };
  ui: {
    theme: 'light' | 'dark' | 'auto';
    updateInterval: number;
  };
}

/**
 * Get unified frontend configuration following backend pattern
 */
export function getFrontendConfig(): FrontendConfig {
  // Detect environment context
  const isDevelopment =
    import.meta.env.MODE === 'development' ||
    window.location.hostname === 'localhost' ||
    window.location.hostname === '127.0.0.1';

  const environment = import.meta.env.VITE_SKYLAPSE_ENV ||
                     (isDevelopment ? 'development' : 'production');

  return {
    environment,

    services: {
      // Processing service (API + WebSocket)
      api: {
        host: getServiceHost('processing', isDevelopment),
        port: getServicePort('PROCESSING_PORT', 8081),
        protocol: getServiceProtocol(isDevelopment)
      },

      // WebSocket endpoint (same as processing service)
      websocket: {
        host: getServiceHost('processing', isDevelopment),
        port: getServicePort('PROCESSING_PORT', 8081),
        protocol: getServiceProtocol(isDevelopment)
      },

      // Capture service (hardware device)
      capture: {
        host: getServiceHost('capture', false), // Always use helios.local
        port: getServicePort('CAPTURE_PORT', 8080),
        protocol: 'http' as const // Hardware device uses HTTP
      }
    },

    location: {
      latitude: getNumericEnv('VITE_LOCATION_LATITUDE', 40.7608),
      longitude: getNumericEnv('VITE_LOCATION_LONGITUDE', -111.8910),
      name: import.meta.env.VITE_LOCATION_NAME || 'Park City, UT',
      timezone: import.meta.env.VITE_LOCATION_TIMEZONE || 'America/Denver'
    },

    features: {
      weatherAPI: import.meta.env.VITE_OPENWEATHER_API_KEY || null,
      realTimeUpdates: getBooleanEnv('VITE_ENABLE_REALTIME', true),
      cameraPreview: getBooleanEnv('VITE_ENABLE_CAMERA_PREVIEW', true)
    },

    ui: {
      theme: (import.meta.env.VITE_UI_THEME as 'light' | 'dark' | 'auto') || 'auto',
      updateInterval: getNumericEnv('VITE_UPDATE_INTERVAL_MS', 5000)
    }
  };
}

/**
 * Get service host based on environment and service type
 */
function getServiceHost(service: 'processing' | 'capture', isDevelopment: boolean): string {
  const envVar = `VITE_${service.toUpperCase()}_HOST`;
  const envValue = import.meta.env[envVar];

  if (envValue) return envValue;

  // Service-specific defaults
  switch (service) {
    case 'processing':
      return isDevelopment ? 'localhost' : 'processing';
    case 'capture':
      return 'helios.local'; // Hardware device - consistent across environments
    default:
      return 'localhost';
  }
}

/**
 * Get service port with fallback
 */
function getServicePort(envVar: string, defaultPort: number): number {
  const viteVar = `VITE_${envVar}`;
  const envValue = import.meta.env[viteVar];
  return envValue ? parseInt(envValue, 10) : defaultPort;
}

/**
 * Get service protocol based on environment
 */
function getServiceProtocol(isDevelopment: boolean): 'http' | 'https' {
  return isDevelopment ? 'http' : 'https';
}

/**
 * Parse numeric environment variable with fallback
 */
function getNumericEnv(varName: string, defaultValue: number): number {
  const value = import.meta.env[varName];
  if (!value) return defaultValue;

  const parsed = parseFloat(value);
  return isNaN(parsed) ? defaultValue : parsed;
}

/**
 * Parse boolean environment variable with fallback
 */
function getBooleanEnv(varName: string, defaultValue: boolean): boolean {
  const value = import.meta.env[varName];
  if (!value) return defaultValue;

  return value.toLowerCase() === 'true' || value === '1';
}

/**
 * Build full URL from service endpoint
 */
export function buildServiceURL(endpoint: ServiceEndpoint, path: string = ''): string {
  const baseUrl = `${endpoint.protocol}://${endpoint.host}:${endpoint.port}`;
  return path ? `${baseUrl}${path.startsWith('/') ? path : `/${path}`}` : baseUrl;
}

/**
 * Validate configuration and log in development
 */
function validateAndLogConfig(config: FrontendConfig): void {
  // Validate location coordinates
  const { latitude, longitude } = config.location;
  if (latitude < -90 || latitude > 90 || longitude < -180 || longitude > 180) {
    console.warn('⚠️ Invalid location coordinates detected, using defaults');
    config.location.latitude = 40.7608;
    config.location.longitude = -111.8910;
    config.location.name = 'Park City, UT';
    config.location.timezone = 'America/Denver';
  }

  // Log configuration in development
  if (config.environment === 'development') {
    console.log('🚀 Skylapse Unified Frontend Configuration:');
    console.log('🌍 Environment:', config.environment);
    console.log('📡 API Service:', buildServiceURL(config.services.api));
    console.log('🔌 WebSocket Service:', buildServiceURL(config.services.websocket));
    console.log('📷 Capture Service:', buildServiceURL(config.services.capture));
    console.log('📍 Location:', `${config.location.name} (${config.location.latitude}°N, ${config.location.longitude}°W)`);
    console.log('🌤️ Weather API:', config.features.weatherAPI ? 'Configured' : 'Not configured');
    console.log('🔄 Real-time Updates:', config.features.realTimeUpdates ? 'Enabled' : 'Disabled');
    console.log('📹 Camera Preview:', config.features.cameraPreview ? 'Enabled' : 'Disabled');
    console.log('✅ Unified configuration loaded successfully');
  }
}

// Create and validate configuration
export const config = getFrontendConfig();
validateAndLogConfig(config);

// Export convenience URLs for backward compatibility
export const API_URL = buildServiceURL(config.services.api);
export const WS_URL = buildServiceURL(config.services.websocket);
export const CAPTURE_URL = buildServiceURL(config.services.capture);

// Export configuration sections
export const { environment, services, location, features, ui } = config;

// Expose to global scope for debugging and testing
if (typeof window !== 'undefined') {
  (window as any).SKYLAPSE_CONFIG = {
    ...config,
    // Add computed URLs for convenience
    urls: {
      api: API_URL,
      websocket: WS_URL,
      capture: CAPTURE_URL
    },
    // Add metadata
    meta: {
      configVersion: '2.0.0',
      loadedAt: new Date().toISOString(),
      source: 'unified-config'
    }
  };

  if (config.environment === 'development') {
    console.log('🌍 Global configuration exposed to window.SKYLAPSE_CONFIG');
  }
}
