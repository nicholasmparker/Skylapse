/**
 * Capture Progress Panel - Active capture monitoring
 * Professional Mountain Timelapse Camera System
 */

import React from 'react';
import type { CaptureProgress } from '../../api/types';
import { Card, Button } from '../../design-system/components';
import {
  CameraIcon,
  PlayIcon,
  PauseIcon,
  StopIcon,
  ClockIcon,
  PhotoIcon
} from '@heroicons/react/24/outline';

interface CaptureProgressPanelProps {
  progress: CaptureProgress | null;
  isConnected: boolean;
}

export const CaptureProgressPanel: React.FC<CaptureProgressPanelProps> = ({
  progress,
  isConnected
}) => {
  const formatTimeRemaining = (seconds: number) => {
    if (seconds <= 0) return 'Now';

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
  };

  const formatEstimatedCompletion = (timestamp: string | undefined) => {
    if (!timestamp) return 'Unknown';

    const date = new Date(timestamp);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getProgressPercentage = () => {
    if (!progress?.totalCaptures || progress.totalCaptures === 0) return 0;
    return (progress.capturesCompleted / progress.totalCaptures) * 100;
  };

  const handleCaptureControl = async (action: 'start' | 'pause' | 'stop') => {
    try {
      const response = await fetch(`/api/v1/capture/${action}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error(`Failed to ${action} capture`);
      }
    } catch (error) {
      console.error(`Error ${action}ing capture:`, error);
      // TODO: Show toast notification
    }
  };

  return (
    <Card
      title="Capture Progress"
      subtitle="Active timelapse session monitoring"
      className="h-full"
    >
      <div className="space-y-6">

        {/* Capture Status */}
        <div className="flex items-center justify-between p-4 bg-mountain-50 rounded-lg">
          <div className="flex items-center space-x-3">
            <div className={`p-2 rounded-lg ${
              progress?.isActive
                ? 'bg-green-100 text-green-600'
                : 'bg-mountain-200 text-mountain-600'
            }`}>
              <CameraIcon className="w-6 h-6" />
            </div>
            <div>
              <div className="font-semibold text-mountain-900">
                {progress?.isActive ? 'Capture Active' : 'No Active Capture'}
              </div>
              <div className="text-sm text-mountain-600">
                {progress?.isActive
                  ? 'Timelapse sequence in progress'
                  : 'Ready to start new sequence'
                }
              </div>
            </div>
          </div>

          {progress?.isActive && (
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse-slow" />
              <span className="text-sm font-medium text-green-600">Recording</span>
            </div>
          )}
        </div>

        {/* Progress Details */}
        {progress?.isActive && (
          <div className="space-y-4">

            {/* Next Capture Countdown */}
            <div className="text-center p-4 bg-white border border-mountain-200 rounded-lg">
              <div className="flex items-center justify-center space-x-2 mb-2">
                <ClockIcon className="w-5 h-5 text-golden-500" />
                <span className="text-sm font-medium text-mountain-700">Next Capture In</span>
              </div>
              <div className="text-2xl font-bold text-golden-600">
                {formatTimeRemaining(progress.nextCaptureIn)}
              </div>
            </div>

            {/* Capture Statistics */}
            <div className="grid grid-cols-2 gap-4">

              {/* Captures Completed */}
              <div className="text-center p-3 bg-mountain-50 rounded-lg">
                <div className="flex items-center justify-center space-x-1 mb-1">
                  <PhotoIcon className="w-4 h-4 text-mountain-600" />
                  <span className="text-sm text-mountain-600">Completed</span>
                </div>
                <div className="text-lg font-semibold text-mountain-900">
                  {progress.capturesCompleted}
                  {progress.totalCaptures && (
                    <span className="text-sm text-mountain-500 ml-1">
                      / {progress.totalCaptures}
                    </span>
                  )}
                </div>
              </div>

              {/* Estimated Completion */}
              <div className="text-center p-3 bg-mountain-50 rounded-lg">
                <div className="text-sm text-mountain-600 mb-1">Est. Complete</div>
                <div className="text-sm font-medium text-mountain-900">
                  {formatEstimatedCompletion(progress.estimatedCompletion)}
                </div>
              </div>
            </div>

            {/* Progress Bar */}
            {progress.totalCaptures && progress.totalCaptures > 0 && (
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-mountain-600">Progress</span>
                  <span className="font-medium">{getProgressPercentage().toFixed(1)}%</span>
                </div>
                <div className="w-full bg-mountain-200 rounded-full h-2">
                  <div
                    className="bg-gradient-to-r from-golden-400 to-golden-600 h-2 rounded-full transition-all duration-500"
                    style={{ width: `${getProgressPercentage()}%` }}
                  />
                </div>
              </div>
            )}

            {/* Current Settings Summary */}
            {progress.currentSettings && (
              <div className="p-3 bg-white border border-mountain-200 rounded-lg">
                <div className="text-sm font-medium text-mountain-700 mb-2">Current Settings</div>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="flex justify-between">
                    <span className="text-mountain-600">ISO:</span>
                    <span className="font-medium">{progress.currentSettings.iso}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-mountain-600">Exposure:</span>
                    <span className="font-medium">{progress.currentSettings.exposureTime}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-mountain-600">Quality:</span>
                    <span className="font-medium">{progress.currentSettings.quality}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-mountain-600">HDR:</span>
                    <span className="font-medium">
                      {progress.currentSettings.hdr.enabled ? 'On' : 'Off'}
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Control Buttons */}
        <div className="pt-4 border-t border-mountain-200">
          {progress?.isActive ? (
            <div className="flex space-x-3">
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleCaptureControl('pause')}
                disabled={!isConnected}
                className="flex-1"
              >
                <PauseIcon className="w-4 h-4 mr-2" />
                Pause
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleCaptureControl('stop')}
                disabled={!isConnected}
                className="flex-1 border-red-300 text-red-600 hover:bg-red-50"
              >
                <StopIcon className="w-4 h-4 mr-2" />
                Stop
              </Button>
            </div>
          ) : (
            <Button
              variant="golden"
              size="md"
              onClick={() => handleCaptureControl('start')}
              disabled={!isConnected}
              className="w-full"
            >
              <PlayIcon className="w-4 h-4 mr-2" />
              Start New Capture
            </Button>
          )}

          {!isConnected && (
            <div className="mt-2 text-xs text-red-600 text-center">
              Connection required for capture controls
            </div>
          )}
        </div>
      </div>
    </Card>
  );
};
