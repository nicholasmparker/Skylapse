/**
 * Environment Configuration (Legacy Compatibility)
 * Professional Mountain Timelapse Camera System
 *
 * This file now uses the unified configuration system for centralized management.
 * Maintained for backward compatibility with existing imports.
 */

import {
  config as unifiedConfig,
  API_URL as UNIFIED_API_URL,
  WS_URL as UNIFIED_WS_URL,
  CAPTURE_URL as UNIFIED_CAPTURE_URL,
  location as unifiedLocation,
  features as unifiedFeatures
} from './unified-config';

// Legacy interface for backward compatibility
interface LocationConfig {
  latitude: number;
  longitude: number;
  name: string;
  timezone: string;
}

interface EnvironmentConfig {
  API_URL: string;
  WS_URL: string;
  CAPTURE_URL: string;
  NODE_ENV: string;
  OPENWEATHER_API_KEY?: string;
  LOCATION: LocationConfig;
}

// Create legacy-compatible configuration object
const config: EnvironmentConfig = {
  API_URL: UNIFIED_API_URL,
  WS_URL: UNIFIED_WS_URL,
  CAPTURE_URL: UNIFIED_CAPTURE_URL,
  NODE_ENV: unifiedConfig.environment,
  OPENWEATHER_API_KEY: unifiedFeatures.weatherAPI || undefined,
  LOCATION: unifiedLocation
};

// Legacy validation for URL format (maintained for existing error handling)
try {
  new URL(config.API_URL);
  new URL(config.WS_URL);
  new URL(config.CAPTURE_URL);
} catch (error) {
  throw new Error(
    `Invalid URL format in unified configuration. Please check your setup.\n` +
    `API_URL: ${config.API_URL}\n` +
    `WS_URL: ${config.WS_URL}\n` +
    `CAPTURE_URL: ${config.CAPTURE_URL}`
  );
}

// Export legacy configuration for backward compatibility
export { config };
export const { API_URL, WS_URL, CAPTURE_URL, NODE_ENV, OPENWEATHER_API_KEY, LOCATION } = config;

// Expose configuration globally for testing and debugging
if (typeof window !== 'undefined') {
  // Expose config to global scope for Playwright tests and debugging
  (window as any).APP_CONFIG = {
    API_URL,
    WS_URL,
    CAPTURE_URL,
    NODE_ENV,
    OPENWEATHER_API_KEY: OPENWEATHER_API_KEY ? 'configured' : 'not configured',
    LOCATION,
    // Add validation flag for tests
    configValidated: true,
    // Add build info if available
    buildInfo: {
      version: (globalThis as any).__APP_VERSION__ || 'unknown',
      buildTime: (globalThis as any).__BUILD_TIME__ || 'unknown',
    },
  };

  // Enhanced logging for development
  if (NODE_ENV === 'development') {
    console.log('🌍 Global configuration exposed to window.APP_CONFIG');
    console.log('🔧 Frontend Environment Variables Debug:');
    console.log('  VITE_API_URL:', import.meta.env.VITE_API_URL);
    console.log('  VITE_WS_URL:', import.meta.env.VITE_WS_URL);
    console.log('  VITE_CAPTURE_URL:', import.meta.env.VITE_CAPTURE_URL);
    console.log('  MODE:', import.meta.env.MODE);
    console.log('  NODE_ENV:', import.meta.env.NODE_ENV);
    console.log('  All VITE vars:', Object.keys(import.meta.env).filter(key => key.startsWith('VITE_')));
  }
}
