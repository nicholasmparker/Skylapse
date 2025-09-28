/**
 * Production Real-Time Service for Skylapse Mountain Camera System
 *
 * Features:
 * - SSE primary, WebSocket fallback, Long polling emergency
 * - JWT authentication with automatic refresh
 * - Offline-first with smart caching
 * - Connection quality adaptation
 * - Multi-camera support
 */

import { config } from '../config/environment';

export interface SkylapsEvent {
  id: string;
  type: EventType;
  timestamp: string;
  camera_id: string;
  sequence_number: number;
  data: EventData;
  priority: 'low' | 'normal' | 'high' | 'critical';
  ttl?: number;
}

export enum EventType {
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

export type EventData = any; // Will be properly typed based on EventType

export interface ConnectionState {
  status: 'online' | 'degraded' | 'offline';
  transport: 'sse' | 'websocket' | 'polling' | 'cache';
  quality: 'excellent' | 'good' | 'poor';
  lastSeen: Date;
  retryCount: number;
  latency: number;
}

export interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  expiresAt: Date | null;
  isRefreshing: boolean;
}

interface EventHandler {
  (event: SkylapsEvent): void;
}

interface ConnectionOptions {
  cameraId?: string;
  subscriptions?: EventType[];
  reconnectInterval?: number;
  maxRetries?: number;
  heartbeatInterval?: number;
}

export class RealTimeService {
  private eventSource: EventSource | null = null;
  private webSocket: WebSocket | null = null;
  private pollingTimer: number | null = null;

  private connectionState: ConnectionState = {
    status: 'offline',
    transport: 'sse',
    quality: 'excellent',
    lastSeen: new Date(),
    retryCount: 0,
    latency: 0
  };

  private authState: AuthState = {
    accessToken: null,
    refreshToken: null,
    expiresAt: null,
    isRefreshing: false
  };

  private eventHandlers = new Map<EventType, Set<EventHandler>>();
  private connectionHandlers = new Set<(state: ConnectionState) => void>();

  private lastSequenceNumber = 0;
  private missedEvents = new Set<number>();
  private eventCache = new Map<string, SkylapsEvent>();

  private options: ConnectionOptions = {
    reconnectInterval: 5000,
    maxRetries: 10,
    heartbeatInterval: 30000
  };

  constructor(options: Partial<ConnectionOptions> = {}) {
    this.options = { ...this.options, ...options };
    this.loadAuthFromStorage();
    this.setupPeriodicTasks();
  }

  /**
   * Initialize the real-time connection with authentication
   */
  async connect(): Promise<void> {
    try {
      await this.ensureAuthenticated();
      await this.establishConnection();
    } catch (error) {
      console.error('Failed to establish real-time connection:', error);
      this.handleConnectionError(error);
    }
  }

  /**
   * Disconnect and cleanup all connections
   */
  disconnect(): void {
    this.closeConnections();
    this.updateConnectionState({ status: 'offline', transport: 'cache' });
  }

  /**
   * Subscribe to specific event types
   */
  subscribe(eventType: EventType, handler: EventHandler): () => void {
    if (!this.eventHandlers.has(eventType)) {
      this.eventHandlers.set(eventType, new Set());
    }

    this.eventHandlers.get(eventType)!.add(handler);

    // Return unsubscribe function
    return () => {
      const handlers = this.eventHandlers.get(eventType);
      if (handlers) {
        handlers.delete(handler);
        if (handlers.size === 0) {
          this.eventHandlers.delete(eventType);
        }
      }
    };
  }

  /**
   * Subscribe to connection state changes
   */
  onConnectionChange(handler: (state: ConnectionState) => void): () => void {
    this.connectionHandlers.add(handler);

    // Immediately call with current state
    handler(this.connectionState);

    // Return unsubscribe function
    return () => {
      this.connectionHandlers.delete(handler);
    };
  }

  /**
   * Send command to server (requires WebSocket)
   */
  async sendCommand(command: string, data: any): Promise<void> {
    if (this.connectionState.status === 'offline') {
      throw new Error('Cannot send command while offline');
    }

    // Ensure WebSocket connection for bidirectional communication
    if (!this.webSocket || this.webSocket.readyState !== WebSocket.OPEN) {
      await this.establishWebSocketConnection();
    }

    const message = {
      type: 'command',
      command,
      data,
      timestamp: new Date().toISOString()
    };

    this.webSocket!.send(JSON.stringify(message));
  }

  /**
   * Get current connection state
   */
  getConnectionState(): ConnectionState {
    return { ...this.connectionState };
  }

  /**
   * Force reconnection attempt
   */
  async reconnect(): Promise<void> {
    this.connectionState.retryCount = 0;
    this.disconnect();
    await this.connect();
  }

  // Private Methods

  private async ensureAuthenticated(): Promise<void> {
    const token = this.getValidToken();
    if (!token) {
      throw new Error('Authentication required');
    }
  }

  private getValidToken(): string | null {
    if (!this.authState.accessToken || !this.authState.expiresAt) {
      return null;
    }

    // Check if token expires within next 5 minutes
    const fiveMinutesFromNow = new Date(Date.now() + 5 * 60 * 1000);
    if (this.authState.expiresAt <= fiveMinutesFromNow) {
      this.refreshTokenIfNeeded();
      return null; // Will be refreshed asynchronously
    }

    return this.authState.accessToken;
  }

  private async refreshTokenIfNeeded(): Promise<void> {
    if (this.authState.isRefreshing || !this.authState.refreshToken) {
      return;
    }

    this.authState.isRefreshing = true;

    try {
      const response = await fetch(`${config.API_URL}/auth/refresh`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          refresh_token: this.authState.refreshToken
        })
      });

      if (response.ok) {
        const { access_token, expires_in } = await response.json();
        this.updateAuthTokens(access_token, this.authState.refreshToken!, expires_in);
      } else {
        // Refresh failed, need to re-authenticate
        this.clearAuth();
        throw new Error('Token refresh failed');
      }
    } catch (error) {
      console.error('Token refresh error:', error);
      this.clearAuth();
    } finally {
      this.authState.isRefreshing = false;
    }
  }

  private async establishConnection(): Promise<void> {
    // Try SSE first (preferred for mountain deployments)
    try {
      await this.establishSSEConnection();
      this.updateConnectionState({
        status: 'online',
        transport: 'sse',
        retryCount: 0
      });
      return;
    } catch (error) {
      console.warn('SSE connection failed, falling back to WebSocket:', error);
    }

    // Fallback to WebSocket
    try {
      await this.establishWebSocketConnection();
      this.updateConnectionState({
        status: 'degraded',
        transport: 'websocket',
        retryCount: 0
      });
      return;
    } catch (error) {
      console.warn('WebSocket connection failed, falling back to polling:', error);
    }

    // Emergency fallback to polling
    try {
      this.establishPollingConnection();
      this.updateConnectionState({
        status: 'degraded',
        transport: 'polling',
        retryCount: 0
      });
    } catch (error) {
      console.error('All connection methods failed:', error);
      this.updateConnectionState({
        status: 'offline',
        transport: 'cache'
      });
      throw error;
    }
  }

  private async establishSSEConnection(): Promise<void> {
    const token = this.getValidToken();
    if (!token) {
      throw new Error('No valid authentication token');
    }

    const sseUrl = new URL(`${config.API_URL}/events/stream`);
    if (this.options.cameraId) {
      sseUrl.searchParams.set('camera_id', this.options.cameraId);
    }

    this.eventSource = new EventSource(sseUrl.toString(), {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    } as any); // Type assertion for headers support

    this.eventSource.onopen = () => {
      console.log('SSE connection established');
      this.updateConnectionState({
        status: 'online',
        lastSeen: new Date()
      });
    };

    this.eventSource.onmessage = (event) => {
      this.handleEvent(JSON.parse(event.data));
    };

    this.eventSource.onerror = (error) => {
      console.error('SSE connection error:', error);
      this.handleConnectionError(error);
    };

    // Wait for connection to be established
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error('SSE connection timeout'));
      }, 10000);

      this.eventSource!.addEventListener('open', () => {
        clearTimeout(timeout);
        resolve();
      });

      this.eventSource!.addEventListener('error', () => {
        clearTimeout(timeout);
        reject(new Error('SSE connection failed'));
      });
    });
  }

  private async establishWebSocketConnection(): Promise<void> {
    const token = this.getValidToken();
    if (!token) {
      throw new Error('No valid authentication token');
    }

    const wsUrl = `${config.WS_URL}?token=${encodeURIComponent(token)}`;
    if (this.options.cameraId) {
      wsUrl + `&camera_id=${encodeURIComponent(this.options.cameraId)}`;
    }

    this.webSocket = new WebSocket(wsUrl);

    this.webSocket.onopen = () => {
      console.log('WebSocket connection established');
      this.updateConnectionState({
        status: 'online',
        lastSeen: new Date()
      });
    };

    this.webSocket.onmessage = (event) => {
      this.handleEvent(JSON.parse(event.data));
    };

    this.webSocket.onerror = (error) => {
      console.error('WebSocket error:', error);
      this.handleConnectionError(error);
    };

    this.webSocket.onclose = (event) => {
      console.log('WebSocket closed:', event.code, event.reason);
      this.handleConnectionError(new Error(`WebSocket closed: ${event.reason}`));
    };

    // Wait for connection to be established
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error('WebSocket connection timeout'));
      }, 10000);

      this.webSocket!.addEventListener('open', () => {
        clearTimeout(timeout);
        resolve();
      });

      this.webSocket!.addEventListener('error', () => {
        clearTimeout(timeout);
        reject(new Error('WebSocket connection failed'));
      });
    });
  }

  private establishPollingConnection(): void {
    const poll = async () => {
      try {
        const token = this.getValidToken();
        if (!token) {
          throw new Error('No valid authentication token');
        }

        const response = await fetch(`${config.API_URL}/events/poll`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });

        if (response.ok) {
          const events = await response.json();
          events.forEach((event: SkylapsEvent) => this.handleEvent(event));

          this.updateConnectionState({
            status: 'degraded',
            lastSeen: new Date()
          });
        } else {
          throw new Error(`Polling failed: ${response.status}`);
        }
      } catch (error) {
        console.error('Polling error:', error);
        this.handleConnectionError(error);
      }
    };

    // Poll every 5 seconds
    this.pollingTimer = window.setInterval(poll, 5000);
    poll(); // Initial poll
  }

  private handleEvent(event: SkylapsEvent): void {
    // Cache event for offline replay
    this.eventCache.set(event.id, event);

    // Check for missing events
    if (event.sequence_number > this.lastSequenceNumber + 1) {
      for (let i = this.lastSequenceNumber + 1; i < event.sequence_number; i++) {
        this.missedEvents.add(i);
      }
    }
    this.lastSequenceNumber = Math.max(this.lastSequenceNumber, event.sequence_number);

    // Update connection quality based on event latency
    const eventTime = new Date(event.timestamp).getTime();
    const now = Date.now();
    const latency = now - eventTime;
    this.updateConnectionQuality(latency);

    // Dispatch to handlers
    const handlers = this.eventHandlers.get(event.type);
    if (handlers) {
      handlers.forEach(handler => {
        try {
          handler(event);
        } catch (error) {
          console.error('Event handler error:', error);
        }
      });
    }

    // Handle special event types
    if (event.type === EventType.HEARTBEAT) {
      this.updateConnectionState({ lastSeen: new Date() });
    }
  }

  private handleConnectionError(error: any): void {
    this.connectionState.retryCount++;

    if (this.connectionState.retryCount >= this.options.maxRetries!) {
      console.error('Max retries exceeded, entering offline mode');
      this.updateConnectionState({
        status: 'offline',
        transport: 'cache'
      });
      return;
    }

    // Exponential backoff with jitter
    const delay = Math.min(
      this.options.reconnectInterval! * Math.pow(2, this.connectionState.retryCount - 1),
      30000 // Max 30 seconds
    ) + Math.random() * 1000;

    console.log(`Reconnecting in ${delay}ms (attempt ${this.connectionState.retryCount})`);

    setTimeout(() => {
      this.establishConnection().catch(err => {
        console.error('Reconnection failed:', err);
      });
    }, delay);
  }

  private updateConnectionQuality(latency: number): void {
    let quality: ConnectionState['quality'];

    if (latency < 500) {
      quality = 'excellent';
    } else if (latency < 2000) {
      quality = 'good';
    } else {
      quality = 'poor';
    }

    if (quality !== this.connectionState.quality) {
      this.updateConnectionState({ quality, latency });
    }
  }

  private updateConnectionState(updates: Partial<ConnectionState>): void {
    this.connectionState = { ...this.connectionState, ...updates };

    // Notify connection state handlers
    this.connectionHandlers.forEach(handler => {
      try {
        handler(this.connectionState);
      } catch (error) {
        console.error('Connection state handler error:', error);
      }
    });
  }

  private closeConnections(): void {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }

    if (this.webSocket) {
      this.webSocket.close();
      this.webSocket = null;
    }

    if (this.pollingTimer) {
      clearInterval(this.pollingTimer);
      this.pollingTimer = null;
    }
  }

  private setupPeriodicTasks(): void {
    // Heartbeat to detect connection issues
    setInterval(() => {
      const timeSinceLastSeen = Date.now() - this.connectionState.lastSeen.getTime();
      if (timeSinceLastSeen > this.options.heartbeatInterval! * 2) {
        console.warn('Connection appears stale, forcing reconnection');
        this.reconnect();
      }
    }, this.options.heartbeatInterval);

    // Cleanup old cached events
    setInterval(() => {
      const cutoff = Date.now() - 24 * 60 * 60 * 1000; // 24 hours
      for (const [id, event] of this.eventCache.entries()) {
        if (new Date(event.timestamp).getTime() < cutoff) {
          this.eventCache.delete(id);
        }
      }
    }, 60 * 60 * 1000); // Run every hour
  }

  private loadAuthFromStorage(): void {
    try {
      const authData = localStorage.getItem('skylapse_auth');
      if (authData) {
        const parsed = JSON.parse(authData);
        this.authState = {
          ...parsed,
          expiresAt: parsed.expiresAt ? new Date(parsed.expiresAt) : null,
          isRefreshing: false
        };
      }
    } catch (error) {
      console.error('Failed to load auth from storage:', error);
    }
  }

  private updateAuthTokens(accessToken: string, refreshToken: string, expiresIn: number): void {
    this.authState = {
      accessToken,
      refreshToken,
      expiresAt: new Date(Date.now() + expiresIn * 1000),
      isRefreshing: false
    };

    // Persist to storage
    localStorage.setItem('skylapse_auth', JSON.stringify({
      accessToken: this.authState.accessToken,
      refreshToken: this.authState.refreshToken,
      expiresAt: this.authState.expiresAt?.toISOString()
    }));
  }

  private clearAuth(): void {
    this.authState = {
      accessToken: null,
      refreshToken: null,
      expiresAt: null,
      isRefreshing: false
    };
    localStorage.removeItem('skylapse_auth');
  }
}

// Singleton instance
export const realTimeService = new RealTimeService();
