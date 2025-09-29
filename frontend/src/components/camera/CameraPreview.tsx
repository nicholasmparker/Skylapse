/**
 * Live Camera Preview Component
 * Professional Mountain Timelapse Camera System
 */

import React, { useState, useEffect, useRef } from 'react';
import { apiClient } from '@/api/client';
import { cn } from '@/utils';

interface CameraPreviewProps {
  className?: string;
  showControls?: boolean;
  showOverlay?: boolean;
  autoStart?: boolean;
}

interface CameraStatus {
  initialized: boolean;
  running: boolean;
  camera_model: string;
  capabilities: string[];
  current_settings: {
    exposure_time_us: number | null;
    iso: number | null;
    exposure_compensation: number;
    focus_distance_mm: number | null;
    autofocus_enabled: boolean;
    white_balance_k: number | null;
    white_balance_mode: string;
    quality: number;
    format: string;
  };
  performance: {
    total_captures: number;
    successful_captures: number;
    failed_captures: number;
    average_capture_time_ms: number;
    last_capture_time: number;
  };
}

export const CameraPreview: React.FC<CameraPreviewProps> = ({
  className,
  showControls = true,
  showOverlay = true,
  autoStart = true,
}) => {
  const [isLoading, setIsLoading] = useState(true);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isCapturing, setIsCapturing] = useState(false);
  const [cameraStatus, setCameraStatus] = useState<CameraStatus | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const imgRef = useRef<HTMLImageElement>(null);
  const refreshIntervalRef = useRef<NodeJS.Timeout>();

  // Get the camera preview URL from our configurable API client
  const previewURL = apiClient.capture.getCameraPreviewURL();

  useEffect(() => {
    if (autoStart) {
      startPreview();
    }

    return () => {
      stopPreview();
    };
  }, [autoStart]);

  const startPreview = async () => {
    try {
      setIsLoading(true);
      setError(null);

      // Check camera status first
      const statusResponse = await apiClient.capture.getCameraStatus();
      if (statusResponse.data) {
        setCameraStatus(statusResponse.data);
      }

      // Test if preview endpoint is available before starting stream
      const testResponse = await fetch(`${previewURL}?test=true`);
      if (!testResponse.ok) {
        if (testResponse.status === 404) {
          setError('Live preview feature not available on camera service');
        } else {
          setError('Camera preview service temporarily unavailable');
        }
        return;
      }

      // Start streaming
      setIsStreaming(true);

      // Force initial image load without waiting for state update
      if (imgRef.current) {
        const timestamp = Date.now();
        const url = `${previewURL}?t=${timestamp}`;
        imgRef.current.src = url;
        setLastUpdate(new Date());
      }

      // Set up refresh interval for live updates
      refreshIntervalRef.current = setInterval(() => {
        refreshImage();
      }, 100); // ~10 FPS refresh rate

    } catch (err) {
      if (err instanceof Error && err.message.includes('Failed to fetch')) {
        setError('Cannot connect to camera service - check network connection');
      } else {
        setError(err instanceof Error ? err.message : 'Failed to start camera preview');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const stopPreview = () => {
    setIsStreaming(false);
    if (refreshIntervalRef.current) {
      clearInterval(refreshIntervalRef.current);
    }
  };

  const refreshImage = () => {
    if (!isStreaming || !imgRef.current) return;

    // Add timestamp to prevent caching
    const timestamp = Date.now();
    const url = `${previewURL}?t=${timestamp}`;

    imgRef.current.src = url;
    setLastUpdate(new Date());
  };

  const handleManualCapture = async () => {
    try {
      setIsCapturing(true);
      setError(null);

      const response = await apiClient.capture.manualCapture();

      if (response.data) {
        // Optionally show capture success feedback
        console.log('Capture successful:', response.data);
      }

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to capture image');
    } finally {
      setIsCapturing(false);
    }
  };

  const handleImageError = () => {
    setError('Camera preview service unavailable');
    setIsLoading(false);
  };

  const handleImageLoad = () => {
    setIsLoading(false);
    setError(null);
  };

  return (
    <div className={cn('relative bg-mountain-900 rounded-lg overflow-hidden', className)}>
      {/* Preview Image */}
      <div className="relative aspect-[4/3] bg-mountain-800">
        {isStreaming ? (
          <img
            ref={imgRef}
            alt="Live Camera Preview"
            className="w-full h-full object-contain"
            onLoad={handleImageLoad}
            onError={handleImageError}
          />
        ) : error ? (
          <div className="flex items-center justify-center h-full text-mountain-400">
            <div className="text-center max-w-md p-6">
              <div className="text-6xl mb-4">📷</div>
              <div className="text-lg font-medium text-mountain-300 mb-2">Camera Preview Unavailable</div>
              <div className="text-sm mb-4">{error}</div>
              {cameraStatus ? (
                <div className="bg-mountain-800 rounded-lg p-4 text-left">
                  <div className="text-sm font-medium text-golden-400 mb-2">Camera Status</div>
                  <div className="space-y-1 text-xs">
                    <div>Model: {cameraStatus.camera_model}</div>
                    <div>Status: {cameraStatus.running ? 'Running' : 'Stopped'}</div>
                    <div>Captures: {cameraStatus.performance.successful_captures}/{cameraStatus.performance.total_captures}</div>
                  </div>
                </div>
              ) : (
                <div className="text-sm text-mountain-500">
                  Manual capture controls are still available
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-mountain-400">
            <div className="text-center">
              <div className="text-6xl mb-4">📷</div>
              <div className="text-lg font-medium">Camera Preview</div>
              <div className="text-sm">Click start to begin live preview</div>
            </div>
          </div>
        )}

        {/* Loading Overlay */}
        {isLoading && (
          <div className="absolute inset-0 bg-mountain-900/75 flex items-center justify-center">
            <div className="text-center text-white">
              <div className="animate-spin w-8 h-8 border-2 border-white border-t-transparent rounded-full mx-auto mb-2"></div>
              <div>Loading camera...</div>
            </div>
          </div>
        )}

        {/* Settings Overlay */}
        {showOverlay && cameraStatus && isStreaming && (
          <div className="absolute top-4 left-4 bg-black/75 text-white p-3 rounded-lg text-sm space-y-1">
            <div className="font-medium text-golden-400">{cameraStatus.camera_model}</div>
            {cameraStatus.current_settings.iso && (
              <div>ISO: {cameraStatus.current_settings.iso}</div>
            )}
            {cameraStatus.current_settings.exposure_time_us && (
              <div>Exposure: 1/{Math.round(1000000 / cameraStatus.current_settings.exposure_time_us)}s</div>
            )}
            <div>WB: {cameraStatus.current_settings.white_balance_mode}</div>
            <div className="text-xs text-mountain-300 pt-1">
              Updated: {lastUpdate.toLocaleTimeString()}
            </div>
          </div>
        )}

        {/* Capture Indicator */}
        {isCapturing && (
          <div className="absolute top-4 right-4 bg-red-600 text-white px-3 py-2 rounded-lg flex items-center space-x-2">
            <div className="w-3 h-3 bg-red-400 rounded-full animate-pulse"></div>
            <span className="text-sm font-medium">CAPTURING</span>
          </div>
        )}

        {/* Status Indicator */}
        <div className="absolute bottom-4 left-4 flex items-center space-x-2">
          <div className={cn(
            'w-3 h-3 rounded-full',
            isStreaming ? 'bg-green-500 animate-pulse' : 'bg-red-500'
          )}></div>
          <span className="text-white text-sm">
            {isStreaming ? 'LIVE' : 'OFFLINE'}
          </span>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="p-4 bg-red-600/10 border border-red-600/25 text-red-400">
          <div className="flex items-center space-x-2">
            <span className="text-lg">⚠️</span>
            <span>{error}</span>
          </div>
        </div>
      )}

      {/* Controls */}
      {showControls && (
        <div className="p-4 bg-mountain-800 border-t border-mountain-700">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              {!isStreaming ? (
                <button
                  onClick={startPreview}
                  className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium transition-colors"
                  disabled={isLoading}
                >
                  Start Preview
                </button>
              ) : (
                <button
                  onClick={stopPreview}
                  className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium transition-colors"
                >
                  Stop Preview
                </button>
              )}

              <button
                onClick={handleManualCapture}
                disabled={!isStreaming || isCapturing}
                className={cn(
                  'px-4 py-2 rounded-lg font-medium transition-colors',
                  isStreaming && !isCapturing
                    ? 'bg-golden-600 hover:bg-golden-700 text-white'
                    : 'bg-mountain-600 text-mountain-400 cursor-not-allowed'
                )}
              >
                {isCapturing ? 'Capturing...' : 'Capture Photo'}
              </button>
            </div>

            {cameraStatus && (
              <div className="text-sm text-mountain-400">
                <div>Captures: {cameraStatus.performance.total_captures}</div>
                <div>Success: {cameraStatus.performance.successful_captures}/{cameraStatus.performance.total_captures}</div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default CameraPreview;
