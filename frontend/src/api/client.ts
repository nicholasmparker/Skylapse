/**
 * Skylapse API Client
 * Professional Mountain Timelapse Camera System
 */

import type {
  APIResponse,
  APIError,
  AuthTokens,
  SystemStatus,
  CaptureProgress,
  CameraSettings,
  ScheduleRule,
  TimelapseSequence,
  VideoGenerationJob,
  PerformanceAnalytics,
  PaginatedResponse,
  SearchFilters
} from './types';

class APIClient {
  private baseURL: string;
  private accessToken: string | null = null;

  constructor(baseURL: string) {
    this.baseURL = baseURL.replace(/\/$/, ''); // Remove trailing slash
  }

  setAccessToken(token: string | null) {
    this.accessToken = token;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<APIResponse<T>> {
    const url = `${this.baseURL}${endpoint}`;
    const headers = new Headers(options.headers);

    // Add authentication header
    if (this.accessToken) {
      headers.set('Authorization', `Bearer ${this.accessToken}`);
    }

    // Set content type for JSON requests
    if (options.body && !headers.has('Content-Type')) {
      headers.set('Content-Type', 'application/json');
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new APIClientError(data as APIError, response.status);
      }

      return {
        data,
        status: response.status,
        message: response.statusText,
      };
    } catch (error) {
      if (error instanceof APIClientError) {
        throw error;
      }

      // Network or parsing error
      throw new APIClientError(
        {
          error: {
            code: 'NETWORK_ERROR',
            message: 'Failed to connect to server',
            timestamp: new Date().toISOString(),
          },
          status: 0,
        },
        0
      );
    }
  }

  // GET request helper
  async get<T>(endpoint: string): Promise<APIResponse<T>> {
    return this.request<T>(endpoint, { method: 'GET' });
  }

  // POST request helper
  async post<T>(endpoint: string, data?: any): Promise<APIResponse<T>> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  // PUT request helper
  async put<T>(endpoint: string, data?: any): Promise<APIResponse<T>> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  // DELETE request helper
  async delete<T>(endpoint: string): Promise<APIResponse<T>> {
    return this.request<T>(endpoint, { method: 'DELETE' });
  }
}

class CaptureAPI extends APIClient {
  // Authentication
  async login(username: string, password: string): Promise<APIResponse<AuthTokens>> {
    return this.post<AuthTokens>('/api/auth/login', { username, password });
  }

  async refreshToken(refreshToken: string): Promise<APIResponse<AuthTokens>> {
    return this.post<AuthTokens>('/api/auth/refresh', { refresh_token: refreshToken });
  }

  async logout(): Promise<APIResponse<void>> {
    return this.post<void>('/api/auth/logout');
  }

  // Dashboard data
  async getDashboardStatus(): Promise<APIResponse<SystemStatus>> {
    return this.get<SystemStatus>('/api/dashboard/status');
  }

  async getCaptureProgress(): Promise<APIResponse<CaptureProgress>> {
    return this.get<CaptureProgress>('/api/dashboard/progress');
  }

  // Camera settings
  async getCameraSettings(): Promise<APIResponse<CameraSettings>> {
    return this.get<CameraSettings>('/api/settings');
  }

  async updateCameraSettings(settings: Partial<CameraSettings>): Promise<APIResponse<CameraSettings>> {
    return this.put<CameraSettings>('/api/settings', settings);
  }

  // Manual capture
  async triggerCapture(): Promise<APIResponse<{ capture_id: string }>> {
    return this.post<{ capture_id: string }>('/api/capture/trigger');
  }

  async stopCapture(): Promise<APIResponse<void>> {
    return this.post<void>('/api/capture/stop');
  }

  // Schedule management
  async getSchedule(): Promise<APIResponse<ScheduleRule[]>> {
    return this.get<ScheduleRule[]>('/api/schedule');
  }

  async createScheduleRule(rule: Omit<ScheduleRule, 'id'>): Promise<APIResponse<ScheduleRule>> {
    return this.post<ScheduleRule>('/api/schedule', rule);
  }

  async updateScheduleRule(id: string, rule: Partial<ScheduleRule>): Promise<APIResponse<ScheduleRule>> {
    return this.put<ScheduleRule>(`/api/schedule/${id}`, rule);
  }

  async deleteScheduleRule(id: string): Promise<APIResponse<void>> {
    return this.delete<void>(`/api/schedule/${id}`);
  }
}

class ProcessingAPI extends APIClient {
  // Gallery management
  async getTimelapseSequences(filters?: SearchFilters): Promise<APIResponse<PaginatedResponse<TimelapseSequence>>> {
    const params = new URLSearchParams();
    if (filters?.dateRange) {
      params.set('start_date', filters.dateRange.start);
      params.set('end_date', filters.dateRange.end);
    }
    if (filters?.location) params.set('location', filters.location);
    if (filters?.weather) params.set('weather', filters.weather);
    if (filters?.tags) params.set('tags', filters.tags.join(','));

    const query = params.toString();
    return this.get<PaginatedResponse<TimelapseSequence>>(`/api/gallery/sequences${query ? `?${query}` : ''}`);
  }

  async getSequenceDetails(id: string): Promise<APIResponse<TimelapseSequence>> {
    return this.get<TimelapseSequence>(`/api/gallery/sequences/${id}`);
  }

  async deleteSequence(id: string): Promise<APIResponse<void>> {
    return this.delete<void>(`/api/gallery/sequences/${id}`);
  }

  // Video generation
  async generateVideo(sequenceId: string, settings: any): Promise<APIResponse<VideoGenerationJob>> {
    return this.post<VideoGenerationJob>('/api/gallery/generate', {
      sequence_id: sequenceId,
      settings,
    });
  }

  async getVideoJobs(): Promise<APIResponse<VideoGenerationJob[]>> {
    return this.get<VideoGenerationJob[]>('/api/gallery/jobs');
  }

  async getJobStatus(jobId: string): Promise<APIResponse<VideoGenerationJob>> {
    return this.get<VideoGenerationJob>(`/api/gallery/jobs/${jobId}`);
  }

  // Analytics
  async getPerformanceAnalytics(): Promise<APIResponse<PerformanceAnalytics>> {
    return this.get<PerformanceAnalytics>('/api/analytics/performance');
  }

  async getSystemOverview(): Promise<APIResponse<any>> {
    return this.get<any>('/api/analytics/overview');
  }
}

class WebSocketClient {
  private ws: WebSocket | null = null;
  private url: string;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private eventHandlers: Map<string, ((data: any) => void)[]> = new Map();

  constructor(url: string) {
    this.url = url;
  }

  connect(accessToken?: string): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        const wsUrl = accessToken
          ? `${this.url}?token=${accessToken}`
          : this.url;

        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
          console.log('WebSocket connected');
          this.reconnectAttempts = 0;
          resolve();
        };

        this.ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            this.handleEvent(data);
          } catch (error) {
            console.error('Failed to parse WebSocket message:', error);
          }
        };

        this.ws.onclose = () => {
          console.log('WebSocket disconnected');
          this.attemptReconnect();
        };

        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          reject(error);
        };
      } catch (error) {
        reject(error);
      }
    });
  }

  private handleEvent(event: any) {
    const handlers = this.eventHandlers.get(event.type) || [];
    handlers.forEach(handler => handler(event.data));

    // Also call wildcard handlers
    const wildcardHandlers = this.eventHandlers.get('*') || [];
    wildcardHandlers.forEach(handler => handler(event));
  }

  private attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      setTimeout(() => {
        console.log(`Reconnecting... (attempt ${this.reconnectAttempts})`);
        this.connect();
      }, this.reconnectDelay * this.reconnectAttempts);
    }
  }

  subscribe(eventType: string, handler: (data: any) => void) {
    if (!this.eventHandlers.has(eventType)) {
      this.eventHandlers.set(eventType, []);
    }
    this.eventHandlers.get(eventType)!.push(handler);
  }

  unsubscribe(eventType: string, handler: (data: any) => void) {
    const handlers = this.eventHandlers.get(eventType);
    if (handlers) {
      const index = handlers.indexOf(handler);
      if (index > -1) {
        handlers.splice(index, 1);
      }
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}

// Custom error class
class APIClientError extends Error {
  public apiError: APIError;
  public statusCode: number;

  constructor(apiError: APIError, statusCode: number) {
    super(apiError.error.message);
    this.name = 'APIClientError';
    this.apiError = apiError;
    this.statusCode = statusCode;
  }
}

// Main API client class
export class SkylarpseAPIClient {
  private captureBaseURL: string;
  private processingBaseURL: string;
  private wsURL: string;

  public capture: CaptureAPI;
  public processing: ProcessingAPI;
  public websocket: WebSocketClient;

  constructor() {
    this.captureBaseURL = import.meta.env.VITE_CAPTURE_URL || 'http://helios.local:8080';
    this.processingBaseURL = import.meta.env.VITE_API_URL || 'http://localhost:8081';
    this.wsURL = import.meta.env.VITE_WS_URL || 'ws://localhost:8081/ws';

    this.capture = new CaptureAPI(this.captureBaseURL);
    this.processing = new ProcessingAPI(this.processingBaseURL);
    this.websocket = new WebSocketClient(this.wsURL);
  }

  setAccessToken(token: string | null) {
    this.capture.setAccessToken(token);
    this.processing.setAccessToken(token);
  }

  async connectWebSocket(accessToken?: string): Promise<void> {
    return this.websocket.connect(accessToken);
  }

  disconnectWebSocket() {
    this.websocket.disconnect();
  }
}

// Export singleton instance
export const apiClient = new SkylarpseAPIClient();
export { APIClientError };
