/**
 * Simple Real-Time Client Hook
 * Working version without overcomplicated state management
 */

import { useEffect, useRef, useState } from 'react';
import { io, Socket } from 'socket.io-client';
import { config } from '../config/environment';

interface SimpleConnectionState {
  isConnected: boolean;
  isOnline: boolean;
  connectionQuality: string;
  lastConnected: Date | null;
  reconnectAttempts: number;
  isReconnecting: boolean;
  error: string | null;
}

interface UseSimpleRealTimeClientReturn {
  client: Socket | null;
  connectionState: SimpleConnectionState;
}

export function useSimpleRealTimeClient(
  accessToken: string | null,
  eventHandlers: Record<string, (data: any) => void> = {}
): UseSimpleRealTimeClientReturn {
  const socketRef = useRef<Socket | null>(null);
  const [connectionState, setConnectionState] = useState<SimpleConnectionState>({
    isConnected: false,
    isOnline: navigator.onLine,
    connectionQuality: 'offline',
    lastConnected: null,
    reconnectAttempts: 0,
    isReconnecting: false,
    error: null,
  });

  useEffect(() => {
    if (!accessToken) return;

    console.log('🔌 Creating simple Socket.IO connection...');

    const socket = io(config.WS_URL, {
      autoConnect: false,
      forceNew: true,
      transports: ['polling', 'websocket'],
      auth: { token: accessToken },
      query: { token: accessToken }
    });

    socketRef.current = socket;

    // Basic event handlers
    socket.on('connect', () => {
      console.log('✅ Socket.IO connected:', socket.id);
      setConnectionState(prev => ({
        ...prev,
        isConnected: true,
        isReconnecting: false,
        lastConnected: new Date(),
        reconnectAttempts: 0,
        error: null,
        connectionQuality: 'good'
      }));
    });

    socket.on('disconnect', (reason) => {
      console.log('❌ Socket.IO disconnected:', reason);
      setConnectionState(prev => ({
        ...prev,
        isConnected: false,
        connectionQuality: 'offline'
      }));
    });

    socket.on('connect_error', (error) => {
      console.log('💥 Socket.IO connection error:', error);
      setConnectionState(prev => ({
        ...prev,
        error: error.message,
        isReconnecting: false
      }));
    });

    // Register event handlers
    Object.entries(eventHandlers).forEach(([event, handler]) => {
      socket.on(event, handler);
    });

    // Connect
    socket.connect();

    // Cleanup
    return () => {
      console.log('🧹 Cleaning up Socket.IO connection');
      socket.disconnect();
      socketRef.current = null;
    };
  }, [accessToken]);

  // Monitor online status
  useEffect(() => {
    const handleOnline = () => setConnectionState(prev => ({ ...prev, isOnline: true }));
    const handleOffline = () => setConnectionState(prev => ({ ...prev, isOnline: false, connectionQuality: 'offline' }));

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  return {
    client: socketRef.current,
    connectionState
  };
}
