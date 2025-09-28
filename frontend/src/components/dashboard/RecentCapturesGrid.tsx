/**
 * Recent Captures Grid - Latest timelapse sequences
 * Professional Mountain Timelapse Camera System
 */

import React from 'react';
import type { TimelapseSequence } from '../../api/types';
import { Card } from '../../design-system/components';
import {
  PlayIcon,
  EyeIcon,
  CalendarIcon,
  ClockIcon,
  PhotoIcon,
  ArrowTopRightOnSquareIcon
} from '@heroicons/react/24/outline';

interface RecentCapturesGridProps {
  captures: TimelapseSequence[];
  isConnected: boolean;
}

// Data validation helper
const validateCapture = (capture: any): capture is TimelapseSequence => {
  return (
    capture &&
    typeof capture === 'object' &&
    capture.id &&
    capture.name &&
    capture.startTime &&
    capture.status
  );
};

// Safe metadata access helper
const safeMetadata = (capture: TimelapseSequence) => {
  return capture.metadata || {};
};

export const RecentCapturesGrid: React.FC<RecentCapturesGridProps> = ({
  captures = [],
  isConnected
}) => {
  const formatDuration = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);

    if (hours > 0) {
      return `${hours}h ${minutes}m`;
    } else {
      return `${minutes}m`;
    }
  };

  const formatFileSize = (bytes: number) => {
    const sizes = ['B', 'KB', 'MB', 'GB'];
    if (bytes === 0) return '0 B';

    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${sizes[i]}`;
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'text-green-600 bg-green-100';
      case 'processing':
        return 'text-blue-600 bg-blue-100';
      case 'capturing':
        return 'text-golden-600 bg-golden-100';
      case 'failed':
        return 'text-red-600 bg-red-100';
      default:
        return 'text-mountain-600 bg-mountain-100';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return '✅';
      case 'processing':
        return '⚙️';
      case 'capturing':
        return '📸';
      case 'failed':
        return '❌';
      default:
        return '⏸️';
    }
  };

  const handleViewCapture = (capture: TimelapseSequence) => {
    // TODO: Navigate to gallery detail view
    console.log('View capture:', capture.id);
  };

  const handlePlayCapture = (capture: TimelapseSequence) => {
    // TODO: Open video player modal
    console.log('Play capture:', capture.id);
  };

  if (!isConnected) {
    return (
      <Card
        title="Recent Captures"
        subtitle="Latest timelapse sequences"
        className="h-full"
      >
        <div className="flex items-center justify-center h-32 bg-mountain-50 rounded-lg">
          <div className="text-center">
            <div className="text-mountain-400 text-4xl mb-2">📸</div>
            <div className="text-mountain-600 font-medium">No connection</div>
            <div className="text-sm text-mountain-500 mt-1">
              Connect to view recent captures
            </div>
          </div>
        </div>
      </Card>
    );
  }

  if (captures.length === 0) {
    return (
      <Card
        title="Recent Captures"
        subtitle="Latest timelapse sequences"
        className="h-full"
      >
        <div className="flex items-center justify-center h-32 bg-mountain-50 rounded-lg">
          <div className="text-center">
            <div className="text-mountain-400 text-4xl mb-2">🎬</div>
            <div className="text-mountain-600 font-medium">No captures yet</div>
            <div className="text-sm text-mountain-500 mt-1">
              Start your first timelapse to see it here
            </div>
          </div>
        </div>
      </Card>
    );
  }

  return (
    <Card
      title="Recent Captures"
      subtitle={`${captures.length} latest timelapse sequences`}
      actions={
        <button className="text-sm text-blue-600 hover:text-blue-700 flex items-center space-x-1">
          <span>View All</span>
          <ArrowTopRightOnSquareIcon className="w-4 h-4" />
        </button>
      }
      className="h-full"
    >
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {captures.filter(validateCapture).map((capture) => (
          <div
            key={capture.id}
            className="group relative bg-white border border-mountain-200 rounded-lg overflow-hidden hover:shadow-md transition-all duration-200"
          >
            {/* Thumbnail */}
            <div className="relative aspect-video bg-mountain-100">
              {capture.thumbnail ? (
                <img
                  src={capture.thumbnail}
                  alt={capture.name}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="flex items-center justify-center h-full bg-mountain-100">
                  <PhotoIcon className="w-8 h-8 text-mountain-400" />
                </div>
              )}

              {/* Play Overlay */}
              <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-30 transition-all duration-200 flex items-center justify-center">
                <button
                  onClick={() => handlePlayCapture(capture)}
                  className="opacity-0 group-hover:opacity-100 transition-opacity duration-200 bg-white bg-opacity-90 rounded-full p-3 hover:bg-opacity-100"
                >
                  <PlayIcon className="w-6 h-6 text-mountain-900" />
                </button>
              </div>

              {/* Status Badge */}
              <div className="absolute top-2 right-2">
                <span className={`inline-flex items-center space-x-1 px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(capture.status)}`}>
                  <span>{getStatusIcon(capture.status)}</span>
                  <span className="capitalize">{capture.status}</span>
                </span>
              </div>
            </div>

            {/* Content */}
            <div className="p-4">
              <div className="flex items-start justify-between mb-2">
                <h3 className="font-medium text-mountain-900 truncate pr-2">
                  {capture.name}
                </h3>
                <button
                  onClick={() => handleViewCapture(capture)}
                  className="text-mountain-400 hover:text-mountain-600 transition-colors"
                >
                  <EyeIcon className="w-4 h-4" />
                </button>
              </div>

              {/* Metadata */}
              <div className="space-y-2 text-sm text-mountain-600">

                {/* Date and Duration */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-1">
                    <CalendarIcon className="w-3 h-3" />
                    <span>{new Date(capture.startTime).toLocaleDateString()}</span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <ClockIcon className="w-3 h-3" />
                    <span>{formatDuration(safeMetadata(capture).duration || 0)}</span>
                  </div>
                </div>

                {/* Capture Count and File Size */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-1">
                    <PhotoIcon className="w-3 h-3" />
                    <span>{capture.captureCount} frames</span>
                  </div>
                  <div className="text-xs">
                    {formatFileSize(safeMetadata(capture).fileSize || 0)}
                  </div>
                </div>

                {/* Location */}
                {safeMetadata(capture).location && (
                  <div className="text-xs text-mountain-500 truncate">
                    📍 {safeMetadata(capture).location?.name || 'Unknown'}
                  </div>
                )}

                {/* Weather */}
                {safeMetadata(capture).weather && (
                  <div className="text-xs text-mountain-500">
                    🌤️ {safeMetadata(capture).weather?.condition || 'Unknown'}, {safeMetadata(capture).weather?.temperature || 'N/A'}°C
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
};
