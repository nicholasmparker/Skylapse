/**
 * Environment Configuration Validation
 * Professional Mountain Timelapse Camera System
 */

interface EnvironmentConfig {
  API_URL: string;
  WS_URL: string;
  CAPTURE_URL: string;
  NODE_ENV: string;
}

function validateEnvironment(): EnvironmentConfig {
  const requiredVars = {
    API_URL: import.meta.env.VITE_API_URL || getDefaultAPIURL(),
    WS_URL: import.meta.env.VITE_WS_URL || getDefaultWSURL(),
    CAPTURE_URL: import.meta.env.VITE_CAPTURE_URL || getDefaultCaptureURL(),
    NODE_ENV: import.meta.env.MODE || 'development'
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

// Validate environment on module load
export const config = validateEnvironment();

// Export individual values for convenience
export const { API_URL, WS_URL, CAPTURE_URL, NODE_ENV } = config;
