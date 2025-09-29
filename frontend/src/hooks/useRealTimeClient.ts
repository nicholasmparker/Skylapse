/**
 * Real-Time Client Hook
 * Professional Mountain Timelapse Camera System
 *
 * Simplified real-time client using RealTimeService directly.
 */

import { useEffect, useState, useCallback } from 'react';
import { realTimeService, ConnectionState, EventType } from '../services/RealTimeService';

export interface UseRealTimeClientReturn {
  connectionState: {
    isConnected: boolean;
    isOnline: boolean;
    connectionQuality: string;
    lastConnected: Date | null;
    reconnectAttempts: number;
    isReconnecting: boolean;
    error: string | null;
  };
  reconnect: () => Promise<void>;
  sendCommand: (command: string, data: any) => Promise<void>;
}

export function useRealTimeClient(
  accessToken: string | null,
  config: any = {}
): UseRealTimeClientReturn {
  const [connectionState, setConnectionState] = useState<ConnectionState>({
    status: 'offline',
    transport: 'sse',
    quality: 'excellent',
    lastSeen: new Date(),
    retryCount: 0,
    latency: 0
  });
  const [error, setError] = useState<string | null>(null);
  const [isReconnecting, setIsReconnecting] = useState(false);

  // Connect to real-time service
  useEffect(() => {
    if (!accessToken) return;

    const unsubscribe = realTimeService.onConnectionChange((state) => {
      setConnectionState(state);
      setError(null);
    });

    // Connect the service
    realTimeService.connect().catch((err) => {
      setError(err.message);
    });

    return () => {
      unsubscribe();
    };
  }, [accessToken]);

  const reconnect = useCallback(async () => {
    setIsReconnecting(true);
    setError(null);
    try {
      await realTimeService.reconnect();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsReconnecting(false);
    }
  }, []);

  const sendCommand = useCallback(async (command: string, data: any) => {
    try {
      await realTimeService.sendCommand(command, data);
    } catch (err: any) {
      setError(err.message);
      throw err;
    }
  }, []);

  return {
    connectionState: {
      isConnected: connectionState.status === 'online',
      isOnline: connectionState.status !== 'offline',
      connectionQuality: connectionState.quality,
      lastConnected: connectionState.lastSeen,
      reconnectAttempts: connectionState.retryCount,
      isReconnecting,
      error,
    },
    reconnect,
    sendCommand,
  };
}
