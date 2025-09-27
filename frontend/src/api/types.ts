/**
 * Skylapse API Types
 * Professional Mountain Timelapse Camera System
 */

// Core API Response Types
export interface APIResponse<T = any> {
  data: T;
  status: number;
  message?: string;
}

export interface APIError {
  error: {
    code: string;           // Machine-readable code
    message: string;        // Human-readable message
    details?: any;          // Additional context
    timestamp: string;      // ISO timestamp
    request_id?: string;    // For debugging
  };
  status: number;          // HTTP status code
}

// Authentication Types
export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  token_type: 'Bearer';
}

export interface User {
  id: string;
  username: string;
  role: 'admin' | 'viewer';
  permissions: string[];
}

// System Status Types
export interface SystemStatus {
  service: ServiceHealth;
  camera: CameraStatus;
  storage: StorageStatus;
  resources: ResourceMetrics;
  timestamp: string;
}

export interface ServiceHealth {
  capture: 'running' | 'stopped' | 'error';
  processing: 'running' | 'stopped' | 'error';
  camera: 'connected' | 'disconnected' | 'error';
}

export interface CameraStatus {
  isConnected: boolean;
  model: string;
  resolution: {
    width: number;
    height: number;
  };
  currentSettings: CameraSettings;
}

export interface StorageStatus {
  used: number;
  total: number;
  available: number;
  percentage: number;
}

export interface ResourceMetrics {
  cpu: {
    usage: number;
    temperature: number;
  };
  memory: {
    used: number;
    total: number;
    percentage: number;
  };
  disk: {
    io_read: number;
    io_write: number;
  };
}

// Capture Types
export interface CaptureProgress {
  isActive: boolean;
  nextCaptureIn: number;
  currentSettings: CameraSettings;
  capturesCompleted: number;
  totalCaptures?: number;
  estimatedCompletion?: string;
}

export interface CameraSettings {
  iso: number;
  exposureTime: string;
  aperture?: string;
  whiteBalance: 'auto' | 'daylight' | 'cloudy' | 'tungsten' | 'fluorescent';
  imageFormat: 'jpeg' | 'raw' | 'jpeg+raw';
  quality: number;
  hdr: {
    enabled: boolean;
    brackets: number;
    evSteps: number;
  };
}

export interface ScheduleRule {
  id: string;
  name: string;
  enabled: boolean;
  trigger: {
    type: 'interval' | 'astronomical' | 'conditional';
    interval?: number;
    astronomical?: 'sunrise' | 'sunset' | 'golden_hour' | 'blue_hour';
    conditions?: WeatherCondition[];
  };
  settings: CameraSettings;
  location?: {
    latitude: number;
    longitude: number;
    timezone: string;
  };
}

export interface WeatherCondition {
  parameter: 'cloud_cover' | 'wind_speed' | 'temperature' | 'humidity';
  operator: 'lt' | 'lte' | 'gt' | 'gte' | 'eq';
  value: number;
}

// Gallery Types
export interface TimelapseSequence {
  id: string;
  name: string;
  startTime: string;
  endTime: string;
  captureCount: number;
  thumbnail: string;
  metadata: SequenceMetadata;
  status: 'capturing' | 'processing' | 'completed' | 'failed';
}

export interface SequenceMetadata {
  location?: {
    latitude: number;
    longitude: number;
    name: string;
  };
  weather?: {
    condition: string;
    temperature: number;
    humidity: number;
    wind_speed: number;
  };
  settings: CameraSettings;
  duration: number;
  fileSize: number;
}

export interface VideoGenerationJob {
  id: string;
  sequenceId: string;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  progress: number;
  settings: VideoSettings;
  outputPath?: string;
  error?: string;
}

export interface VideoSettings {
  frameRate: number;
  resolution: '720p' | '1080p' | '4k';
  format: 'mp4' | 'webm' | 'mov';
  quality: 'low' | 'medium' | 'high' | 'ultra';
  stabilization: boolean;
  colorGrading?: string;
}

// Analytics Types
export interface PerformanceAnalytics {
  captureSuccess: {
    rate: number;
    trend: number[];
    lastWeek: number;
  };
  resourceUsage: {
    cpu: TrendData;
    memory: TrendData;
    storage: TrendData;
  };
  weatherCorrelation: {
    bestConditions: WeatherCondition[];
    successByCondition: Record<string, number>;
  };
}

export interface TrendData {
  current: number;
  average: number;
  trend: number[];
  timestamps: string[];
}

// WebSocket Event Types
export interface WebSocketEvent {
  type: string;
  timestamp: string;
  data: any;
  source: 'capture' | 'processing';
}

export type DashboardEvent =
  | { type: 'system.status'; data: SystemStatus }
  | { type: 'capture.progress'; data: CaptureProgress }
  | { type: 'capture.complete'; data: { sequenceId: string; captureCount: number } }
  | { type: 'resource.update'; data: ResourceMetrics }
  | { type: 'error.occurred'; data: APIError }
  | { type: 'job.status'; data: VideoGenerationJob };

// Configuration Types
export interface AppConfig {
  apiUrls: {
    capture: string;
    processing: string;
    websocket: string;
  };
  features: {
    darkMode: boolean;
    realTimeUpdates: boolean;
    notifications: boolean;
  };
  camera: {
    defaultSettings: CameraSettings;
    availableISO: number[];
    maxExposureTime: number;
  };
}

// Utility Types
export type LoadingState = 'idle' | 'loading' | 'success' | 'error';

export interface PaginatedResponse<T> {
  data: T[];
  pagination: {
    page: number;
    size: number;
    total: number;
    pages: number;
  };
}

export interface SearchFilters {
  dateRange?: {
    start: string;
    end: string;
  };
  location?: string;
  weather?: string;
  tags?: string[];
}

// Component Props Types
export interface ComponentProps {
  className?: string;
  children?: React.ReactNode;
}

export interface ButtonProps extends ComponentProps {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'golden';
  size?: 'sm' | 'md' | 'lg';
  disabled?: boolean;
  loading?: boolean;
  onClick?: () => void;
}

export interface CardProps extends ComponentProps {
  title?: string;
  subtitle?: string;
  actions?: React.ReactNode;
}

export interface StatusIndicatorProps extends ComponentProps {
  status: 'active' | 'paused' | 'error' | 'success';
  label: string;
  pulse?: boolean;
}
