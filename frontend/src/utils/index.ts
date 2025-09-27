/**
 * Skylapse Utility Functions
 * Professional Mountain Timelapse Camera System
 */

import { type ClassValue, clsx } from 'clsx';

// Class name utility (combines clsx with Tailwind merge-like functionality)
export function cn(...inputs: ClassValue[]) {
  return clsx(inputs);
}

// Date and Time Utilities
export const dateUtils = {
  // Format timestamp for display
  formatTimestamp(timestamp: string | Date, format: 'short' | 'long' | 'time' = 'short'): string {
    const date = new Date(timestamp);

    switch (format) {
      case 'short':
        return date.toLocaleDateString();
      case 'long':
        return date.toLocaleDateString('en-US', {
          year: 'numeric',
          month: 'long',
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
        });
      case 'time':
        return date.toLocaleTimeString('en-US', {
          hour: '2-digit',
          minute: '2-digit',
        });
      default:
        return date.toISOString();
    }
  },

  // Get relative time (e.g., "2 minutes ago")
  getRelativeTime(timestamp: string | Date): string {
    const date = new Date(timestamp);
    const now = new Date();
    const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);

    if (diffInSeconds < 60) return 'just now';
    if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)} minutes ago`;
    if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)} hours ago`;
    if (diffInSeconds < 2592000) return `${Math.floor(diffInSeconds / 86400)} days ago`;

    return date.toLocaleDateString();
  },

  // Format duration in seconds to human readable
  formatDuration(seconds: number): string {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;

    if (hours > 0) {
      return `${hours}h ${minutes}m ${secs}s`;
    } else if (minutes > 0) {
      return `${minutes}m ${secs}s`;
    } else {
      return `${secs}s`;
    }
  },

  // Calculate next capture time
  getNextCaptureTime(interval: number, lastCapture?: string): Date {
    const last = lastCapture ? new Date(lastCapture) : new Date();
    return new Date(last.getTime() + interval * 1000);
  },
};

// File Size Utilities
export const fileUtils = {
  // Format bytes to human readable size
  formatFileSize(bytes: number): string {
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    let size = bytes;
    let unitIndex = 0;

    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024;
      unitIndex++;
    }

    return `${size.toFixed(unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
  },

  // Get file extension from filename
  getFileExtension(filename: string): string {
    return filename.split('.').pop()?.toLowerCase() || '';
  },

  // Check if file is image
  isImageFile(filename: string): boolean {
    const imageExtensions = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'raw', 'tiff'];
    return imageExtensions.includes(this.getFileExtension(filename));
  },

  // Check if file is video
  isVideoFile(filename: string): boolean {
    const videoExtensions = ['mp4', 'avi', 'mov', 'wmv', 'flv', 'webm', 'mkv'];
    return videoExtensions.includes(this.getFileExtension(filename));
  },
};

// Number Utilities
export const numberUtils = {
  // Format number with commas
  formatNumber(num: number): string {
    return num.toLocaleString();
  },

  // Format percentage
  formatPercentage(value: number, total: number, decimals = 1): string {
    const percentage = (value / total) * 100;
    return `${percentage.toFixed(decimals)}%`;
  },

  // Clamp number between min and max
  clamp(value: number, min: number, max: number): number {
    return Math.min(Math.max(value, min), max);
  },

  // Round to specified decimal places
  round(value: number, decimals = 2): number {
    return Math.round(value * Math.pow(10, decimals)) / Math.pow(10, decimals);
  },

  // Generate random ID
  generateId(): string {
    return Math.random().toString(36).substr(2, 9);
  },
};

// Color Utilities
export const colorUtils = {
  // Get status color class
  getStatusColor(status: string): string {
    const statusColors = {
      active: 'text-success-600 bg-success-100',
      paused: 'text-warning-600 bg-warning-100',
      error: 'text-error-600 bg-error-100',
      success: 'text-success-600 bg-success-100',
      loading: 'text-mountain-600 bg-mountain-100',
    };
    return statusColors[status as keyof typeof statusColors] || 'text-slate-600 bg-slate-100';
  },

  // Get progress bar color
  getProgressColor(percentage: number): string {
    if (percentage < 30) return 'bg-error-500';
    if (percentage < 70) return 'bg-warning-500';
    return 'bg-success-500';
  },

  // Generate avatar color from name
  getAvatarColor(name: string): string {
    const colors = [
      'bg-mountain-500',
      'bg-golden-500',
      'bg-success-500',
      'bg-warning-500',
      'bg-error-500',
    ];
    const index = name.charCodeAt(0) % colors.length;
    return colors[index];
  },
};

// Local Storage Utilities
export const storageUtils = {
  // Get item from localStorage with fallback
  getItem<T>(key: string, fallback: T): T {
    try {
      const item = localStorage.getItem(key);
      return item ? JSON.parse(item) : fallback;
    } catch {
      return fallback;
    }
  },

  // Set item in localStorage
  setItem<T>(key: string, value: T): void {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch (error) {
      console.warn('Failed to save to localStorage:', error);
    }
  },

  // Remove item from localStorage
  removeItem(key: string): void {
    try {
      localStorage.removeItem(key);
    } catch (error) {
      console.warn('Failed to remove from localStorage:', error);
    }
  },

  // Clear all items
  clear(): void {
    try {
      localStorage.clear();
    } catch (error) {
      console.warn('Failed to clear localStorage:', error);
    }
  },
};

// URL Utilities
export const urlUtils = {
  // Build URL with query parameters
  buildUrl(base: string, params: Record<string, any>): string {
    const url = new URL(base, window.location.origin);
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        url.searchParams.set(key, String(value));
      }
    });
    return url.toString();
  },

  // Parse query parameters from current URL
  getQueryParams(): Record<string, string> {
    const params = new URLSearchParams(window.location.search);
    const result: Record<string, string> = {};
    params.forEach((value, key) => {
      result[key] = value;
    });
    return result;
  },

  // Download file from URL
  downloadFile(url: string, filename: string): void {
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  },
};

// Validation Utilities
export const validationUtils = {
  // Validate email format
  isValidEmail(email: string): boolean {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  },

  // Validate required fields
  isRequired(value: any): boolean {
    return value !== null && value !== undefined && value !== '';
  },

  // Validate number range
  isInRange(value: number, min: number, max: number): boolean {
    return value >= min && value <= max;
  },

  // Validate ISO value
  isValidISO(iso: number): boolean {
    const validISOs = [100, 200, 400, 800, 1600, 3200, 6400];
    return validISOs.includes(iso);
  },

  // Validate exposure time
  isValidExposureTime(exposure: string): boolean {
    const exposureRegex = /^(1\/\d+|\d+)$/;
    return exposureRegex.test(exposure);
  },
};

// Async Utilities
export const asyncUtils = {
  // Delay function
  delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  },

  // Retry function with exponential backoff
  async retry<T>(
    fn: () => Promise<T>,
    maxAttempts = 3,
    baseDelay = 1000
  ): Promise<T> {
    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      try {
        return await fn();
      } catch (error) {
        if (attempt === maxAttempts) throw error;

        const delay = baseDelay * Math.pow(2, attempt - 1);
        await this.delay(delay);
      }
    }
    throw new Error('Max retry attempts reached');
  },

  // Debounce function
  debounce<T extends (...args: any[]) => void>(
    func: T,
    wait: number
  ): (...args: Parameters<T>) => void {
    let timeout: number;
    return (...args: Parameters<T>) => {
      clearTimeout(timeout);
      timeout = window.setTimeout(() => func(...args), wait);
    };
  },

  // Throttle function
  throttle<T extends (...args: any[]) => void>(
    func: T,
    wait: number
  ): (...args: Parameters<T>) => void {
    let inThrottle: boolean;
    return (...args: Parameters<T>) => {
      if (!inThrottle) {
        func(...args);
        inThrottle = true;
        window.setTimeout(() => inThrottle = false, wait);
      }
    };
  },
};

// Development Utilities
export const devUtils = {
  // Log with timestamp (only in development)
  log(...args: any[]): void {
    if (import.meta.env.DEV) {
      console.log(`[${new Date().toISOString()}]`, ...args);
    }
  },

  // Performance measurement
  performance: {
    start(label: string): void {
      if (import.meta.env.DEV) {
        performance.mark(`${label}-start`);
      }
    },

    end(label: string): void {
      if (import.meta.env.DEV) {
        performance.mark(`${label}-end`);
        performance.measure(label, `${label}-start`, `${label}-end`);
        const measurement = performance.getEntriesByName(label)[0];
        console.log(`Performance: ${label} took ${measurement.duration.toFixed(2)}ms`);
      }
    },
  },
};
