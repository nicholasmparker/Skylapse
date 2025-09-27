/**
 * Skylapse Application Constants
 * Professional Mountain Timelapse Camera System
 */

// API Configuration
export const API_ENDPOINTS = {
  CAPTURE: {
    LOGIN: '/api/auth/login',
    REFRESH: '/api/auth/refresh',
    LOGOUT: '/api/auth/logout',
    DASHBOARD: '/api/dashboard/status',
    PROGRESS: '/api/dashboard/progress',
    SETTINGS: '/api/settings',
    TRIGGER: '/api/capture/trigger',
    STOP: '/api/capture/stop',
    SCHEDULE: '/api/schedule',
  },
  PROCESSING: {
    SEQUENCES: '/api/gallery/sequences',
    GENERATE: '/api/gallery/generate',
    JOBS: '/api/gallery/jobs',
    ANALYTICS: '/api/analytics',
  },
} as const;

// Application Routes
export const ROUTES = {
  HOME: '/',
  DASHBOARD: '/dashboard',
  GALLERY: '/gallery',
  SETTINGS: '/settings',
  ANALYTICS: '/analytics',
  LOGIN: '/login',
  SEQUENCE_DETAIL: '/gallery/:id',
} as const;

// UI Constants
export const THEME = {
  COLORS: {
    MOUNTAIN: {
      50: '#f0f9ff',
      100: '#e0f2fe',
      200: '#bae6fd',
      300: '#7dd3fc',
      400: '#38bdf8',
      500: '#0ea5e9',
      600: '#0284c7',
      700: '#0369a1',
      800: '#075985',
      900: '#0c4a6e',
      950: '#082f49',
    },
    GOLDEN: {
      50: '#fefce8',
      100: '#fef9c3',
      200: '#fef08a',
      300: '#fde047',
      400: '#facc15',
      500: '#eab308',
      600: '#ca8a04',
      700: '#a16207',
      800: '#854d0e',
      900: '#713f12',
      950: '#422006',
    },
  },
  BREAKPOINTS: {
    SM: '640px',
    MD: '768px',
    LG: '1024px',
    XL: '1280px',
    '2XL': '1536px',
  },
} as const;

// Camera Configuration
export const CAMERA_SETTINGS = {
  ISO_VALUES: [100, 200, 400, 800, 1600, 3200, 6400],
  EXPOSURE_TIMES: [
    '1/4000', '1/2000', '1/1000', '1/500', '1/250', '1/125', '1/60', '1/30',
    '1/15', '1/8', '1/4', '1/2', '1', '2', '4', '8', '15', '30'
  ],
  WHITE_BALANCE_OPTIONS: [
    { value: 'auto', label: 'Auto' },
    { value: 'daylight', label: 'Daylight' },
    { value: 'cloudy', label: 'Cloudy' },
    { value: 'tungsten', label: 'Tungsten' },
    { value: 'fluorescent', label: 'Fluorescent' },
  ],
  IMAGE_FORMATS: [
    { value: 'jpeg', label: 'JPEG' },
    { value: 'raw', label: 'RAW' },
    { value: 'jpeg+raw', label: 'JPEG + RAW' },
  ],
  QUALITY_LEVELS: [
    { value: 1, label: 'Low' },
    { value: 2, label: 'Medium' },
    { value: 3, label: 'High' },
    { value: 4, label: 'Ultra' },
  ],
} as const;

// Video Generation Settings
export const VIDEO_SETTINGS = {
  FRAME_RATES: [12, 24, 30, 60],
  RESOLUTIONS: [
    { value: '720p', label: '720p (HD)' },
    { value: '1080p', label: '1080p (Full HD)' },
    { value: '4k', label: '4K (Ultra HD)' },
  ],
  FORMATS: [
    { value: 'mp4', label: 'MP4 (H.264)' },
    { value: 'webm', label: 'WebM (VP9)' },
    { value: 'mov', label: 'MOV (ProRes)' },
  ],
  QUALITY_PRESETS: [
    { value: 'low', label: 'Low (Fast)', bitrate: '2M' },
    { value: 'medium', label: 'Medium (Balanced)', bitrate: '5M' },
    { value: 'high', label: 'High (Quality)', bitrate: '10M' },
    { value: 'ultra', label: 'Ultra (Max)', bitrate: '20M' },
  ],
} as const;

// Status Types
export const STATUS_TYPES = {
  ACTIVE: 'active',
  PAUSED: 'paused',
  ERROR: 'error',
  SUCCESS: 'success',
  LOADING: 'loading',
} as const;

// WebSocket Event Types
export const WS_EVENTS = {
  SYSTEM_STATUS: 'system.status',
  CAPTURE_PROGRESS: 'capture.progress',
  CAPTURE_COMPLETE: 'capture.complete',
  RESOURCE_UPDATE: 'resource.update',
  ERROR_OCCURRED: 'error.occurred',
  JOB_STATUS: 'job.status',
} as const;

// Local Storage Keys
export const STORAGE_KEYS = {
  ACCESS_TOKEN: 'skylapse_access_token',
  REFRESH_TOKEN: 'skylapse_refresh_token',
  USER_PREFERENCES: 'skylapse_user_preferences',
  THEME_MODE: 'skylapse_theme_mode',
  LAST_SETTINGS: 'skylapse_last_settings',
} as const;

// Application Limits
export const LIMITS = {
  MAX_FILE_SIZE: 50 * 1024 * 1024, // 50MB
  MAX_SEQUENCE_LENGTH: 10000, // Maximum captures per sequence
  PAGINATION_SIZE: 20,
  WEBSOCKET_RECONNECT_ATTEMPTS: 5,
  API_TIMEOUT: 30000, // 30 seconds
  REFRESH_INTERVALS: {
    DASHBOARD: 5000, // 5 seconds
    GALLERY: 30000, // 30 seconds
    ANALYTICS: 60000, // 1 minute
  },
} as const;

// Astronomical Events
export const ASTRONOMICAL_EVENTS = {
  SUNRISE: 'sunrise',
  SUNSET: 'sunset',
  GOLDEN_HOUR_MORNING: 'golden_hour_morning',
  GOLDEN_HOUR_EVENING: 'golden_hour_evening',
  BLUE_HOUR_MORNING: 'blue_hour_morning',
  BLUE_HOUR_EVENING: 'blue_hour_evening',
  CIVIL_TWILIGHT_BEGIN: 'civil_twilight_begin',
  CIVIL_TWILIGHT_END: 'civil_twilight_end',
} as const;

// Weather Conditions
export const WEATHER_CONDITIONS = {
  CLEAR: 'clear',
  PARTLY_CLOUDY: 'partly_cloudy',
  CLOUDY: 'cloudy',
  OVERCAST: 'overcast',
  RAIN: 'rain',
  SNOW: 'snow',
  FOG: 'fog',
  STORM: 'storm',
} as const;

// Error Codes
export const ERROR_CODES = {
  UNAUTHORIZED: 'UNAUTHORIZED',
  FORBIDDEN: 'FORBIDDEN',
  NOT_FOUND: 'NOT_FOUND',
  VALIDATION_ERROR: 'VALIDATION_ERROR',
  CAMERA_UNAVAILABLE: 'CAMERA_UNAVAILABLE',
  STORAGE_FULL: 'STORAGE_FULL',
  NETWORK_ERROR: 'NETWORK_ERROR',
  SERVICE_UNAVAILABLE: 'SERVICE_UNAVAILABLE',
} as const;

// Success Messages
export const SUCCESS_MESSAGES = {
  LOGIN: 'Successfully logged in',
  LOGOUT: 'Successfully logged out',
  SETTINGS_SAVED: 'Settings saved successfully',
  CAPTURE_STARTED: 'Capture started successfully',
  CAPTURE_STOPPED: 'Capture stopped successfully',
  VIDEO_GENERATED: 'Video generation started',
  SCHEDULE_CREATED: 'Schedule created successfully',
  SCHEDULE_UPDATED: 'Schedule updated successfully',
  SEQUENCE_DELETED: 'Sequence deleted successfully',
} as const;

// Animation Durations (in milliseconds)
export const ANIMATIONS = {
  FAST: 150,
  NORMAL: 300,
  SLOW: 500,
  VERY_SLOW: 1000,
} as const;

// Z-Index Scale
export const Z_INDEX = {
  DROPDOWN: 1000,
  STICKY: 1020,
  MODAL_BACKDROP: 1040,
  MODAL: 1050,
  POPOVER: 1060,
  TOOLTIP: 1070,
  TOAST: 1080,
} as const;

// Development flags
export const DEV_FLAGS = {
  ENABLE_DEBUG_LOGS: import.meta.env.DEV,
  ENABLE_MOCK_API: import.meta.env.VITE_MOCK_API === 'true',
  ENABLE_PERFORMANCE_MONITORING: import.meta.env.PROD,
} as const;
