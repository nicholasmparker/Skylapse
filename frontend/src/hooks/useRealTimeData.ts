/**
 * Real-time data hook for WebSocket integration
 * Professional Mountain Timelapse Camera System
 */

import { useState, useEffect, useCallback } from 'react';
import { io, Socket } from 'socket.io-client';
import {
  SystemStatus,
  ResourceMetrics,
  CaptureProgress,
  TimelapseSequence,
  DashboardEvent
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

interface UseRealTimeDataReturn {
  systemStatus: SystemStatus | null;
  resourceMetrics: ResourceMetrics[];
  environmentalData: EnvironmentalData | null;
  captureProgress: CaptureProgress | null;
  recentCaptures: TimelapseSequence[];
  isConnected: boolean;
  error: string | null;
  reconnect: () => void;
}

const WEBSOCKET_URL = process.env.NODE_ENV === 'production'
  ? 'wss://api.skylapse.dev'
  : 'ws://localhost:8000';

export const useRealTimeData = (): UseRealTimeDataReturn => {
  const [socket, setSocket] = useState<Socket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Data state
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [resourceMetrics, setResourceMetrics] = useState<ResourceMetrics[]>([]);
  const [environmentalData, setEnvironmentalData] = useState<EnvironmentalData | null>(null);
  const [captureProgress, setCaptureProgress] = useState<CaptureProgress | null>(null);
  const [recentCaptures, setRecentCaptures] = useState<TimelapseSequence[]>([]);

  const handleEvent = useCallback((event: DashboardEvent) => {
    console.log('Dashboard event received:', event.type, event.data);

    switch (event.type) {
      case 'system.status':
        setSystemStatus(event.data);
        break;

      case 'capture.progress':
        setCaptureProgress(event.data);
        break;

      case 'resource.update':
        setResourceMetrics(prev => {
          const newMetrics = [...prev, event.data];
          // Keep only last 100 data points for performance
          return newMetrics.slice(-100);
        });
        break;

      case 'capture.complete':
        // Refresh recent captures when a new one completes
        fetchRecentCaptures();
        break;

      case 'error.occurred':
        console.error('System error:', event.data);
        setError(event.data.error.message);
        break;

      default:
        console.log('Unknown event type:', event.type);
    }
  }, []);

  const fetchRecentCaptures = useCallback(async () => {
    try {
      const response = await fetch('/api/v1/gallery/recent?limit=6');
      if (response.ok) {
        const captures = await response.json();
        setRecentCaptures(captures.data || []);
      }
    } catch (error) {
      console.error('Failed to fetch recent captures:', error);
    }
  }, []);

  const fetchEnvironmentalData = useCallback(async () => {
    try {
      const response = await fetch('/api/v1/environmental/current');
      if (response.ok) {
        const data = await response.json();
        setEnvironmentalData(data.data);
      }
    } catch (error) {
      console.error('Failed to fetch environmental data:', error);
    }
  }, []);

  const connectWebSocket = useCallback(() => {
    console.log('Connecting to WebSocket:', WEBSOCKET_URL);

    const newSocket = io(WEBSOCKET_URL, {
      transports: ['websocket', 'polling'],
      timeout: 10000,
      auth: {
        token: localStorage.getItem('auth_token')
      }
    });

    newSocket.on('connect', () => {
      console.log('WebSocket connected');
      setIsConnected(true);
      setError(null);

      // Subscribe to dashboard events
      newSocket.emit('subscribe', 'dashboard');

      // Fetch initial data
      fetchRecentCaptures();
      fetchEnvironmentalData();
    });

    newSocket.on('disconnect', (reason) => {
      console.log('WebSocket disconnected:', reason);
      setIsConnected(false);

      if (reason === 'io server disconnect') {
        // Server initiated disconnect, try to reconnect
        setTimeout(() => newSocket.connect(), 5000);
      }
    });

    newSocket.on('connect_error', (error) => {
      console.error('WebSocket connection error:', error);
      setError('Failed to connect to real-time updates');
      setIsConnected(false);
    });

    // Listen for dashboard events
    newSocket.on('dashboard-event', handleEvent);

    // Handle authentication errors
    newSocket.on('auth_error', (error) => {
      console.error('WebSocket auth error:', error);
      setError('Authentication failed. Please refresh the page.');
    });

    setSocket(newSocket);

    return newSocket;
  }, [handleEvent, fetchRecentCaptures, fetchEnvironmentalData]);

  const reconnect = useCallback(() => {
    if (socket) {
      socket.disconnect();
    }
    setError(null);
    connectWebSocket();
  }, [socket, connectWebSocket]);

  useEffect(() => {
    const newSocket = connectWebSocket();

    // Cleanup on unmount
    return () => {
      if (newSocket) {
        newSocket.disconnect();
      }
    };
  }, [connectWebSocket]);

  // Periodic data refresh for non-WebSocket data
  useEffect(() => {
    const interval = setInterval(() => {
      if (isConnected) {
        fetchEnvironmentalData();
      }
    }, 60000); // Update environmental data every minute

    return () => clearInterval(interval);
  }, [isConnected, fetchEnvironmentalData]);

  return {
    systemStatus,
    resourceMetrics,
    environmentalData,
    captureProgress,
    recentCaptures,
    isConnected,
    error,
    reconnect
  };
};
