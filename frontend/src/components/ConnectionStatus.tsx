/**
 * Connection Status Components
 * Professional Mountain Timelapse Camera System
 *
 * Provides comprehensive connection status indicators and offline-first patterns
 * for reliable operation in remote mountain locations.
 */

import React, { useState, useEffect } from 'react';
import { Button } from '../design-system/components/Button';
import { StatusIndicator } from '../design-system/components/StatusIndicator';

export interface ConnectionStatusProps {
  isOnline: boolean;
  isWebSocketConnected: boolean;
  connectionQuality: 'excellent' | 'good' | 'fair' | 'poor' | 'offline';
  lastConnected: Date | null;
  reconnectAttempts: number;
  isReconnecting: boolean;
  error: string | null;
  onReconnect?: () => void;
  onDismissError?: () => void;
  className?: string;
}

// Main connection status component
export function ConnectionStatus({
  isOnline,
  isWebSocketConnected,
  connectionQuality,
  lastConnected,
  reconnectAttempts,
  isReconnecting,
  error,
  onReconnect,
  onDismissError,
  className = ''
}: ConnectionStatusProps) {
  const [showDetails, setShowDetails] = useState(false);

  const getStatusInfo = () => {
    if (!isOnline) {
      return {
        status: 'error' as const,
        label: 'Offline',
        message: 'No internet connection',
        color: 'text-red-600',
        bgColor: 'bg-red-50',
        borderColor: 'border-red-200'
      };
    }

    if (isReconnecting) {
      return {
        status: 'paused' as const,
        label: 'Reconnecting',
        message: `Attempting to reconnect (${reconnectAttempts}/10)`,
        color: 'text-yellow-600',
        bgColor: 'bg-yellow-50',
        borderColor: 'border-yellow-200'
      };
    }

    if (!isWebSocketConnected) {
      return {
        status: 'error' as const,
        label: 'Disconnected',
        message: 'Real-time updates unavailable',
        color: 'text-red-600',
        bgColor: 'bg-red-50',
        borderColor: 'border-red-200'
      };
    }

    // Connected - determine quality
    switch (connectionQuality) {
      case 'excellent':
        return {
          status: 'success' as const,
          label: 'Excellent',
          message: 'Real-time updates active',
          color: 'text-green-600',
          bgColor: 'bg-green-50',
          borderColor: 'border-green-200'
        };
      case 'good':
        return {
          status: 'success' as const,
          label: 'Good',
          message: 'Real-time updates active',
          color: 'text-green-600',
          bgColor: 'bg-green-50',
          borderColor: 'border-green-200'
        };
      case 'fair':
        return {
          status: 'paused' as const,
          label: 'Fair',
          message: 'Slower connection detected',
          color: 'text-yellow-600',
          bgColor: 'bg-yellow-50',
          borderColor: 'border-yellow-200'
        };
      case 'poor':
        return {
          status: 'paused' as const,
          label: 'Poor',
          message: 'Limited connectivity',
          color: 'text-orange-600',
          bgColor: 'bg-orange-50',
          borderColor: 'border-orange-200'
        };
      default:
        return {
          status: 'error' as const,
          label: 'Unknown',
          message: 'Connection status unknown',
          color: 'text-gray-600',
          bgColor: 'bg-gray-50',
          borderColor: 'border-gray-200'
        };
    }
  };

  const statusInfo = getStatusInfo();

  return (
    <div className={`${className}`}>
      {/* Main status indicator */}
      <div className={`rounded-lg border ${statusInfo.borderColor} ${statusInfo.bgColor} p-3`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <StatusIndicator
              status={statusInfo.status}
              label=""
              pulse={isReconnecting}
            />
            <div>
              <div className={`font-medium text-sm ${statusInfo.color}`}>
                {statusInfo.label}
              </div>
              <div className="text-xs text-gray-600">
                {statusInfo.message}
              </div>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            {error && onDismissError && (
              <Button
                size="sm"
                variant="ghost"
                onClick={onDismissError}
                className="text-xs"
              >
                Dismiss
              </Button>
            )}
            {onReconnect && !isWebSocketConnected && !isReconnecting && (
              <Button
                size="sm"
                variant="outline"
                onClick={onReconnect}
                className="text-xs"
              >
                Reconnect
              </Button>
            )}
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setShowDetails(!showDetails)}
              className="text-xs"
            >
              {showDetails ? 'Hide' : 'Details'}
            </Button>
          </div>
        </div>

        {/* Error message */}
        {error && (
          <div className="mt-2 p-2 bg-red-100 border border-red-200 rounded text-xs text-red-700">
            {error}
          </div>
        )}

        {/* Detailed information */}
        {showDetails && (
          <div className="mt-3 pt-3 border-t border-gray-200 space-y-2 text-xs">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <span className="font-medium">Network:</span>
                <span className={`ml-2 ${isOnline ? 'text-green-600' : 'text-red-600'}`}>
                  {isOnline ? 'Online' : 'Offline'}
                </span>
              </div>
              <div>
                <span className="font-medium">Real-time:</span>
                <span className={`ml-2 ${isWebSocketConnected ? 'text-green-600' : 'text-red-600'}`}>
                  {isWebSocketConnected ? 'Connected' : 'Disconnected'}
                </span>
              </div>
              <div>
                <span className="font-medium">Quality:</span>
                <span className="ml-2 capitalize">
                  {connectionQuality}
                </span>
              </div>
              <div>
                <span className="font-medium">Attempts:</span>
                <span className="ml-2">
                  {reconnectAttempts}/10
                </span>
              </div>
            </div>
            {lastConnected && (
              <div>
                <span className="font-medium">Last connected:</span>
                <span className="ml-2">
                  {lastConnected.toLocaleTimeString()}
                </span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// Compact status indicator for headers/toolbars
export function ConnectionStatusBadge({
  isWebSocketConnected,
  connectionQuality,
  isReconnecting,
  className = ''
}: Pick<ConnectionStatusProps, 'isWebSocketConnected' | 'connectionQuality' | 'isReconnecting' | 'className'>) {
  const getStatusColor = () => {
    if (isReconnecting) return 'bg-yellow-400';
    if (!isWebSocketConnected) return 'bg-red-400';

    switch (connectionQuality) {
      case 'excellent':
      case 'good':
        return 'bg-green-400';
      case 'fair':
        return 'bg-yellow-400';
      case 'poor':
        return 'bg-orange-400';
      default:
        return 'bg-gray-400';
    }
  };

  const getStatusText = () => {
    if (isReconnecting) return 'Reconnecting...';
    if (!isWebSocketConnected) return 'Offline';
    return 'Live';
  };

  return (
    <div className={`inline-flex items-center space-x-2 ${className}`}>
      <div className={`w-2 h-2 rounded-full ${getStatusColor()} ${isReconnecting ? 'animate-pulse' : ''}`} />
      <span className="text-xs font-medium text-gray-600">
        {getStatusText()}
      </span>
    </div>
  );
}

// Offline notification banner
export function OfflineBanner({
  isOnline,
  onDismiss,
  className = ''
}: {
  isOnline: boolean;
  onDismiss?: () => void;
  className?: string;
}) {
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    // Reset dismissed state when coming back online
    if (isOnline && dismissed) {
      setDismissed(false);
    }
  }, [isOnline, dismissed]);

  const handleDismiss = () => {
    setDismissed(true);
    onDismiss?.();
  };

  if (isOnline || dismissed) {
    return null;
  }

  return (
    <div className={`bg-red-600 text-white ${className}`}>
      <div className="px-4 py-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span className="text-sm font-medium">
              You're currently offline. Some features may be limited.
            </span>
          </div>
          <Button
            size="sm"
            variant="ghost"
            onClick={handleDismiss}
            className="text-white hover:bg-red-700"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </Button>
        </div>
      </div>
    </div>
  );
}

// Connection quality indicator with signal bars
export function SignalStrengthIndicator({
  connectionQuality,
  className = ''
}: {
  connectionQuality: ConnectionStatusProps['connectionQuality'];
  className?: string;
}) {
  const getBars = () => {
    switch (connectionQuality) {
      case 'excellent': return 4;
      case 'good': return 3;
      case 'fair': return 2;
      case 'poor': return 1;
      default: return 0;
    }
  };

  const activeBars = getBars();

  return (
    <div className={`inline-flex items-end space-x-1 ${className}`}>
      {[1, 2, 3, 4].map((bar) => (
        <div
          key={bar}
          className={`w-1 ${
            bar === 1 ? 'h-2' : bar === 2 ? 'h-3' : bar === 3 ? 'h-4' : 'h-5'
          } rounded-sm ${
            bar <= activeBars ? 'bg-green-500' : 'bg-gray-300'
          }`}
        />
      ))}
    </div>
  );
}

// Auto-updating connection status hook
export function useConnectionStatusDisplay(connectionState: any) {
  const [lastUpdateTime, setLastUpdateTime] = useState<Date>(new Date());

  useEffect(() => {
    const interval = setInterval(() => {
      setLastUpdateTime(new Date());
    }, 30000); // Update every 30 seconds

    return () => clearInterval(interval);
  }, []);

  const timeSinceLastConnected = connectionState.lastConnected
    ? Math.floor((lastUpdateTime.getTime() - connectionState.lastConnected.getTime()) / 1000)
    : null;

  return {
    ...connectionState,
    timeSinceLastConnected,
    lastUpdateTime
  };
}
