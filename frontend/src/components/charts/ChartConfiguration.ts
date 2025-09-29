/**
 * Optimized Chart.js Configuration
 * Professional Mountain Timelapse Camera System
 *
 * Tree-shaken imports and lazy-loaded chart setup
 */

// Import only the Chart.js components we actually use
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
  type ChartOptions
} from 'chart.js';

// Register only the components we need
let isChartJSRegistered = false;

export function initializeChartJS() {
  if (!isChartJSRegistered) {
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
    isChartJSRegistered = true;
  }
}

// Shared chart options for consistent styling and performance
export const getOptimizedChartOptions = (): ChartOptions<'line'> => ({
  responsive: true,
  maintainAspectRatio: false,

  // Performance optimizations
  animation: {
    duration: 300, // Reduced from 750ms for better performance
  },

  // Reduce memory usage by limiting data points
  interaction: {
    mode: 'index',
    intersect: false,
  },

  // Efficient plugin configuration
  plugins: {
    legend: {
      position: 'top',
      labels: {
        usePointStyle: true,
        padding: 20,
        boxWidth: 12,
      }
    },
    tooltip: {
      backgroundColor: 'rgba(15, 23, 42, 0.95)',
      titleColor: '#f8fafc',
      bodyColor: '#f1f5f9',
      borderColor: '#64748b',
      borderWidth: 1,
      cornerRadius: 8,
      displayColors: true,
      // Optimize tooltip rendering
      caretPadding: 8,
      callbacks: {
        title: (context) => `Time: ${context[0].label}`,
        label: (context) => {
          const label = context.dataset.label || '';
          const value = context.parsed.y;
          return label.includes('Temperature')
            ? `${label}: ${value.toFixed(1)}°C`
            : `${label}: ${value.toFixed(1)}%`;
        }
      }
    }
  },

  // Optimized scales
  scales: {
    x: {
      display: true,
      title: {
        display: true,
        text: 'Time'
      },
      ticks: {
        maxTicksLimit: 8, // Reduced for better performance
        autoSkip: true,
      },
      grid: {
        color: 'rgba(148, 163, 184, 0.2)',
        lineWidth: 1,
      }
    },
    y: {
      type: 'linear',
      display: true,
      position: 'left',
      title: {
        display: true,
        text: 'Usage (%)'
      },
      min: 0,
      max: 100,
      ticks: {
        stepSize: 20,
        callback: (value) => `${value}%`
      },
      grid: {
        color: 'rgba(148, 163, 184, 0.2)',
        lineWidth: 1,
      }
    },
    temperature: {
      type: 'linear',
      display: true,
      position: 'right',
      title: {
        display: true,
        text: 'Temperature (°C)'
      },
      min: 20,
      max: 80,
      ticks: {
        stepSize: 10,
        callback: (value) => `${value}°C`
      },
      grid: {
        drawOnChartArea: false,
        lineWidth: 1,
      }
    }
  },

  // Optimize point rendering
  elements: {
    point: {
      radius: 0, // Hide points by default for better performance
      hoverRadius: 4,
      hoverBackgroundColor: '#ffffff',
      hoverBorderWidth: 2
    },
    line: {
      borderWidth: 2,
      tension: 0.3, // Slightly reduced for better performance
    }
  },

  // Dataset defaults for consistent styling
  datasets: {
    line: {
      pointRadius: 0,
      pointHoverRadius: 4,
      fill: true,
      tension: 0.3,
    }
  }
});

// Predefined color schemes for consistent chart styling
export const CHART_COLORS = {
  cpu: {
    border: 'rgb(59, 130, 246)', // blue-500
    background: 'rgba(59, 130, 246, 0.1)',
  },
  memory: {
    border: 'rgb(245, 158, 11)', // amber-500
    background: 'rgba(245, 158, 11, 0.1)',
  },
  temperature: {
    border: 'rgb(239, 68, 68)', // red-500
    background: 'rgba(239, 68, 68, 0.1)',
  },
  storage: {
    border: 'rgb(139, 69, 19)', // saddle-brown
    background: 'rgba(139, 69, 19, 0.1)',
  },
  network: {
    border: 'rgb(34, 197, 94)', // green-500
    background: 'rgba(34, 197, 94, 0.1)',
  }
} as const;
