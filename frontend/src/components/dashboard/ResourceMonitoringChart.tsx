/**
 * Resource Monitoring Chart - Real-time system metrics visualization
 * Professional Mountain Timelapse Camera System
 */

import React, { useMemo, useEffect } from 'react';
import { Line } from 'react-chartjs-2';
import type { ResourceMetrics } from '../../api/types';
import { Card } from '../../design-system/components';
import {
  initializeChartJS,
  getOptimizedChartOptions,
  CHART_COLORS
} from '../charts/ChartConfiguration';

// Initialize Chart.js with only the components we need
initializeChartJS();

interface ResourceMonitoringChartProps {
  metrics: ResourceMetrics[];
  isConnected: boolean;
}

export const ResourceMonitoringChart: React.FC<ResourceMonitoringChartProps> = ({
  metrics,
  isConnected
}) => {
  const chartData = useMemo(() => {
    // Optimize by limiting to last 30 data points for better performance
    const limitedMetrics = metrics.slice(-30);

    // Generate time labels
    const labels = limitedMetrics.map((_, index) => {
      const now = new Date();
      const timeAgo = new Date(now.getTime() - (limitedMetrics.length - 1 - index) * 5000);
      return timeAgo.toLocaleTimeString('en-US', {
        hour12: false,
        minute: '2-digit',
        second: '2-digit'
      });
    });

    // Extract data series with optimized structure
    const cpuData = limitedMetrics.map(m => m.cpu.usage);
    const memoryData = limitedMetrics.map(m => m.memory.percentage);
    const temperatureData = limitedMetrics.map(m => m.cpu.temperature);

    return {
      labels,
      datasets: [
        {
          label: 'CPU Usage (%)',
          data: cpuData,
          borderColor: CHART_COLORS.cpu.border,
          backgroundColor: CHART_COLORS.cpu.background,
        },
        {
          label: 'Memory Usage (%)',
          data: memoryData,
          borderColor: CHART_COLORS.memory.border,
          backgroundColor: CHART_COLORS.memory.background,
        },
        {
          label: 'Temperature (°C)',
          data: temperatureData,
          borderColor: CHART_COLORS.temperature.border,
          backgroundColor: CHART_COLORS.temperature.background,
          fill: false,
          yAxisID: 'temperature',
        }
      ]
    };
  }, [metrics]);

  const chartOptions = useMemo(() => getOptimizedChartOptions(), []);

  const currentMetrics = metrics[metrics.length - 1];

  return (
    <Card
      title="Resource Monitoring"
      subtitle="Real-time system performance metrics"
      className="h-full"
    >
      <div className="space-y-4">

        {/* Current Values Summary */}
        {currentMetrics && (
          <div className="grid grid-cols-3 gap-4 p-4 bg-mountain-50 rounded-lg">
            <div className="text-center">
              <div className="text-lg font-semibold text-blue-600">
                {currentMetrics.cpu.usage.toFixed(1)}%
              </div>
              <div className="text-sm text-mountain-600">CPU</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-semibold text-golden-600">
                {currentMetrics.memory.percentage.toFixed(1)}%
              </div>
              <div className="text-sm text-mountain-600">Memory</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-semibold text-red-600">
                {currentMetrics.cpu.temperature.toFixed(1)}°C
              </div>
              <div className="text-sm text-mountain-600">Temp</div>
            </div>
          </div>
        )}

        {/* Chart Container */}
        <div className="relative h-64">
          {metrics.length > 0 ? (
            <Line data={chartData} options={chartOptions} />
          ) : (
            <div className="flex items-center justify-center h-full bg-mountain-50 rounded-lg">
              <div className="text-center">
                <div className="text-mountain-400 text-4xl mb-2">📊</div>
                <div className="text-mountain-600 font-medium">
                  {isConnected ? 'Waiting for data...' : 'No connection'}
                </div>
                <div className="text-sm text-mountain-500 mt-1">
                  {isConnected
                    ? 'Resource metrics will appear here'
                    : 'Connect to view real-time metrics'
                  }
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Status Indicators */}
        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center space-x-2">
            <div className={`w-2 h-2 rounded-full ${
              isConnected ? 'bg-green-500 animate-pulse-slow' : 'bg-red-500'
            }`} />
            <span className="text-mountain-600">
              {isConnected ? 'Live updates' : 'Disconnected'}
            </span>
          </div>

          <div className="text-mountain-500">
            {metrics.length > 0 && (
              <>Data points: {metrics.length}</>
            )}
          </div>
        </div>
      </div>
    </Card>
  );
};
