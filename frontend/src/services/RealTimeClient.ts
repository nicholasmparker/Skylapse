/**
 * Secure Real-Time Client for Skylapse Dashboard
 * Professional Mountain Timelapse Camera System
 *
 * Provides authenticated WebSocket connections with automatic reconnection,
 * offline support, and bulletproof error handling for mountain deployments.
 */

import { useConnectionState, type ConnectionConfig } from '../hooks/useConnectionState';
import { config } from '../config/environment';
import type { DashboardEvent, SystemStatus, ResourceMetrics, CaptureProgress } from '../api/types';

export interface RealTimeEventHandlers {
  onSystemStatus?: (status: SystemStatus) => void;
  onCaptureProgress?: (progress: CaptureProgress) => void;
  onResourceUpdate?: (metrics: ResourceMetrics) => void;
  onCaptureComplete?: (data: { sequenceId: string; captureCount: number }) => void;
  onError?: (error: any) => void;
  onConnectionChange?: (connected: boolean) => void;
}

export interface RealTimeClientConfig extends Partial<ConnectionConfig> {
  autoConnect?: boolean;
  subscribeToEvents?: string[];
  eventHandlers?: RealTimeEventHandlers;
}

export class RealTimeClient {
  private connectionState: ReturnType<typeof useConnectionState>;
  private eventHandlers: RealTimeEventHandlers = {};
  private subscribedEvents: Set<string> = new Set();
  private isInitialized = false;

  constructor(
    connectionState: ReturnType<typeof useConnectionState>,
    config: RealTimeClientConfig = {}
  ) {
    this.connectionState = connectionState;
    this.eventHandlers = config.eventHandlers || {};

    // Subscribe to default events
    const defaultEvents = [
      'system.status',
      'capture.progress',
      'resource.update',
      'capture.complete',
      'error.occurred'
    ];

    const eventsToSubscribe = config.subscribeToEvents || defaultEvents;
    eventsToSubscribe.forEach(event => this.subscribeToEvent(event));

    this.setupEventHandlers();
    this.isInitialized = true;
  }

  private setupEventHandlers() {
    // Handle dashboard events
    this.connectionState.subscribe('dashboard-event', this.handleDashboardEvent.bind(this));

    // Handle authentication errors
    this.connectionState.subscribe('auth_error', (error) => {
      console.error('Real-time authentication error:', error);
      this.eventHandlers.onError?.(error);
    });

    // Handle connection state changes
    this.connectionState.subscribe('connection_change', (connected: boolean) => {
      this.eventHandlers.onConnectionChange?.(connected);
    });
  }

  private handleDashboardEvent(event: DashboardEvent) {
    console.log('Dashboard event received:', event.type, event.data);

    switch (event.type) {
      case 'system.status':
        this.eventHandlers.onSystemStatus?.(event.data);
        break;

      case 'capture.progress':
        this.eventHandlers.onCaptureProgress?.(event.data);
        break;

      case 'resource.update':
        this.eventHandlers.onResourceUpdate?.(event.data);
        break;

      case 'capture.complete':
        this.eventHandlers.onCaptureComplete?.(event.data);
        break;

      case 'error.occurred':
        console.error('System error event:', event.data);
        this.eventHandlers.onError?.(event.data);
        break;

      default:
        console.log('Unknown dashboard event type:', event.type);
    }
  }

  public async connect(accessToken: string): Promise<void> {
    try {
      await this.connectionState.connect(accessToken);

      // Subscribe to dashboard events once connected
      this.subscribeToDashboard();

      console.log('Real-time client connected successfully');
    } catch (error) {
      console.error('Failed to connect real-time client:', error);
      throw error;
    }
  }

  public disconnect(): void {
    this.connectionState.disconnect();
    console.log('Real-time client disconnected');
  }

  public forceReconnect(): void {
    this.connectionState.forceReconnect();
  }

  public subscribeToDashboard(): boolean {
    return this.connectionState.emit('subscribe', 'dashboard');
  }

  public subscribeToEvent(eventType: string): void {
    if (!this.subscribedEvents.has(eventType)) {
      this.subscribedEvents.add(eventType);

      if (this.connectionState.isWebSocketConnected) {
        this.connectionState.emit('subscribe', eventType);
      }
    }
  }

  public unsubscribeFromEvent(eventType: string): void {
    if (this.subscribedEvents.has(eventType)) {
      this.subscribedEvents.delete(eventType);

      if (this.connectionState.isWebSocketConnected) {
        this.connectionState.emit('unsubscribe', eventType);
      }
    }
  }

  public updateEventHandlers(handlers: Partial<RealTimeEventHandlers>): void {
    this.eventHandlers = { ...this.eventHandlers, ...handlers };
  }

  public sendEvent(eventType: string, data: any): boolean {
    return this.connectionState.emit(eventType, data);
  }

  public async pingConnection(): Promise<number | null> {
    return this.connectionState.sendPing();
  }

  // Getters for connection state
  public get isConnected(): boolean {
    return this.connectionState.isWebSocketConnected;
  }

  public get isOnline(): boolean {
    return this.connectionState.isOnline;
  }

  public get connectionQuality(): string {
    return this.connectionState.connectionQuality;
  }

  public get reconnectAttempts(): number {
    return this.connectionState.reconnectAttempts;
  }

  public get isReconnecting(): boolean {
    return this.connectionState.isReconnecting;
  }

  public get error(): string | null {
    return this.connectionState.error;
  }

  public get lastConnected(): Date | null {
    return this.connectionState.lastConnected;
  }

  public clearError(): void {
    this.connectionState.clearError();
  }
}

// Factory function to create a configured real-time client
export function createRealTimeClient(
  connectionState: ReturnType<typeof useConnectionState>,
  config: RealTimeClientConfig = {}
): RealTimeClient {
  return new RealTimeClient(connectionState, {
    autoConnect: true,
    subscribeToEvents: [
      'system.status',
      'capture.progress',
      'resource.update',
      'capture.complete',
      'error.occurred'
    ],
    ...config
  });
}

// Note: This hook is moved to a separate file to avoid circular dependencies
// See hooks/useRealTimeClient.ts

// Production configuration for Docker container networking
export const PRODUCTION_REALTIME_CONFIG: RealTimeClientConfig = {
  wsUrl: config.WS_URL, // Uses proper Docker service names
  maxReconnectAttempts: 15, // More attempts for mountain deployments
  baseReconnectDelay: 2000, // Longer initial delay for unstable connections
  maxReconnectDelay: 60000, // Up to 1 minute for very poor connectivity
  connectionTimeoutMs: 15000, // Longer timeout for slow mountain networks
  pingIntervalMs: 45000, // Less frequent pings to reduce bandwidth usage
  healthCheckIntervalMs: 120000, // 2-minute health checks
  autoConnect: true,
  subscribeToEvents: [
    'system.status',
    'capture.progress',
    'resource.update',
    'capture.complete',
    'error.occurred',
    'environmental.update'
  ]
};
