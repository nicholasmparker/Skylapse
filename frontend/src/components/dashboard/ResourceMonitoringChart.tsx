/**
 * Resource Monitoring Chart - Real-time system metrics visualization
 * Professional Mountain Timelapse Camera System
 */

import React, { useMemo } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';
import { Line } from 'react-chartjs-2';
import type { ResourceMetrics } from '../../api/types';
import { Card } from '../../design-system/components';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

interface ResourceMonitoringChartProps {
  metrics: ResourceMetrics[];
  isConnected: boolean;
}

export const ResourceMonitoringChart: React.FC<ResourceMonitoringChartProps> = ({
  metrics,
  isConnected
}) => {
  const chartData = useMemo(() => {
    // Generate time labels for the last 50 data points
    const labels = metrics.slice(-50).map((_, index) => {
      const now = new Date();
      const timeAgo = new Date(now.getTime() - (49 - index) * 5000); // 5 second intervals
      return timeAgo.toLocaleTimeString('en-US', {
        hour12: false,
        minute: '2-digit',
        second: '2-digit'
      });
    });

    // Extract data series
    const cpuData = metrics.slice(-50).map(m => m.cpu.usage);
    const memoryData = metrics.slice(-50).map(m => m.memory.percentage);
    const temperatureData = metrics.slice(-50).map(m => m.cpu.temperature);

    return {
      labels,
      datasets: [
        {
          label: 'CPU Usage (%)',
          data: cpuData,
          borderColor: 'rgb(59, 130, 246)', // blue-500
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          borderWidth: 2,
          fill: true,
          tension: 0.4,
          pointRadius: 0,
          pointHoverRadius: 4,
        },
        {
          label: 'Memory Usage (%)',
          data: memoryData,
          borderColor: 'rgb(245, 158, 11)', // golden-500
          backgroundColor: 'rgba(245, 158, 11, 0.1)',
          borderWidth: 2,
          fill: true,
          tension: 0.4,
          pointRadius: 0,
          pointHoverRadius: 4,
        },
        {
          label: 'Temperature (°C)',
          data: temperatureData,
          borderColor: 'rgb(239, 68, 68)', // red-500
          backgroundColor: 'rgba(239, 68, 68, 0.1)',
          borderWidth: 2,
          fill: false,
          tension: 0.4,
          pointRadius: 0,
          pointHoverRadius: 4,
          yAxisID: 'temperature',
        }
      ]
    };
  }, [metrics]);

  const chartOptions = useMemo(() => ({
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: 'index' as const,
      intersect: false,
    },
    plugins: {
      legend: {
        position: 'top' as const,
        labels: {
          usePointStyle: true,
          padding: 20,
        }
      },
      tooltip: {
        backgroundColor: 'rgba(15, 23, 42, 0.9)',
        titleColor: '#f8fafc',
        bodyColor: '#f1f5f9',
        borderColor: '#64748b',
        borderWidth: 1,
        cornerRadius: 8,
        displayColors: true,
        callbacks: {
          title: (context: any) => `Time: ${context[0].label}`,
          label: (context: any) => {
            const label = context.dataset.label;
            const value = context.parsed.y;
            return label.includes('Temperature')
              ? `${label}: ${value.toFixed(1)}°C`
              : `${label}: ${value.toFixed(1)}%`;
          }
        }
      }
    },
    scales: {
      x: {
        display: true,
        title: {
          display: true,
          text: 'Time'
        },
        ticks: {
          maxTicksLimit: 10
        },
        grid: {
          color: 'rgba(148, 163, 184, 0.2)'
        }
      },
      y: {
        type: 'linear' as const,
        display: true,
        position: 'left' as const,
        title: {
          display: true,
          text: 'Usage (%)'
        },
        min: 0,
        max: 100,
        ticks: {
          callback: (value: any) => `${value}%`
        },
        grid: {
          color: 'rgba(148, 163, 184, 0.2)'
        }
      },
      temperature: {
        type: 'linear' as const,
        display: true,
        position: 'right' as const,
        title: {
          display: true,
          text: 'Temperature (°C)'
        },
        min: 20,
        max: 80,
        ticks: {
          callback: (value: any) => `${value}°C`
        },
        grid: {
          drawOnChartArea: false
        }
      }
    },
    elements: {
      point: {
        hoverBackgroundColor: '#ffffff',
        hoverBorderWidth: 2
      }
    },
    animation: {
      duration: 750
    }
  } as any), []);

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
