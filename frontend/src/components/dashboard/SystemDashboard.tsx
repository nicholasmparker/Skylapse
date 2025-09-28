/**
 * System Dashboard - Real-time monitoring interface
 * Professional Mountain Timelapse Camera System
 */

import React from 'react';
import { useRealTimeData } from '../../hooks/useRealTimeData';
import { SystemStatusPanel } from './SystemStatusPanel';
import { ResourceMonitoringChart } from './ResourceMonitoringChart';
import { EnvironmentalConditionsPanel } from './EnvironmentalConditionsPanel';
import { CaptureProgressPanel } from './CaptureProgressPanel';
import { RecentCapturesGrid } from './RecentCapturesGrid';
import { Card } from '../../design-system/components';
import { RealTimeErrorBoundary } from '../ErrorBoundary';
import { CameraPreview } from '../camera/CameraPreview';

export const SystemDashboard: React.FC = () => {
  const {
    systemStatus,
    resourceMetrics,
    environmentalData,
    captureProgress,
    recentCaptures,
    isConnected,
    error
  } = useRealTimeData();

  if (error && error.includes('Failed to connect')) {
    return (
      <div className="p-6">
        <Card className="max-w-md mx-auto">
          <div className="text-center p-6">
            <div className="text-red-500 text-4xl mb-4">⚠️</div>
            <h2 className="text-xl font-semibold text-mountain-900 mb-2">
              Connection Error
            </h2>
            <p className="text-mountain-600 mb-4">
              Unable to connect to the Skylapse system. Please check your connection.
            </p>
            <button
              onClick={() => window.location.reload()}
              className="px-4 py-2 bg-golden-500 text-white rounded-lg hover:bg-golden-600 transition-colors"
            >
              Retry Connection
            </button>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-6">
      {/* Status Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-mountain-900">
              System Dashboard
            </h1>
            <p className="text-mountain-700 mt-2">
              Real-time monitoring and camera control
            </p>
          </div>
          <div className="flex items-center space-x-4">
            <div className={`flex items-center space-x-2 ${
              isConnected ? 'text-green-600' : 'text-yellow-600'
            }`}>
              <div className={`w-2 h-2 rounded-full ${
                isConnected ? 'bg-green-500' : 'bg-yellow-500'
              } ${isConnected ? 'animate-pulse-slow' : ''}`} />
              <span className="text-sm font-medium">
                {isConnected ? 'Real-time' : 'Manual refresh'}
              </span>
            </div>
            {error && error.includes('Real-time updates unavailable') && (
              <div className="text-sm text-yellow-600 bg-yellow-50 px-2 py-1 rounded">
                WebSocket offline - Dashboard functional
              </div>
            )}
            <div className="text-sm text-mountain-500">
              Last updated: {new Date().toLocaleTimeString()}
            </div>
          </div>
        </div>
      </div>

      {/* Main Dashboard Grid */}
      <div className="max-w-7xl mx-auto">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">

          {/* System Status - Full width on mobile, 4 cols on desktop */}
          <div className="lg:col-span-4">
            <SystemStatusPanel
              status={systemStatus}
              isConnected={isConnected}
            />
          </div>

          {/* Live Camera Preview - Full width on mobile, 8 cols on desktop */}
          <div className="lg:col-span-8">
            <Card className="h-full">
              <div className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h3 className="text-lg font-semibold text-mountain-900">
                      🎥 Live Camera Preview
                    </h3>
                    <p className="text-sm text-mountain-600">
                      Real-time camera feed with manual capture controls
                    </p>
                  </div>
                </div>
                <CameraPreview
                  showControls={true}
                  showOverlay={true}
                  autoStart={true}
                />
              </div>
            </Card>
          </div>

          {/* Resource Monitoring - Full width on mobile, 12 cols on desktop */}
          <div className="lg:col-span-12">
            <ResourceMonitoringChart
              metrics={resourceMetrics}
              isConnected={isConnected}
            />
          </div>

          {/* Environmental Conditions - Full width on mobile, 6 cols on desktop */}
          <div className="lg:col-span-6">
            <EnvironmentalConditionsPanel
              data={environmentalData}
              isConnected={isConnected}
            />
          </div>

          {/* Capture Progress - Full width on mobile, 6 cols on desktop */}
          <div className="lg:col-span-6">
            <CaptureProgressPanel
              progress={captureProgress}
              isConnected={isConnected}
            />
          </div>

          {/* Recent Captures - Full width */}
          <div className="lg:col-span-12">
            <RealTimeErrorBoundary>
              <RecentCapturesGrid
                captures={recentCaptures}
                isConnected={isConnected}
              />
            </RealTimeErrorBoundary>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SystemDashboard;
