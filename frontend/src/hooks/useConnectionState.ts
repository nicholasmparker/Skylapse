/**
 * Connection State Management Hook
 * Professional Mountain Timelapse Camera System
 *
 * Manages network connectivity, Socket.IO connections, and provides
 * offline-first patterns for reliable operation in remote mountain locations.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { io, Socket } from 'socket.io-client';

export interface ConnectionState {
  isOnline: boolean;
  isWebSocketConnected: boolean;
  connectionQuality: 'excellent' | 'good' | 'fair' | 'poor' | 'offline';
  lastConnected: Date | null;
  reconnectAttempts: number;
  isReconnecting: boolean;
  error: string | null;
}

export interface ConnectionConfig {
  serverUrl: string;
  maxReconnectAttempts: number;
  baseReconnectDelay: number;
  maxReconnectDelay: number;
  connectionTimeoutMs: number;
  pingIntervalMs: number;
  healthCheckIntervalMs: number;
}

interface UseConnectionStateReturn extends ConnectionState {
  connect: (accessToken?: string) => Promise<void>;
  disconnect: () => void;
  forceReconnect: () => void;
  clearError: () => void;
  sendPing: () => Promise<number | null>;
  subscribe: (eventType: string, handler: (data: any) => void) => void;
  unsubscribe: (eventType: string, handler: (data: any) => void) => void;
  emit: (eventType: string, data: any) => boolean;
}

const defaultConfig: ConnectionConfig = {
  serverUrl: '',
  maxReconnectAttempts: 10,
  baseReconnectDelay: 1000,
  maxReconnectDelay: 30000,
  connectionTimeoutMs: 30000,
  pingIntervalMs: 30000,
  healthCheckIntervalMs: 60000,
};

export function useConnectionState(
  config: Partial<ConnectionConfig> = {}
): UseConnectionStateReturn {
  const finalConfig = { ...defaultConfig, ...config };

  const [state, setState] = useState<ConnectionState>({
    isOnline: navigator.onLine,
    isWebSocketConnected: false,
    connectionQuality: 'offline',
    lastConnected: null,
    reconnectAttempts: 0,
    isReconnecting: false,
    error: null,
  });

  const socketRef = useRef<Socket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const pingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const healthCheckIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const eventHandlersRef = useRef<Map<string, ((data: any) => void)[]>>(new Map());
  const pingStartTimeRef = useRef<number>(0);
  const accessTokenRef = useRef<string | undefined>();
  const lastConnectAttemptRef = useRef<number>(0);
  const isConnectingRef = useRef<boolean>(false);

  // Calculate exponential backoff delay
  const getReconnectDelay = useCallback((attempt: number): number => {
    const delay = finalConfig.baseReconnectDelay * Math.pow(2, attempt);
    return Math.min(delay, finalConfig.maxReconnectDelay);
  }, [finalConfig.baseReconnectDelay, finalConfig.maxReconnectDelay]);

  // Determine connection quality based on ping time and stability
  const determineConnectionQuality = useCallback((pingTime: number): ConnectionState['connectionQuality'] => {
    if (!state.isOnline || !state.isWebSocketConnected) return 'offline';
    if (pingTime < 100) return 'excellent';
    if (pingTime < 300) return 'good';
    if (pingTime < 1000) return 'fair';
    return 'poor';
  }, [state.isOnline, state.isWebSocketConnected]);

  // Handle Socket.IO events
  const handleSocketEvent = useCallback((eventType: string, data: any) => {
    try {
      // Handle ping/pong for connection quality measurement
      if (eventType === 'pong') {
        const pingTime = Date.now() - pingStartTimeRef.current;
        setState(prev => ({
          ...prev,
          connectionQuality: determineConnectionQuality(pingTime),
        }));
        return;
      }

      // Dispatch event to registered handlers
      const handlers = eventHandlersRef.current.get(eventType) || [];
      handlers.forEach(handler => {
        try {
          handler(data);
        } catch (error) {
          console.error(`Error in event handler for ${eventType}:`, error);
        }
      });

      // Also dispatch to wildcard handlers
      const wildcardHandlers = eventHandlersRef.current.get('*') || [];
      wildcardHandlers.forEach(handler => {
        try {
          handler({ type: eventType, data });
        } catch (error) {
          console.error('Error in wildcard event handler:', error);
        }
      });
    } catch (error) {
      console.error('Failed to handle Socket.IO event:', error);
    }
  }, [determineConnectionQuality]);

  // Clear all timers
  const clearTimers = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }
    if (healthCheckIntervalRef.current) {
      clearInterval(healthCheckIntervalRef.current);
      healthCheckIntervalRef.current = null;
    }
  }, []);

  // Connect to Socket.IO server
  const connect = useCallback(async (accessToken?: string): Promise<void> => {
    return new Promise((resolve, reject) => {
      if (!finalConfig.serverUrl) {
        const error = 'Server URL not configured';
        setState(prev => ({ ...prev, error }));
        reject(new Error(error));
        return;
      }

      // Don't connect if already connected or connecting
      if (socketRef.current?.connected || isConnectingRef.current) {
        resolve();
        return;
      }

      // Debounce connection attempts (minimum 2 seconds between attempts)
      const now = Date.now();
      if (now - lastConnectAttemptRef.current < 2000) {
        console.log('🔄 Connection attempt debounced, waiting...');
        setTimeout(() => connect(accessToken).then(resolve).catch(reject), 2000);
        return;
      }

      lastConnectAttemptRef.current = now;
      isConnectingRef.current = true;

      // Store access token for reconnection attempts
      accessTokenRef.current = accessToken;

      setState(prev => ({
        ...prev,
        isReconnecting: true,
        error: null,
      }));

      try {
        // Close existing connection
        if (socketRef.current) {
          socketRef.current.disconnect();
          socketRef.current = null;
        }

        // Socket.IO connection options optimized for React development
        const socketOptions: any = {
          timeout: finalConfig.connectionTimeoutMs,
          autoConnect: false,
          forceNew: true, // Force new connection to avoid React Strict Mode conflicts
          transports: ['polling', 'websocket'], // Start with polling, upgrade to websocket
          upgrade: true,
          rememberUpgrade: false, // Don't remember upgrade in development
          reconnection: false, // We handle reconnection manually
          closeOnBeforeunload: true, // Clean disconnect on page unload
          // Development-specific timeouts
          pingTimeout: 60000, // 60 seconds before considering connection dead
          pingInterval: 25000, // 25 seconds between pings
        };

        // Add authentication if provided
        if (accessToken) {
          socketOptions.auth = { token: accessToken };
          socketOptions.query = { token: accessToken };
        }

        // Create new Socket.IO connection
        const socket = io(finalConfig.serverUrl, socketOptions);
        socketRef.current = socket;

        // Connection timeout with debugging
        const timeoutId = setTimeout(() => {
          console.log('🔍 Connection timeout check:', {
            connected: socket.connected,
            disconnected: socket.disconnected,
            id: socket.id,
            transport: socket.io.engine.transport?.name
          });
          if (!socket.connected) {
            console.log('❌ Timing out connection after', finalConfig.connectionTimeoutMs, 'ms');
            socket.disconnect();
            reject(new Error('Connection timeout'));
          }
        }, finalConfig.connectionTimeoutMs);

        socket.on('connect', () => {
          clearTimeout(timeoutId);
          isConnectingRef.current = false;
          console.log('✅ Socket.IO connected to:', finalConfig.serverUrl);

          setState(prev => ({
            ...prev,
            isWebSocketConnected: true,
            isReconnecting: false,
            lastConnected: new Date(),
            reconnectAttempts: 0,
            error: null,
            connectionQuality: state.isOnline ? 'good' : 'offline',
          }));

          // Start ping interval for connection quality monitoring
          pingIntervalRef.current = setInterval(() => {
            if (socket.connected) {
              pingStartTimeRef.current = Date.now();
              socket.emit('ping', { timestamp: Date.now() });
            }
          }, finalConfig.pingIntervalMs);

          resolve();
        });

        // Set up event listeners for all events
        socket.onAny((eventName: string, ...args: any[]) => {
          handleSocketEvent(eventName, args[0]);
        });

        socket.on('disconnect', (reason: string) => {
          clearTimeout(timeoutId);
          clearTimers();
          isConnectingRef.current = false;

          console.log(`🔌 Socket.IO disconnected: ${reason}`);

          setState(prev => ({
            ...prev,
            isWebSocketConnected: false,
            isReconnecting: false,
            connectionQuality: prev.isOnline ? 'poor' : 'offline',
          }));

          // Attempt reconnection if not manually disconnected and under retry limit
          if (reason !== 'io client disconnect' && state.reconnectAttempts < finalConfig.maxReconnectAttempts) {
            const delay = getReconnectDelay(state.reconnectAttempts);
            console.log(`🔄 Reconnecting in ${delay}ms (attempt ${state.reconnectAttempts + 1}/${finalConfig.maxReconnectAttempts})`);

            setState(prev => ({
              ...prev,
              reconnectAttempts: prev.reconnectAttempts + 1,
              isReconnecting: true,
            }));

            reconnectTimeoutRef.current = setTimeout(() => {
              connect(accessTokenRef.current);
            }, delay);
          } else if (state.reconnectAttempts >= finalConfig.maxReconnectAttempts) {
            console.log('❌ Maximum reconnection attempts exceeded');
            setState(prev => ({
              ...prev,
              error: 'Maximum reconnection attempts exceeded',
              isReconnecting: false,
            }));
          }
        });

        socket.on('connect_error', (error: Error) => {
          clearTimeout(timeoutId);
          isConnectingRef.current = false;
          console.error('❌ Socket.IO connection error:', error);

          setState(prev => ({
            ...prev,
            error: `Socket.IO connection error: ${error.message}`,
            isReconnecting: false,
          }));

          reject(error);
        });

        // Connect to the server
        socket.connect();
      } catch (error) {
        isConnectingRef.current = false;
        setState(prev => ({
          ...prev,
          error: 'Failed to create Socket.IO connection',
          isReconnecting: false,
        }));
        reject(error);
      }
    });
  }, [finalConfig, handleSocketEvent, clearTimers, getReconnectDelay, state.reconnectAttempts, state.isOnline]);

  // Disconnect from Socket.IO server
  const disconnect = useCallback(() => {
    clearTimers();

    if (socketRef.current) {
      socketRef.current.removeAllListeners();
      socketRef.current.disconnect();
      socketRef.current = null;
    }

    setState(prev => ({
      ...prev,
      isWebSocketConnected: false,
      isReconnecting: false,
      reconnectAttempts: 0,
      connectionQuality: prev.isOnline ? 'fair' : 'offline',
      error: null,
    }));
  }, [clearTimers]);

  // Force reconnection
  const forceReconnect = useCallback(() => {
    setState(prev => ({ ...prev, reconnectAttempts: 0 }));
    disconnect();
    connect(accessTokenRef.current);
  }, [disconnect, connect]);

  // Clear error state
  const clearError = useCallback(() => {
    setState(prev => ({ ...prev, error: null }));
  }, []);

  // Send ping and measure response time
  const sendPing = useCallback(async (): Promise<number | null> => {
    if (!socketRef.current || !socketRef.current.connected) {
      return null;
    }

    return new Promise((resolve) => {
      const startTime = Date.now();
      const timeoutId = setTimeout(() => resolve(null), 5000);

      const handler = (data: any) => {
        clearTimeout(timeoutId);
        const pingTime = Date.now() - startTime;
        // Remove the handler after receiving pong
        unsubscribe('pong', handler);
        resolve(pingTime);
      };

      subscribe('pong', handler);
      socketRef.current!.emit('ping', { timestamp: startTime });
    });
  }, []);

  // Subscribe to events
  const subscribe = useCallback((eventType: string, handler: (data: any) => void) => {
    if (!eventHandlersRef.current.has(eventType)) {
      eventHandlersRef.current.set(eventType, []);
    }
    eventHandlersRef.current.get(eventType)!.push(handler);
  }, []);

  // Unsubscribe from events
  const unsubscribe = useCallback((eventType: string, handler: (data: any) => void) => {
    const handlers = eventHandlersRef.current.get(eventType);
    if (handlers) {
      const index = handlers.indexOf(handler);
      if (index > -1) {
        handlers.splice(index, 1);
      }
    }
  }, []);

  // Emit events
  const emit = useCallback((eventType: string, data: any): boolean => {
    if (!socketRef.current || !socketRef.current.connected) {
      return false;
    }

    try {
      socketRef.current.emit(eventType, { ...data, timestamp: Date.now() });
      return true;
    } catch (error) {
      console.error('Failed to emit event:', error);
      return false;
    }
  }, []);

  // Monitor network connectivity
  useEffect(() => {
    const handleOnline = () => {
      setState(prev => ({
        ...prev,
        isOnline: true,
        connectionQuality: prev.isWebSocketConnected ? 'good' : 'fair',
      }));

      // Attempt to reconnect if WebSocket was disconnected
      if (!state.isWebSocketConnected && accessTokenRef.current) {
        connect(accessTokenRef.current);
      }
    };

    const handleOffline = () => {
      setState(prev => ({
        ...prev,
        isOnline: false,
        connectionQuality: 'offline',
      }));
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [connect, state.isWebSocketConnected]);

  // Health check interval
  useEffect(() => {
    if (state.isWebSocketConnected) {
      healthCheckIntervalRef.current = setInterval(async () => {
        const pingTime = await sendPing();
        if (pingTime === null) {
          // Ping failed, connection might be stale
          setState(prev => ({
            ...prev,
            connectionQuality: 'poor',
          }));
        }
      }, finalConfig.healthCheckIntervalMs);
    }

    return () => {
      if (healthCheckIntervalRef.current) {
        clearInterval(healthCheckIntervalRef.current);
      }
    };
  }, [state.isWebSocketConnected, sendPing, finalConfig.healthCheckIntervalMs]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      clearTimers();
      if (socketRef.current) {
        socketRef.current.disconnect();
      }
    };
  }, [clearTimers]);

  return {
    ...state,
    connect,
    disconnect,
    forceReconnect,
    clearError,
    sendPing,
    subscribe,
    unsubscribe,
    emit,
  };
}
