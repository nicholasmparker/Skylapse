/**
 * System Status Panel - Service health monitoring
 * Professional Mountain Timelapse Camera System
 */

import React from 'react';
import type { SystemStatus } from '../../api/types';
import { Card, StatusIndicator } from '../../design-system/components';
import {
  CameraIcon,
  ServerIcon,
  CpuChipIcon,
  CircleStackIcon
} from '@heroicons/react/24/outline';

interface SystemStatusPanelProps {
  status: SystemStatus | null;
  isConnected: boolean;
}

export const SystemStatusPanel: React.FC<SystemStatusPanelProps> = ({
  status,
  isConnected
}) => {
  const getServiceStatus = (service: string) => {
    // Don't show all services as error just because WebSocket is disconnected
    // Each service should show its actual health status
    if (!status) return 'paused';

    switch (service) {
      case 'capture':
        return status.captureService?.status === 'healthy' ? 'active' : 'error';
      case 'processing':
        return status.processingService?.status === 'healthy' ? 'active' : 'error';
      case 'camera':
        return status.networkStatus?.connected ? 'active' : 'error';
      default:
        return 'paused';
    }
  };

  const formatStorageUsage = () => {
    if (!status?.storage) return 'Unknown';

    const used = status.storage.used ?? 0;
    const total = status.storage.total ?? 1000;
    const percentage = status.storage.percentage ?? 0;

    const usedGB = (used / (1024 ** 3)).toFixed(1);
    const totalGB = (total / (1024 ** 3)).toFixed(1);
    const percentageFormatted = percentage.toFixed(1);

    return `${usedGB}GB / ${totalGB}GB (${percentageFormatted}%)`;
  };

  const getStorageStatus = () => {
    if (!status?.storage) return 'paused';

    const percentage = status.storage.percentage ?? 0;
    if (percentage > 90) return 'error';
    if (percentage > 75) return 'paused';
    return 'active';
  };

  return (
    <Card
      title="System Status"
      data-testid="system-metrics"
      subtitle="Service health and system overview"
      className="h-full"
    >
      <div className="space-y-6">

        {/* Service Status Grid */}
        <div className="grid grid-cols-1 gap-4">

          {/* Capture Service */}
          <div className="flex items-center justify-between p-3 bg-mountain-50 rounded-lg">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-white rounded-lg shadow-sm">
                <CameraIcon className="w-5 h-5 text-mountain-600" />
              </div>
              <div>
                <div className="font-medium text-mountain-900">Capture Service</div>
                <div className="text-sm text-mountain-700">Camera control & scheduling</div>
              </div>
            </div>
            <StatusIndicator
              status={getServiceStatus('capture')}
              label=""
              pulse={getServiceStatus('capture') === 'active'}
            />
          </div>

          {/* Processing Service */}
          <div className="flex items-center justify-between p-3 bg-mountain-50 rounded-lg">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-white rounded-lg shadow-sm">
                <CpuChipIcon className="w-5 h-5 text-mountain-600" />
              </div>
              <div>
                <div className="font-medium text-mountain-900">Processing Service</div>
                <div className="text-sm text-mountain-700">HDR & timelapse assembly</div>
              </div>
            </div>
            <StatusIndicator
              status={getServiceStatus('processing')}
              label=""
              pulse={getServiceStatus('processing') === 'active'}
            />
          </div>

          {/* Camera Hardware */}
          <div className="flex items-center justify-between p-3 bg-mountain-50 rounded-lg">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-white rounded-lg shadow-sm">
                <ServerIcon className="w-5 h-5 text-mountain-600" />
              </div>
              <div>
                <div className="font-medium text-mountain-900">Camera Hardware</div>
                <div className="text-sm text-mountain-700">
                  {status?.camera?.model || 'Unknown model'}
                </div>
              </div>
            </div>
            <StatusIndicator
              status={getServiceStatus('camera')}
              label=""
              pulse={getServiceStatus('camera') === 'active'}
            />
          </div>

          {/* Storage Status */}
          <div className="flex items-center justify-between p-3 bg-mountain-50 rounded-lg">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-white rounded-lg shadow-sm">
                <CircleStackIcon className="w-5 h-5 text-mountain-600" />
              </div>
              <div>
                <div className="font-medium text-mountain-900">Storage</div>
                <div className="text-sm text-mountain-700">
                  {formatStorageUsage()}
                </div>
              </div>
            </div>
            <StatusIndicator
              status={getStorageStatus()}
              label=""
            />
          </div>
        </div>

        {/* System Resources Summary */}
        {status?.resources && (
          <div className="pt-4 border-t border-mountain-200">
            <h4 className="font-medium text-mountain-900 mb-3">System Resources</h4>
            <div className="grid grid-cols-2 gap-4">

              {/* CPU Usage */}
              <div className="text-center">
                <div className="text-2xl font-bold text-mountain-900">
                  {status.resources?.cpu?.usage?.toFixed(1) || '0'}%
                </div>
                <div className="text-sm text-mountain-700">CPU Usage</div>
                <div className="text-xs text-mountain-500">
                  {status.resources?.cpu?.temperature?.toFixed(1) || '0'}°C
                </div>
              </div>

              {/* Memory Usage */}
              <div className="text-center">
                <div className="text-2xl font-bold text-mountain-900">
                  {status.resources?.memory?.percentage?.toFixed(1) || '0'}%
                </div>
                <div className="text-sm text-mountain-700">Memory</div>
                <div className="text-xs text-mountain-500">
                  {((status.resources?.memory?.used || 0) / (1024 ** 3)).toFixed(1)}GB used
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Connection Status */}
        <div className="pt-4 border-t border-mountain-200">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-mountain-700">
              Real-time Updates
            </span>
            <div className={`flex items-center space-x-2 ${
              isConnected ? 'text-green-600' : 'text-red-600'
            }`}>
              <div className={`w-2 h-2 rounded-full ${
                isConnected ? 'bg-green-500 animate-pulse-slow' : 'bg-red-500'
              }`} />
              <span className="text-sm">
                {isConnected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
          </div>

          {status?.timestamp && (
            <div className="mt-2 text-xs text-mountain-500">
              Last update: {new Date(status.timestamp).toLocaleString()}
            </div>
          )}
        </div>
      </div>
    </Card>
  );
};
