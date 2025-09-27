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

  if (error) {
    return (
      <div className="min-h-screen bg-mountain-50 p-6">
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
    <div className="min-h-screen bg-mountain-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-mountain-200">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-mountain-900">
                🏔️ Skylapse Dashboard
              </h1>
              <p className="text-mountain-600 mt-1">
                Mountain Timelapse Camera System
              </p>
            </div>
            <div className="flex items-center space-x-4">
              <div className={`flex items-center space-x-2 ${
                isConnected ? 'text-green-600' : 'text-red-600'
              }`}>
                <div className={`w-2 h-2 rounded-full ${
                  isConnected ? 'bg-green-500' : 'bg-red-500'
                } ${isConnected ? 'animate-pulse-slow' : ''}`} />
                <span className="text-sm font-medium">
                  {isConnected ? 'Connected' : 'Disconnected'}
                </span>
              </div>
              <div className="text-sm text-mountain-500">
                Last updated: {new Date().toLocaleTimeString()}
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Dashboard Grid */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">

          {/* System Status - Full width on mobile, 4 cols on desktop */}
          <div className="lg:col-span-4">
            <SystemStatusPanel
              status={systemStatus}
              isConnected={isConnected}
            />
          </div>

          {/* Resource Monitoring - Full width on mobile, 8 cols on desktop */}
          <div className="lg:col-span-8">
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
            <RecentCapturesGrid
              captures={recentCaptures}
              isConnected={isConnected}
            />
          </div>
        </div>
      </main>
    </div>
  );
};

export default SystemDashboard;
