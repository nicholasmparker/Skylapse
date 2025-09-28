/**
 * Production Real-Time Connection Hook
 * Replaces broken Socket.IO implementation with bulletproof real-time architecture
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import {
  RealTimeService,
  realTimeService,
  EventType,
  SkylapsEvent,
  ConnectionState
} from '../services/RealTimeService';
import type {
  SystemStatus,
  ResourceMetrics,
  CaptureProgress,
  TimelapseSequence
} from '../api/types';

interface EnvironmentalData {
  sunElevation: number;
  sunAzimuth: number;
  isGoldenHour: boolean;
  isBluHour: boolean;
  nextGoldenHour: string | null;
  temperature: number;
  humidity: number;
  cloudCover: number;
  windSpeed: number;
}

interface UseRealTimeConnectionReturn {
  // Connection state
  isConnected: boolean;
  connectionState: ConnectionState;
  error: string | null;

  // Data
  systemStatus: SystemStatus | null;
  resourceMetrics: ResourceMetrics[];
  environmentalData: EnvironmentalData | null;
  captureProgress: CaptureProgress | null;
  recentCaptures: TimelapseSequence[];

  // Actions
  reconnect: () => Promise<void>;
  sendCommand: (command: string, data: any) => Promise<void>;
  clearError: () => void;
}

interface UseRealTimeConnectionOptions {
  cameraId?: string;
  autoConnect?: boolean;
  maxMetricsHistory?: number;
}

export const useRealTimeConnection = (
  options: UseRealTimeConnectionOptions = {}
): UseRealTimeConnectionReturn => {
  const {
    cameraId,
    autoConnect = true,
    maxMetricsHistory = 100
  } = options;

  // Connection state
  const [connectionState, setConnectionState] = useState<ConnectionState>({
    status: 'offline',
    transport: 'sse',
    quality: 'excellent',
    lastSeen: new Date(),
    retryCount: 0,
    latency: 0
  });
  const [error, setError] = useState<string | null>(null);

  // Data state
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [resourceMetrics, setResourceMetrics] = useState<ResourceMetrics[]>([]);
  const [environmentalData, setEnvironmentalData] = useState<EnvironmentalData | null>(null);
  const [captureProgress, setCaptureProgress] = useState<CaptureProgress | null>(null);
  const [recentCaptures, setRecentCaptures] = useState<TimelapseSequence[]>([]);

  // Refs for cleanup
  const unsubscribeRefs = useRef<(() => void)[]>([]);

  // Derived state
  const isConnected = connectionState.status === 'online';

  // Event handlers
  const handleSystemStatus = useCallback((event: SkylapsEvent) => {
    setSystemStatus(event.data);
  }, []);

  const handleCaptureProgress = useCallback((event: SkylapsEvent) => {
    setCaptureProgress(event.data);
  }, []);

  const handleResourceUpdate = useCallback((event: SkylapsEvent) => {
    setResourceMetrics(prev => {
      const newMetrics = [...prev, event.data];
      return newMetrics.slice(-maxMetricsHistory);
    });
  }, [maxMetricsHistory]);

  const handleCaptureComplete = useCallback((event: SkylapsEvent) => {
    // Refresh recent captures when a new one completes
    fetchRecentCaptures();

    // Clear capture progress
    setCaptureProgress(null);
  }, []);

  const handleEnvironmentalUpdate = useCallback((event: SkylapsEvent) => {
    setEnvironmentalData(event.data);
  }, []);

  const handleSystemError = useCallback((event: SkylapsEvent) => {
    console.error('System error event:', event.data);
    setError(event.data.message || 'System error occurred');
  }, []);

  const handleSystemWarning = useCallback((event: SkylapsEvent) => {
    console.warn('System warning:', event.data);
    // Warnings don't set error state, just log them
  }, []);

  const handleConnectionQuality = useCallback((event: SkylapsEvent) => {
    // Connection quality is handled by the service itself
    // This handler is for additional UI feedback if needed
  }, []);

  // Fetch functions for REST API fallbacks
  const fetchRecentCaptures = useCallback(async () => {
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL}/api/v1/gallery/recent?limit=6`);
      if (response.ok) {
        const result = await response.json();
        setRecentCaptures(result.data || []);
      }
    } catch (error) {
      console.error('Failed to fetch recent captures:', error);
    }
  }, []);

  const fetchEnvironmentalData = useCallback(async () => {
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL}/api/v1/environmental/current`);
      if (response.ok) {
        const result = await response.json();
        setEnvironmentalData(result.data);
      }
    } catch (error) {
      console.error('Failed to fetch environmental data:', error);
    }
  }, []);

  const fetchSystemStatus = useCallback(async () => {
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL}/api/v1/system/status`);
      if (response.ok) {
        const result = await response.json();
        setSystemStatus(result.data);
      }
    } catch (error) {
      console.error('Failed to fetch system status:', error);
    }
  }, []);

  // Actions
  const reconnect = useCallback(async () => {
    setError(null);
    try {
      await realTimeService.reconnect();
    } catch (error) {
      console.error('Reconnect failed:', error);
      setError('Failed to reconnect to real-time service');
    }
  }, []);

  const sendCommand = useCallback(async (command: string, data: any) => {
    try {
      await realTimeService.sendCommand(command, data);
    } catch (error) {
      console.error('Command failed:', error);
      setError(`Command failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
      throw error;
    }
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  // Setup subscriptions and connection
  useEffect(() => {
    // Subscribe to connection state changes
    const connectionUnsubscribe = realTimeService.onConnectionChange(setConnectionState);
    unsubscribeRefs.current.push(connectionUnsubscribe);

    // Subscribe to events
    const eventSubscriptions = [
      { type: EventType.SYSTEM_STATUS, handler: handleSystemStatus },
      { type: EventType.CAPTURE_PROGRESS, handler: handleCaptureProgress },
      { type: EventType.RESOURCE_UPDATE, handler: handleResourceUpdate },
      { type: EventType.CAPTURE_COMPLETED, handler: handleCaptureComplete },
      { type: EventType.ENVIRONMENTAL_UPDATE, handler: handleEnvironmentalUpdate },
      { type: EventType.SYSTEM_ERROR, handler: handleSystemError },
      { type: EventType.SYSTEM_WARNING, handler: handleSystemWarning },
      { type: EventType.CONNECTION_QUALITY, handler: handleConnectionQuality },
    ];

    eventSubscriptions.forEach(({ type, handler }) => {
      const unsubscribe = realTimeService.subscribe(type, handler);
      unsubscribeRefs.current.push(unsubscribe);
    });

    // Connect if auto-connect is enabled
    if (autoConnect) {
      realTimeService.connect().catch(error => {
        console.error('Initial connection failed:', error);
        setError('Failed to establish real-time connection');
      });
    }

    // Cleanup function
    return () => {
      unsubscribeRefs.current.forEach(unsubscribe => unsubscribe());
      unsubscribeRefs.current = [];
    };
  }, [
    autoConnect,
    handleSystemStatus,
    handleCaptureProgress,
    handleResourceUpdate,
    handleCaptureComplete,
    handleEnvironmentalUpdate,
    handleSystemError,
    handleSystemWarning,
    handleConnectionQuality
  ]);

  // Fallback data fetching when offline or degraded
  useEffect(() => {
    if (connectionState.status === 'offline' || connectionState.status === 'degraded') {
      // Fetch initial data via REST API
      Promise.all([
        fetchSystemStatus(),
        fetchRecentCaptures(),
        fetchEnvironmentalData()
      ]).catch(error => {
        console.error('Failed to fetch fallback data:', error);
        setError('Unable to load data. Check your connection.');
      });

      // Set up periodic refresh for offline mode
      const interval = setInterval(() => {
        if (connectionState.status === 'offline') {
          Promise.all([
            fetchSystemStatus(),
            fetchEnvironmentalData()
          ]).catch(error => {
            console.error('Periodic data fetch failed:', error);
          });
        }
      }, 30000); // Refresh every 30 seconds when offline

      return () => clearInterval(interval);
    }
  }, [
    connectionState.status,
    fetchSystemStatus,
    fetchRecentCaptures,
    fetchEnvironmentalData
  ]);

  // Performance monitoring and adaptation
  useEffect(() => {
    if (connectionState.quality === 'poor' && connectionState.transport === 'sse') {
      console.warn('Poor connection quality detected, consider fallback options');
      // Could trigger automatic fallback to more efficient transport
    }
  }, [connectionState.quality, connectionState.transport]);

  return {
    // Connection state
    isConnected,
    connectionState,
    error,

    // Data
    systemStatus,
    resourceMetrics,
    environmentalData,
    captureProgress,
    recentCaptures,

    // Actions
    reconnect,
    sendCommand,
    clearError
  };
};

export default useRealTimeConnection;
