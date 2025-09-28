/**
 * Video Generation Interface - Professional timelapse video creation
 * UI-006: Video Generation Interface
 */

import React, { useState, useEffect } from 'react';
import { apiClient } from '@/api/client';
import { Card } from '@/design-system/components';
import { cn } from '@/utils';

interface TimelapseSequence {
  id: string;
  title: string;
  createdAt: string;
  frameCount: number;
  duration: string;
  thumbnailUrl: string;
  metadata: {
    location: { lat: number; lng: number; name: string };
    captureSettings: any;
    weather: any;
  };
  fileSize: number;
  quality: 'excellent' | 'good' | 'fair';
}

interface VideoGenerationJob {
  id: string;
  sequenceId: string;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  progress: number;
  startedAt: string;
  completedAt?: string;
  settings: VideoGenerationSettings;
  outputUrl?: string;
  fileSize?: number;
  duration?: number;
  error?: string;
}

interface VideoGenerationSettings {
  format: 'mp4' | 'webm' | 'mov';
  resolution: '4K' | '1080p' | '720p';
  frameRate: 24 | 30 | 60;
  quality: 'ultra' | 'high' | 'medium' | 'low';
  speedMultiplier: number;
  includeAudio: boolean;
  audioTrack?: 'none' | 'ambient' | 'nature' | 'cinematic';
  watermark: boolean;
  colorGrading: 'none' | 'cinematic' | 'vibrant' | 'natural';
  stabilization: boolean;
  cropToAspectRatio: '16:9' | '4:3' | '21:9' | 'original';
}

const DEFAULT_SETTINGS: VideoGenerationSettings = {
  format: 'mp4',
  resolution: '4K',
  frameRate: 30,
  quality: 'high',
  speedMultiplier: 24, // 24x speed (1 hour = 2.5 minutes)
  includeAudio: false,
  audioTrack: 'none',
  watermark: true,
  colorGrading: 'cinematic',
  stabilization: true,
  cropToAspectRatio: '16:9',
};

const SPEED_PRESETS = [
  { label: '10x Speed', value: 10, description: '1 hour = 6 minutes' },
  { label: '24x Speed', value: 24, description: '1 hour = 2.5 minutes' },
  { label: '60x Speed', value: 60, description: '1 hour = 1 minute' },
  { label: '120x Speed', value: 120, description: '1 hour = 30 seconds' },
  { label: '300x Speed', value: 300, description: '1 hour = 12 seconds' },
];

const QUALITY_PRESETS = [
  {
    id: 'ultra',
    name: 'Ultra Quality',
    description: 'Maximum quality for professional use',
    bitrate: '50 Mbps',
    fileSize: 'Very Large'
  },
  {
    id: 'high',
    name: 'High Quality',
    description: 'Great balance of quality and file size',
    bitrate: '25 Mbps',
    fileSize: 'Large'
  },
  {
    id: 'medium',
    name: 'Medium Quality',
    description: 'Good for web sharing and preview',
    bitrate: '12 Mbps',
    fileSize: 'Medium'
  },
  {
    id: 'low',
    name: 'Low Quality',
    description: 'Fast processing for quick previews',
    bitrate: '6 Mbps',
    fileSize: 'Small'
  },
];

export const VideoGenerationInterface: React.FC = () => {
  const [sequences, setSequences] = useState<TimelapseSequence[]>([]);
  const [selectedSequence, setSelectedSequence] = useState<TimelapseSequence | null>(null);
  const [settings, setSettings] = useState<VideoGenerationSettings>(DEFAULT_SETTINGS);
  const [jobs, setJobs] = useState<VideoGenerationJob[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'sequences' | 'settings' | 'jobs'>('sequences');

  useEffect(() => {
    loadSequences();
    loadJobs();
  }, []);

  const loadSequences = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const response = await apiClient.processing.getTimelapseSequences();

      if (response.data) {
        setSequences(response.data.sequences || []);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load timelapse sequences');
      setSequences([]);
    } finally {
      setIsLoading(false);
    }
  };

  const loadJobs = async () => {
    try {
      const response = await apiClient.processing.getVideoJobs();
      if (response.data && Array.isArray(response.data)) {
        setJobs(response.data);
      } else {
        setJobs([]);
      }
    } catch (err) {
      console.warn('Could not load jobs:', err);
      setJobs([]);
    }
  };

  const generateVideo = async () => {
    if (!selectedSequence) return;

    try {
      setError(null);
      setIsLoading(true);

      const response = await apiClient.processing.generateVideo(selectedSequence.id, settings);

      if (response.data) {
        // Add new job to the list
        const newJob: VideoGenerationJob = {
          id: response.data.jobId || `job-${Date.now()}`,
          sequenceId: selectedSequence.id,
          status: 'queued',
          progress: 0,
          startedAt: new Date().toISOString(),
          settings: { ...settings },
        };

        setJobs(prev => [newJob, ...prev]);
        setActiveTab('jobs');

        console.log('Video generation started:', response.data);
      }

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start video generation');
    } finally {
      setIsLoading(false);
    }
  };

  const updateSettings = (field: keyof VideoGenerationSettings, value: any) => {
    setSettings(prev => ({
      ...prev,
      [field]: value,
    }));
  };

  const formatFileSize = (gb: number): string => {
    if (gb >= 1) {
      return `${gb.toFixed(1)} GB`;
    } else {
      return `${(gb * 1000).toFixed(0)} MB`;
    }
  };

  const formatDuration = (minutes: number): string => {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return `${hours}h ${mins}m`;
  };

  const getQualityBadgeColor = (quality: string) => {
    switch (quality) {
      case 'excellent': return 'bg-green-100 text-green-800';
      case 'good': return 'bg-blue-100 text-blue-800';
      case 'fair': return 'bg-yellow-100 text-yellow-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'text-green-600';
      case 'processing': return 'text-blue-600';
      case 'queued': return 'text-yellow-600';
      case 'failed': return 'text-red-600';
      default: return 'text-gray-600';
    }
  };

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-mountain-900">
              🎬 Video Generation
            </h1>
            <p className="text-mountain-600 mt-2">
              Create professional timelapse videos from captured sequences
            </p>
          </div>

          <button
            onClick={generateVideo}
            disabled={!selectedSequence || isLoading}
            className={cn(
              'px-6 py-3 rounded-lg font-medium transition-colors',
              selectedSequence && !isLoading
                ? 'bg-golden-600 hover:bg-golden-700 text-white shadow-lg'
                : 'bg-mountain-300 text-mountain-500 cursor-not-allowed'
            )}
          >
            {isLoading ? 'Starting Generation...' : 'Generate Video'}
          </button>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="mb-6">
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="flex items-center">
              <span className="text-red-500 text-lg mr-2">⚠️</span>
              <span className="text-red-700">{error}</span>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">

        {/* Main Content */}
        <div className="xl:col-span-2 space-y-6">

          {/* Tab Navigation */}
          <Card>
            <div className="border-b border-mountain-200">
              <nav className="flex space-x-8 px-6 py-4">
                {[
                  { id: 'sequences', label: 'Select Sequence', icon: '📁' },
                  { id: 'settings', label: 'Video Settings', icon: '⚙️' },
                  { id: 'jobs', label: 'Generation Jobs', icon: '🔄' },
                ].map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id as any)}
                    className={cn(
                      'flex items-center space-x-2 py-2 px-1 border-b-2 font-medium text-sm transition-colors',
                      activeTab === tab.id
                        ? 'border-golden-500 text-golden-600'
                        : 'border-transparent text-mountain-500 hover:text-mountain-700 hover:border-mountain-300'
                    )}
                  >
                    <span>{tab.icon}</span>
                    <span>{tab.label}</span>
                  </button>
                ))}
              </nav>
            </div>

            <div className="p-6">
              {/* Sequences Tab */}
              {activeTab === 'sequences' && (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-lg font-semibold text-mountain-900 mb-4">
                      Available Timelapse Sequences
                    </h3>
                    <p className="text-mountain-600 mb-6">
                      Select a sequence to generate a professional timelapse video
                    </p>
                  </div>

                  {isLoading ? (
                    <div className="text-center py-8">
                      <div className="animate-spin w-8 h-8 border-2 border-golden-500 border-t-transparent rounded-full mx-auto mb-4"></div>
                      <p className="text-mountain-600">Loading sequences...</p>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {sequences.map((sequence) => (
                        <div
                          key={sequence.id}
                          className={cn(
                            'p-4 border-2 rounded-lg cursor-pointer transition-all hover:shadow-md',
                            selectedSequence?.id === sequence.id
                              ? 'border-golden-500 bg-golden-50'
                              : 'border-mountain-200 hover:border-mountain-300'
                          )}
                          onClick={() => setSelectedSequence(sequence)}
                        >
                          <div className="flex items-start space-x-4">
                            <div className="w-20 h-14 bg-mountain-100 rounded-lg flex items-center justify-center">
                              <span className="text-2xl">🏔️</span>
                            </div>
                            <div className="flex-1">
                              <div className="flex items-start justify-between">
                                <div>
                                  <h4 className="font-semibold text-mountain-900">
                                    {sequence.title}
                                  </h4>
                                  <p className="text-sm text-mountain-600 mt-1">
                                    {sequence.metadata.location.name}
                                  </p>
                                  <div className="flex items-center space-x-4 mt-2 text-sm text-mountain-500">
                                    <span>{sequence.frameCount} frames</span>
                                    <span>{sequence.duration}</span>
                                    <span>{formatFileSize(sequence.fileSize)}</span>
                                  </div>
                                </div>
                                <div className="flex items-center space-x-2">
                                  <span className={cn(
                                    'px-2 py-1 text-xs font-medium rounded-full',
                                    getQualityBadgeColor(sequence.quality)
                                  )}>
                                    {sequence.quality}
                                  </span>
                                </div>
                              </div>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Settings Tab */}
              {activeTab === 'settings' && (
                <div className="space-y-8">
                  <div>
                    <h3 className="text-lg font-semibold text-mountain-900 mb-4">
                      Video Generation Settings
                    </h3>
                    <p className="text-mountain-600 mb-6">
                      Configure output format, quality, and processing options
                    </p>
                  </div>

                  {/* Format & Resolution */}
                  <div className="space-y-4">
                    <h4 className="font-medium text-mountain-800">Output Format</h4>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-mountain-700 mb-2">
                          Format
                        </label>
                        <select
                          value={settings.format}
                          onChange={(e) => updateSettings('format', e.target.value)}
                          className="w-full px-3 py-2 border border-mountain-300 rounded-lg focus:ring-2 focus:ring-golden-500 focus:border-golden-500"
                        >
                          <option value="mp4">MP4 (Recommended)</option>
                          <option value="webm">WebM</option>
                          <option value="mov">MOV (Apple)</option>
                        </select>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-mountain-700 mb-2">
                          Resolution
                        </label>
                        <select
                          value={settings.resolution}
                          onChange={(e) => updateSettings('resolution', e.target.value)}
                          className="w-full px-3 py-2 border border-mountain-300 rounded-lg focus:ring-2 focus:ring-golden-500 focus:border-golden-500"
                        >
                          <option value="4K">4K (3840×2160)</option>
                          <option value="1080p">1080p (1920×1080)</option>
                          <option value="720p">720p (1280×720)</option>
                        </select>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-mountain-700 mb-2">
                          Frame Rate
                        </label>
                        <select
                          value={settings.frameRate}
                          onChange={(e) => updateSettings('frameRate', parseInt(e.target.value))}
                          className="w-full px-3 py-2 border border-mountain-300 rounded-lg focus:ring-2 focus:ring-golden-500 focus:border-golden-500"
                        >
                          <option value={24}>24 FPS (Cinematic)</option>
                          <option value={30}>30 FPS (Standard)</option>
                          <option value={60}>60 FPS (Smooth)</option>
                        </select>
                      </div>
                    </div>
                  </div>

                  {/* Quality Settings */}
                  <div className="space-y-4">
                    <h4 className="font-medium text-mountain-800">Quality Settings</h4>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {QUALITY_PRESETS.map((preset) => (
                        <div
                          key={preset.id}
                          className={cn(
                            'p-4 border-2 rounded-lg cursor-pointer transition-all',
                            settings.quality === preset.id
                              ? 'border-golden-500 bg-golden-50'
                              : 'border-mountain-200 hover:border-mountain-300'
                          )}
                          onClick={() => updateSettings('quality', preset.id)}
                        >
                          <div className="flex items-center justify-between mb-2">
                            <h5 className="font-medium text-mountain-900">{preset.name}</h5>
                            <span className="text-sm text-mountain-500">{preset.bitrate}</span>
                          </div>
                          <p className="text-sm text-mountain-600 mb-2">{preset.description}</p>
                          <div className="text-xs text-mountain-500">File size: {preset.fileSize}</div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Speed Settings */}
                  <div className="space-y-4">
                    <h4 className="font-medium text-mountain-800">Playback Speed</h4>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      {SPEED_PRESETS.map((preset) => (
                        <div
                          key={preset.value}
                          className={cn(
                            'p-3 border-2 rounded-lg cursor-pointer transition-all text-center',
                            settings.speedMultiplier === preset.value
                              ? 'border-golden-500 bg-golden-50'
                              : 'border-mountain-200 hover:border-mountain-300'
                          )}
                          onClick={() => updateSettings('speedMultiplier', preset.value)}
                        >
                          <div className="font-medium text-mountain-900">{preset.label}</div>
                          <div className="text-xs text-mountain-500 mt-1">{preset.description}</div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Advanced Options */}
                  <div className="space-y-4">
                    <h4 className="font-medium text-mountain-800">Advanced Options</h4>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div className="space-y-4">
                        <div className="flex items-center justify-between">
                          <div>
                            <label className="font-medium text-mountain-700">Image Stabilization</label>
                            <p className="text-sm text-mountain-600">Reduce camera shake and vibration</p>
                          </div>
                          <input
                            type="checkbox"
                            checked={settings.stabilization}
                            onChange={(e) => updateSettings('stabilization', e.target.checked)}
                            className="w-5 h-5 text-golden-600 focus:ring-golden-500 border-mountain-300 rounded"
                          />
                        </div>

                        <div className="flex items-center justify-between">
                          <div>
                            <label className="font-medium text-mountain-700">Skylapse Watermark</label>
                            <p className="text-sm text-mountain-600">Add branding to generated videos</p>
                          </div>
                          <input
                            type="checkbox"
                            checked={settings.watermark}
                            onChange={(e) => updateSettings('watermark', e.target.checked)}
                            className="w-5 h-5 text-golden-600 focus:ring-golden-500 border-mountain-300 rounded"
                          />
                        </div>
                      </div>

                      <div className="space-y-4">
                        <div>
                          <label className="block text-sm font-medium text-mountain-700 mb-2">
                            Color Grading
                          </label>
                          <select
                            value={settings.colorGrading}
                            onChange={(e) => updateSettings('colorGrading', e.target.value)}
                            className="w-full px-3 py-2 border border-mountain-300 rounded-lg focus:ring-2 focus:ring-golden-500 focus:border-golden-500"
                          >
                            <option value="none">No Grading</option>
                            <option value="cinematic">Cinematic</option>
                            <option value="vibrant">Vibrant</option>
                            <option value="natural">Natural</option>
                          </select>
                        </div>

                        <div>
                          <label className="block text-sm font-medium text-mountain-700 mb-2">
                            Aspect Ratio
                          </label>
                          <select
                            value={settings.cropToAspectRatio}
                            onChange={(e) => updateSettings('cropToAspectRatio', e.target.value)}
                            className="w-full px-3 py-2 border border-mountain-300 rounded-lg focus:ring-2 focus:ring-golden-500 focus:border-golden-500"
                          >
                            <option value="original">Original</option>
                            <option value="16:9">16:9 (Widescreen)</option>
                            <option value="4:3">4:3 (Standard)</option>
                            <option value="21:9">21:9 (Ultrawide)</option>
                          </select>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Jobs Tab */}
              {activeTab === 'jobs' && (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-lg font-semibold text-mountain-900 mb-4">
                      Video Generation Jobs
                    </h3>
                    <p className="text-mountain-600 mb-6">
                      Monitor progress and download completed videos
                    </p>
                  </div>

                  <div className="space-y-4">
                    {jobs.length === 0 ? (
                      <div className="text-center py-8">
                        <div className="text-4xl mb-4">🎬</div>
                        <p className="text-mountain-600">No video generation jobs yet</p>
                        <p className="text-mountain-500 text-sm">Generate your first video from a sequence</p>
                      </div>
                    ) : (
                      jobs.map((job) => {
                        const sequence = sequences.find(s => s.id === job.sequenceId);
                        return (
                          <Card key={job.id}>
                            <div className="p-4">
                              <div className="flex items-start justify-between">
                                <div className="flex-1">
                                  <h4 className="font-medium text-mountain-900">
                                    {sequence?.title || 'Unknown Sequence'}
                                  </h4>
                                  <p className="text-sm text-mountain-600 mt-1">
                                    {job.settings.resolution} • {job.settings.frameRate} FPS • {job.settings.format.toUpperCase()}
                                  </p>

                                  <div className="flex items-center space-x-4 mt-3">
                                    <span className={cn('font-medium', getStatusColor(job.status))}>
                                      {job.status.charAt(0).toUpperCase() + job.status.slice(1)}
                                    </span>
                                    <span className="text-sm text-mountain-500">
                                      Started: {new Date(job.startedAt).toLocaleString()}
                                    </span>
                                  </div>

                                  {job.status === 'processing' && (
                                    <div className="mt-3">
                                      <div className="flex items-center justify-between text-sm mb-1">
                                        <span className="text-mountain-600">Progress</span>
                                        <span className="font-medium">{job.progress}%</span>
                                      </div>
                                      <div className="w-full bg-mountain-200 rounded-full h-2">
                                        <div
                                          className="bg-golden-500 h-2 rounded-full transition-all duration-300"
                                          style={{ width: `${job.progress}%` }}
                                        />
                                      </div>
                                    </div>
                                  )}

                                  {job.status === 'completed' && job.outputUrl && (
                                    <div className="mt-3 flex items-center space-x-4">
                                      <button className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm font-medium transition-colors">
                                        Download Video
                                      </button>
                                      <span className="text-sm text-mountain-600">
                                        {job.fileSize && formatFileSize(job.fileSize)} • {job.duration && formatDuration(job.duration)}
                                      </span>
                                    </div>
                                  )}

                                  {job.status === 'failed' && job.error && (
                                    <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg">
                                      <p className="text-sm text-red-700">{job.error}</p>
                                    </div>
                                  )}
                                </div>

                                <div className="ml-4">
                                  {job.status === 'processing' && (
                                    <div className="animate-spin w-6 h-6 border-2 border-golden-500 border-t-transparent rounded-full"></div>
                                  )}
                                  {job.status === 'completed' && (
                                    <div className="w-6 h-6 bg-green-500 rounded-full flex items-center justify-center">
                                      <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 20 20">
                                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                                      </svg>
                                    </div>
                                  )}
                                  {job.status === 'failed' && (
                                    <div className="w-6 h-6 bg-red-500 rounded-full flex items-center justify-center">
                                      <span className="text-white text-sm">!</span>
                                    </div>
                                  )}
                                </div>
                              </div>
                            </div>
                          </Card>
                        );
                      })
                    )}
                  </div>
                </div>
              )}
            </div>
          </Card>
        </div>

        {/* Sidebar - Selected Sequence & Estimated Output */}
        <div className="space-y-6">
          {selectedSequence && (
            <Card>
              <div className="p-6">
                <h3 className="text-lg font-semibold text-mountain-900 mb-4">
                  Selected Sequence
                </h3>

                <div className="space-y-4">
                  <div className="w-full h-32 bg-mountain-100 rounded-lg flex items-center justify-center">
                    <span className="text-4xl">🏔️</span>
                  </div>

                  <div>
                    <h4 className="font-medium text-mountain-900">{selectedSequence.title}</h4>
                    <p className="text-sm text-mountain-600">{selectedSequence.metadata.location.name}</p>
                  </div>

                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-mountain-600">Frames</span>
                      <span className="font-medium">{selectedSequence.frameCount}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-mountain-600">Duration</span>
                      <span className="font-medium">{selectedSequence.duration}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-mountain-600">Source Size</span>
                      <span className="font-medium">{formatFileSize(selectedSequence.fileSize)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-mountain-600">Quality</span>
                      <span className={cn(
                        'px-2 py-1 text-xs font-medium rounded-full',
                        getQualityBadgeColor(selectedSequence.quality)
                      )}>
                        {selectedSequence.quality}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </Card>
          )}

          <Card>
            <div className="p-6">
              <h3 className="text-lg font-semibold text-mountain-900 mb-4">
                Estimated Output
              </h3>

              <div className="space-y-3 text-sm">
                <div className="flex justify-between">
                  <span className="text-mountain-600">Format</span>
                  <span className="font-medium">{settings.format.toUpperCase()}</span>
                </div>

                <div className="flex justify-between">
                  <span className="text-mountain-600">Resolution</span>
                  <span className="font-medium">{settings.resolution}</span>
                </div>

                <div className="flex justify-between">
                  <span className="text-mountain-600">Frame Rate</span>
                  <span className="font-medium">{settings.frameRate} FPS</span>
                </div>

                <div className="flex justify-between">
                  <span className="text-mountain-600">Speed</span>
                  <span className="font-medium">{settings.speedMultiplier}x</span>
                </div>

                <div className="flex justify-between">
                  <span className="text-mountain-600">Quality</span>
                  <span className="font-medium capitalize">{settings.quality}</span>
                </div>

                {selectedSequence && (
                  <>
                    <hr className="border-mountain-200" />
                    <div className="flex justify-between">
                      <span className="text-mountain-600">Estimated Duration</span>
                      <span className="font-medium">
                        {Math.ceil(selectedSequence.frameCount / settings.speedMultiplier / settings.frameRate / 60)} min
                      </span>
                    </div>

                    <div className="flex justify-between">
                      <span className="text-mountain-600">Processing Time</span>
                      <span className="font-medium">~15-45 min</span>
                    </div>
                  </>
                )}
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default VideoGenerationInterface;
