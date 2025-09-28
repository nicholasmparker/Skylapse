/**
 * Real-Time Client Hook
 * Professional Mountain Timelapse Camera System
 *
 * React hook for using the real-time client with authentication integration.
 */

import { useEffect, useMemo, useRef } from 'react';
import { useConnectionState, type ConnectionConfig } from './useConnectionState';
import { createRealTimeClient, type RealTimeClient, type RealTimeClientConfig } from '../services/RealTimeClient';
import { config } from '../config/environment';

export interface UseRealTimeClientReturn {
  client: RealTimeClient;
  connectionState: {
    isConnected: boolean;
    isOnline: boolean;
    connectionQuality: string;
    lastConnected: Date | null;
    reconnectAttempts: number;
    isReconnecting: boolean;
    error: string | null;
  };
}

export function useRealTimeClient(
  accessToken: string | null,
  clientConfig: RealTimeClientConfig = {}
): UseRealTimeClientReturn {
  const connectionConfig: ConnectionConfig = useMemo(() => ({
    serverUrl: clientConfig.wsUrl || config.WS_URL,
    maxReconnectAttempts: 10,
    baseReconnectDelay: 1000,
    maxReconnectDelay: 30000,
    connectionTimeoutMs: 60000, // Increased to 60s for debugging
    pingIntervalMs: 30000,
    healthCheckIntervalMs: 60000,
    ...clientConfig
  }), [clientConfig.wsUrl, clientConfig.maxReconnectAttempts, clientConfig.baseReconnectDelay, clientConfig.maxReconnectDelay, clientConfig.connectionTimeoutMs, clientConfig.pingIntervalMs, clientConfig.healthCheckIntervalMs]);

  const connectionState = useConnectionState(connectionConfig);
  const clientRef = useRef<RealTimeClient | null>(null);
  const hasConnectedRef = useRef(false);
  const isConnectingRef = useRef(false);

  // Create client only once
  if (!clientRef.current) {
    clientRef.current = createRealTimeClient(connectionState, clientConfig);
  }

  // Connection management with proper cleanup
  useEffect(() => {
    const token = accessToken || 'dev-token-for-websocket-connection';
    const client = clientRef.current!;

    // Skip if already connecting/connected or no token
    if (!token || isConnectingRef.current || hasConnectedRef.current) {
      return;
    }

    // Development mode detection for React Strict Mode
    const isDevelopment = import.meta.env.DEV;
    if (isDevelopment) {
      console.log('🔧 Development mode detected - Socket.IO configured for React Strict Mode');
    }

    // Connect with proper error handling
    const connectClient = async () => {
      isConnectingRef.current = true;
      try {
        await client.connect(token);
        hasConnectedRef.current = true;
        console.log('✅ Real-time client connected successfully');
      } catch (error) {
        console.error('❌ Connection failed:', error);
        hasConnectedRef.current = false;
      } finally {
        isConnectingRef.current = false;
      }
    };

    connectClient();

    // Cleanup function
    return () => {
      if (hasConnectedRef.current) {
        console.log('🔌 Disconnecting real-time client');
        client.disconnect();
        hasConnectedRef.current = false;
        isConnectingRef.current = false;
      }
    };
  }, [accessToken]); // Only depend on accessToken, not client

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (clientRef.current && hasConnectedRef.current) {
        clientRef.current.disconnect();
        hasConnectedRef.current = false;
        isConnectingRef.current = false;
      }
    };
  }, []);

  return {
    client: clientRef.current!,
    connectionState: {
      isConnected: connectionState.isWebSocketConnected,
      isOnline: connectionState.isOnline,
      connectionQuality: connectionState.connectionQuality,
      lastConnected: connectionState.lastConnected,
      reconnectAttempts: connectionState.reconnectAttempts,
      isReconnecting: connectionState.isReconnecting,
      error: connectionState.error,
    }
  };
}
