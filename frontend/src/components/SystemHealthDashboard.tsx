/**
 * System Health Dashboard
 * Professional Mountain Timelapse Camera System
 *
 * Demonstrates production-ready real-time frontend client with:
 * - Secure JWT authentication
 * - Bulletproof offline/online state management
 * - Comprehensive error boundaries and graceful degradation
 * - Professional connection status indicators
 */

import React from 'react';
import { useRealTimeData } from '../hooks/useRealTimeData';
import { useAuth } from '../contexts/AuthContext';
import { RealTimeErrorBoundary } from './ErrorBoundary';
import { ConnectionStatus, ConnectionStatusBadge, OfflineBanner, SignalStrengthIndicator } from './ConnectionStatus';
import { Card } from '../design-system/components/Card';
import { Button } from '../design-system/components/Button';
import { StatusIndicator } from '../design-system/components/StatusIndicator';

export function SystemHealthDashboard() {
  const { isAuthenticated, user, logout } = useAuth();
  const {
    // Data
    systemStatus,
    resourceMetrics,
    environmentalData,
    captureProgress,
    recentCaptures,

    // Connection state
    isConnected,
    isOnline,
    connectionQuality,
    isReconnecting,
    reconnectAttempts,
    lastConnected,

    // Error handling
    error,
    hasDataError,

    // Control
    reconnect,
    refreshData,
    clearError,

    // Loading
    isLoadingInitialData,
    isRefreshing,
  } = useRealTimeData();

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <Card className="max-w-md w-full text-center">
          <h1 className="text-2xl font-bold text-gray-900 mb-4">
            Skylapse Dashboard
          </h1>
          <p className="text-gray-600 mb-6">
            Professional Mountain Timelapse Camera System
          </p>
          <p className="text-sm text-gray-500">
            Please authenticate to access the dashboard.
          </p>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Offline Banner */}
      <OfflineBanner isOnline={isOnline} />

      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <h1 className="text-2xl font-bold text-gray-900">
              Skylapse Dashboard
            </h1>
            <ConnectionStatusBadge
              isWebSocketConnected={isConnected}
              connectionQuality={connectionQuality}
              isReconnecting={isReconnecting}
            />
            <SignalStrengthIndicator connectionQuality={connectionQuality} />
          </div>

          <div className="flex items-center space-x-4">
            <span className="text-sm text-gray-600">
              Welcome, {user?.username}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={refreshData}
              disabled={isRefreshing}
            >
              {isRefreshing ? 'Refreshing...' : 'Refresh'}
            </Button>
            <Button variant="outline" size="sm" onClick={logout}>
              Logout
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="px-6 py-6 space-y-6">
        {/* Connection Status */}
        <ConnectionStatus
          isOnline={isOnline}
          isWebSocketConnected={isConnected}
          connectionQuality={connectionQuality}
          lastConnected={lastConnected}
          reconnectAttempts={reconnectAttempts}
          isReconnecting={isReconnecting}
          error={error}
          onReconnect={reconnect}
          onDismissError={clearError}
        />

        {/* System Status Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {/* System Status */}
          <RealTimeErrorBoundary>
            <Card title="System Status">
              {isLoadingInitialData ? (
                <div className="animate-pulse space-y-2">
                  <div className="h-4 bg-gray-200 rounded w-3/4"></div>
                  <div className="h-4 bg-gray-200 rounded w-1/2"></div>
                </div>
              ) : systemStatus ? (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">Camera</span>
                    <StatusIndicator
                      status={systemStatus.service.camera === 'connected' ? 'success' : 'error'}
                      label={systemStatus.service.camera}
                    />
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">Capture Service</span>
                    <StatusIndicator
                      status={systemStatus.service.capture === 'running' ? 'success' : 'error'}
                      label={systemStatus.service.capture}
                    />
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">Processing</span>
                    <StatusIndicator
                      status={systemStatus.service.processing === 'running' ? 'success' : 'error'}
                      label={systemStatus.service.processing}
                    />
                  </div>
                  <div className="text-xs text-gray-500 mt-2">
                    Last updated: {new Date(systemStatus.timestamp).toLocaleTimeString()}
                  </div>
                </div>
              ) : (
                <div className="text-sm text-gray-500">
                  {hasDataError ? 'Failed to load system status' : 'No data available'}
                </div>
              )}
            </Card>
          </RealTimeErrorBoundary>

          {/* Resource Metrics */}
          <RealTimeErrorBoundary>
            <Card title="Resource Usage">
              {isLoadingInitialData ? (
                <div className="animate-pulse space-y-2">
                  <div className="h-4 bg-gray-200 rounded w-full"></div>
                  <div className="h-4 bg-gray-200 rounded w-3/4"></div>
                  <div className="h-4 bg-gray-200 rounded w-1/2"></div>
                </div>
              ) : resourceMetrics.length > 0 ? (
                <div className="space-y-3">
                  {(() => {
                    const latest = resourceMetrics[resourceMetrics.length - 1];
                    return (
                      <>
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-medium">CPU Usage</span>
                          <span className="text-sm text-gray-600">
                            {latest.cpu.usage.toFixed(1)}%
                          </span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-blue-600 h-2 rounded-full"
                            style={{ width: `${latest.cpu.usage}%` }}
                          ></div>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-medium">Memory</span>
                          <span className="text-sm text-gray-600">
                            {latest.memory.percentage.toFixed(1)}%
                          </span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-green-600 h-2 rounded-full"
                            style={{ width: `${latest.memory.percentage}%` }}
                          ></div>
                        </div>
                        <div className="text-xs text-gray-500">
                          Real-time metrics ({resourceMetrics.length} samples)
                        </div>
                      </>
                    );
                  })()}
                </div>
              ) : (
                <div className="text-sm text-gray-500">
                  {hasDataError ? 'Failed to load resource metrics' : 'No metrics available'}
                </div>
              )}
            </Card>
          </RealTimeErrorBoundary>

          {/* Environmental Conditions */}
          <RealTimeErrorBoundary>
            <Card title="Environmental Conditions">
              {isLoadingInitialData ? (
                <div className="animate-pulse space-y-2">
                  <div className="h-4 bg-gray-200 rounded w-2/3"></div>
                  <div className="h-4 bg-gray-200 rounded w-1/2"></div>
                  <div className="h-4 bg-gray-200 rounded w-3/4"></div>
                </div>
              ) : environmentalData ? (
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">Temperature</span>
                    <span className="text-sm text-gray-600">
                      {environmentalData.temperature}°C
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">Humidity</span>
                    <span className="text-sm text-gray-600">
                      {environmentalData.humidity}%
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">Cloud Cover</span>
                    <span className="text-sm text-gray-600">
                      {environmentalData.cloudCover}%
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">Wind Speed</span>
                    <span className="text-sm text-gray-600">
                      {environmentalData.windSpeed} km/h
                    </span>
                  </div>
                  {environmentalData.isGoldenHour && (
                    <div className="mt-2 p-2 bg-amber-50 border border-amber-200 rounded text-xs text-amber-800">
                      Golden Hour Active!
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-sm text-gray-500">
                  {hasDataError ? 'Failed to load environmental data' : 'No data available'}
                </div>
              )}
            </Card>
          </RealTimeErrorBoundary>

          {/* Capture Progress */}
          <RealTimeErrorBoundary>
            <Card title="Capture Progress">
              {isLoadingInitialData ? (
                <div className="animate-pulse space-y-2">
                  <div className="h-4 bg-gray-200 rounded w-1/2"></div>
                  <div className="h-6 bg-gray-200 rounded w-full"></div>
                </div>
              ) : captureProgress ? (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">Status</span>
                    <StatusIndicator
                      status={captureProgress.isActive ? 'active' : 'paused'}
                      label={captureProgress.isActive ? 'Active' : 'Stopped'}
                      pulse={captureProgress.isActive}
                    />
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">Completed</span>
                    <span className="text-sm text-gray-600">
                      {captureProgress.capturesCompleted}
                      {captureProgress.totalCaptures && ` / ${captureProgress.totalCaptures}`}
                    </span>
                  </div>
                  {captureProgress.isActive && (
                    <div className="text-xs text-gray-500">
                      Next capture in {captureProgress.nextCaptureIn}s
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-sm text-gray-500">
                  No active capture session
                </div>
              )}
            </Card>
          </RealTimeErrorBoundary>

          {/* Recent Captures */}
          <RealTimeErrorBoundary>
            <Card title="Recent Captures" className="md:col-span-2">
              {isLoadingInitialData ? (
                <div className="grid grid-cols-3 gap-2">
                  {[1, 2, 3].map(i => (
                    <div key={i} className="animate-pulse">
                      <div className="aspect-video bg-gray-200 rounded"></div>
                    </div>
                  ))}
                </div>
              ) : recentCaptures.length > 0 ? (
                <div className="grid grid-cols-3 gap-2">
                  {recentCaptures.slice(0, 6).map((capture) => (
                    <div key={capture.id} className="relative">
                      <img
                        src={capture.thumbnail}
                        alt={capture.name}
                        className="aspect-video object-cover rounded"
                        onError={(e) => {
                          e.currentTarget.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="200" height="150" viewBox="0 0 200 150"><rect width="200" height="150" fill="%23f3f4f6"/><text x="100" y="75" text-anchor="middle" fill="%236b7280" font-size="12">No Image</text></svg>';
                        }}
                      />
                      <div className="absolute bottom-1 left-1 bg-black bg-opacity-50 text-white text-xs px-1 rounded">
                        {new Date(capture.startTime).toLocaleDateString()}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-sm text-gray-500 text-center py-8">
                  {hasDataError ? 'Failed to load recent captures' : 'No recent captures available'}
                </div>
              )}
            </Card>
          </RealTimeErrorBoundary>
        </div>

        {/* Connection Quality Details */}
        <Card title="Connection Details" className="lg:col-span-3">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <span className="font-medium text-gray-900">Network Status:</span>
              <div className={`mt-1 ${isOnline ? 'text-green-600' : 'text-red-600'}`}>
                {isOnline ? 'Online' : 'Offline'}
              </div>
            </div>
            <div>
              <span className="font-medium text-gray-900">Real-time Status:</span>
              <div className={`mt-1 ${isConnected ? 'text-green-600' : 'text-red-600'}`}>
                {isConnected ? 'Connected' : 'Disconnected'}
              </div>
            </div>
            <div>
              <span className="font-medium text-gray-900">Connection Quality:</span>
              <div className="mt-1 capitalize">
                {connectionQuality}
              </div>
            </div>
            <div>
              <span className="font-medium text-gray-900">Reconnect Attempts:</span>
              <div className="mt-1">
                {reconnectAttempts}/10
              </div>
            </div>
          </div>
          {lastConnected && (
            <div className="mt-4 text-xs text-gray-500">
              Last connected: {lastConnected.toLocaleString()}
            </div>
          )}
        </Card>
      </main>
    </div>
  );
}
