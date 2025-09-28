/**
 * Connection Status Indicator Component
 * Shows real-time connection health and quality for mountain deployments
 */

import React from 'react';
import {
  WifiIcon,
  ExclamationTriangleIcon,
  SignalIcon,
  NoSymbolIcon
} from '@heroicons/react/24/outline';
import { CheckCircleIcon } from '@heroicons/react/24/solid';
import { ConnectionState } from '../../services/RealTimeService';
import { clsx } from 'clsx';

interface ConnectionStatusIndicatorProps {
  connectionState: ConnectionState;
  className?: string;
  showDetails?: boolean;
}

export const ConnectionStatusIndicator: React.FC<ConnectionStatusIndicatorProps> = ({
  connectionState,
  className = '',
  showDetails = true
}) => {
  const getStatusInfo = () => {
    const { status, transport, quality, latency, retryCount } = connectionState;

    switch (status) {
      case 'online':
        return {
          icon: CheckCircleIcon,
          color: 'text-green-500',
          bgColor: 'bg-green-50 border-green-200',
          label: 'Connected',
          description: `${transport.toUpperCase()} • ${quality} quality${latency > 0 ? ` • ${latency}ms` : ''}`
        };

      case 'degraded':
        return {
          icon: ExclamationTriangleIcon,
          color: 'text-yellow-500',
          bgColor: 'bg-yellow-50 border-yellow-200',
          label: 'Degraded',
          description: `${transport.toUpperCase()} • Limited functionality${retryCount > 0 ? ` • ${retryCount} retries` : ''}`
        };

      case 'offline':
        return {
          icon: NoSymbolIcon,
          color: 'text-red-500',
          bgColor: 'bg-red-50 border-red-200',
          label: 'Offline',
          description: transport === 'cache' ? 'Using cached data' : 'Attempting to reconnect...'
        };

      default:
        return {
          icon: SignalIcon,
          color: 'text-gray-500',
          bgColor: 'bg-gray-50 border-gray-200',
          label: 'Unknown',
          description: 'Connection status unknown'
        };
    }
  };

  const getQualityIcon = () => {
    switch (connectionState.quality) {
      case 'excellent':
        return <SignalIcon className="h-4 w-4 text-green-500" />;
      case 'good':
        return <SignalIcon className="h-4 w-4 text-yellow-500" />;
      case 'poor':
        return <SignalIcon className="h-4 w-4 text-red-500" />;
      default:
        return <SignalIcon className="h-4 w-4 text-gray-500" />;
    }
  };

  const statusInfo = getStatusInfo();
  const StatusIcon = statusInfo.icon;

  if (!showDetails) {
    // Compact version - just icon
    return (
      <div className={clsx('flex items-center', className)}>
        <StatusIcon className={clsx('h-5 w-5', statusInfo.color)} />
      </div>
    );
  }

  return (
    <div className={clsx(
      'flex items-center space-x-3 px-3 py-2 rounded-lg border',
      statusInfo.bgColor,
      className
    )}>
      {/* Status Icon */}
      <StatusIcon className={clsx('h-5 w-5', statusInfo.color)} />

      {/* Status Text */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center space-x-2">
          <span className="text-sm font-medium text-gray-900">
            {statusInfo.label}
          </span>
          {connectionState.status === 'online' && getQualityIcon()}
        </div>

        <p className="text-xs text-gray-600 truncate">
          {statusInfo.description}
        </p>
      </div>

      {/* Additional status indicators */}
      {connectionState.status === 'offline' && connectionState.retryCount > 0 && (
        <div className="flex items-center space-x-1">
          <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-red-500"></div>
          <span className="text-xs text-gray-500">
            {connectionState.retryCount}
          </span>
        </div>
      )}

      {/* Transport indicator */}
      <div className="text-xs text-gray-500 font-mono uppercase">
        {connectionState.transport}
      </div>
    </div>
  );
};

/**
 * Lightweight connection dot for minimal UI space
 */
export const ConnectionDot: React.FC<{
  connectionState: ConnectionState;
  className?: string;
}> = ({ connectionState, className = '' }) => {
  const getStatusColor = () => {
    switch (connectionState.status) {
      case 'online':
        return 'bg-green-500';
      case 'degraded':
        return 'bg-yellow-500';
      case 'offline':
        return 'bg-red-500';
      default:
        return 'bg-gray-500';
    }
  };

  return (
    <div
      className={clsx(
        'w-2 h-2 rounded-full',
        getStatusColor(),
        connectionState.status === 'offline' && 'animate-pulse',
        className
      )}
      title={`Connection: ${connectionState.status} (${connectionState.transport})`}
    />
  );
};

/**
 * Detailed connection panel for debugging/monitoring
 */
export const ConnectionDebugPanel: React.FC<{
  connectionState: ConnectionState;
  onReconnect?: () => void;
  className?: string;
}> = ({ connectionState, onReconnect, className = '' }) => {
  const formatLatency = (latency: number) => {
    if (latency === 0) return 'N/A';
    return `${latency}ms`;
  };

  const formatLastSeen = (lastSeen: Date) => {
    const diff = Date.now() - lastSeen.getTime();
    if (diff < 1000) return 'Just now';
    if (diff < 60000) return `${Math.floor(diff / 1000)}s ago`;
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    return lastSeen.toLocaleTimeString();
  };

  return (
    <div className={clsx('bg-white rounded-lg border border-gray-200 p-4', className)}>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-medium text-gray-900">Connection Details</h3>
        {onReconnect && (
          <button
            onClick={onReconnect}
            className="text-xs text-blue-600 hover:text-blue-800 font-medium"
          >
            Reconnect
          </button>
        )}
      </div>

      <div className="grid grid-cols-2 gap-4 text-xs">
        <div>
          <span className="text-gray-500">Status:</span>
          <div className="font-medium capitalize">{connectionState.status}</div>
        </div>

        <div>
          <span className="text-gray-500">Transport:</span>
          <div className="font-medium uppercase">{connectionState.transport}</div>
        </div>

        <div>
          <span className="text-gray-500">Quality:</span>
          <div className="font-medium capitalize">{connectionState.quality}</div>
        </div>

        <div>
          <span className="text-gray-500">Latency:</span>
          <div className="font-medium">{formatLatency(connectionState.latency)}</div>
        </div>

        <div>
          <span className="text-gray-500">Last Seen:</span>
          <div className="font-medium">{formatLastSeen(connectionState.lastSeen)}</div>
        </div>

        <div>
          <span className="text-gray-500">Retries:</span>
          <div className="font-medium">{connectionState.retryCount}</div>
        </div>
      </div>

      {/* Performance indicators */}
      <div className="mt-3 pt-3 border-t border-gray-100">
        <div className="flex items-center space-x-2">
          <SignalIcon className="h-4 w-4 text-gray-400" />
          <div className="flex-1 bg-gray-200 rounded-full h-2">
            <div
              className={clsx(
                'h-2 rounded-full transition-all duration-300',
                connectionState.quality === 'excellent' && 'w-full bg-green-500',
                connectionState.quality === 'good' && 'w-2/3 bg-yellow-500',
                connectionState.quality === 'poor' && 'w-1/3 bg-red-500'
              )}
            />
          </div>
          <span className="text-xs text-gray-500 capitalize">
            {connectionState.quality}
          </span>
        </div>
      </div>
    </div>
  );
};

export default ConnectionStatusIndicator;
