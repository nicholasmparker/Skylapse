/**
 * Environment Configuration Validation
 * Professional Mountain Timelapse Camera System
 */

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

function validateEnvironment(): EnvironmentConfig {
  const requiredVars = {
    API_URL: import.meta.env.VITE_API_URL || getDefaultAPIURL(),
    WS_URL: import.meta.env.VITE_WS_URL || getDefaultWSURL(),
    CAPTURE_URL: import.meta.env.VITE_CAPTURE_URL || getDefaultCaptureURL(),
    NODE_ENV: import.meta.env.MODE || 'development',
    OPENWEATHER_API_KEY: import.meta.env.VITE_OPENWEATHER_API_KEY,
    LOCATION: getLocationConfig()
  };

  // Validate URLs
  try {
    new URL(requiredVars.API_URL);
    new URL(requiredVars.WS_URL);
    new URL(requiredVars.CAPTURE_URL);
  } catch (error) {
    throw new Error(
      `Invalid URL format in environment variables. Please check your configuration.\n` +
      `API_URL: ${requiredVars.API_URL}\n` +
      `WS_URL: ${requiredVars.WS_URL}\n` +
      `CAPTURE_URL: ${requiredVars.CAPTURE_URL}`
    );
  }

  // Log configuration in development
  if (requiredVars.NODE_ENV === 'development') {
    console.log('🚀 Skylapse Frontend Configuration:');
    console.log('📡 API URL:', requiredVars.API_URL);
    console.log('🔌 WebSocket URL:', requiredVars.WS_URL);
    console.log('📷 Capture URL:', requiredVars.CAPTURE_URL);
    console.log('🏔️ Environment:', requiredVars.NODE_ENV);
    console.log('📍 Location:', `${requiredVars.LOCATION.name} (${requiredVars.LOCATION.latitude}°N, ${requiredVars.LOCATION.longitude}°W)`);
    console.log('🌤️ Weather API Key:', requiredVars.OPENWEATHER_API_KEY ? 'Configured' : 'Not configured');
  }

  return requiredVars as EnvironmentConfig;
}

// Default URLs for Docker container networking
function getDefaultAPIURL(): string {
  // Use Docker service name in production, localhost in development
  const isDevelopment = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
  return isDevelopment ? 'http://localhost:8081' : 'http://processing:8081';
}

function getDefaultWSURL(): string {
  const isDevelopment = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
  return isDevelopment ? 'http://localhost:8081' : 'http://processing:8081';
}

function getDefaultCaptureURL(): string {
  // Hardware device URL remains consistent
  return 'http://helios.local:8080';
}

function getLocationConfig(): LocationConfig {
  // Use environment variables for location, with Park City defaults
  const latitude = parseFloat(import.meta.env.VITE_LOCATION_LATITUDE || '40.7608');
  const longitude = parseFloat(import.meta.env.VITE_LOCATION_LONGITUDE || '-111.8910');
  const name = import.meta.env.VITE_LOCATION_NAME || 'Park City, UT';
  const timezone = import.meta.env.VITE_LOCATION_TIMEZONE || 'America/Denver';

  // Validate coordinates
  if (isNaN(latitude) || isNaN(longitude) ||
      latitude < -90 || latitude > 90 ||
      longitude < -180 || longitude > 180) {
    console.warn('Invalid location coordinates, using Park City defaults');
    return {
      latitude: 40.7608,
      longitude: -111.8910,
      name: 'Park City, UT',
      timezone: 'America/Denver'
    };
  }

  return { latitude, longitude, name, timezone };
}

// Validate environment on module load
export const config = validateEnvironment();

// Export individual values for convenience
export const { API_URL, WS_URL, CAPTURE_URL, NODE_ENV, OPENWEATHER_API_KEY, LOCATION } = config;
