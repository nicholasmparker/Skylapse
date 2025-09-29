/**
 * Capture Settings Interface - Professional camera control for mountain timelapse
 * UI-007: Capture Settings Interface
 */

import React, { useState, useEffect } from 'react';
import { apiClient } from '@/api/client';
import { Card } from '@/design-system/components';
import { CameraPreview } from '../camera/CameraPreview';
import { cn } from '@/utils';

interface CaptureSettings {
  manual: {
    iso: number;
    exposureTime: number; // in seconds
    exposureCompensation: number;
    hdrBracketing: boolean;
    bracketStops: number;
    focusDistance: number | null;
    autofocus: boolean;
    whiteBalance: 'auto' | 'daylight' | 'cloudy' | 'tungsten' | 'fluorescent';
    quality: number; // 1-100
    format: 'JPEG' | 'RAW' | 'RAW+JPEG';
    rotationDegrees: number; // 0, 90, 180, 270
  };
  scheduling: {
    enabled: boolean;
    intervalSeconds: number;
    durationMinutes: number;
    goldenHourMode: boolean;
    blueHourMode: boolean;
    nightMode: boolean;
  };
  intelligent: {
    enabled: boolean;
    adaptiveInterval: boolean;
    weatherAdaptation: boolean;
    lightConditionOptimization: boolean;
    autoHDR: boolean;
  };
}

interface CapturePreset {
  id: string;
  name: string;
  description: string;
  icon: string;
  settings: CaptureSettings;
  conditions: string[];
}

const DEFAULT_SETTINGS: CaptureSettings = {
  manual: {
    iso: 100,
    exposureTime: 0.004, // 1/250s
    exposureCompensation: 0,
    hdrBracketing: false,
    bracketStops: 3,
    focusDistance: null,
    autofocus: true,
    whiteBalance: 'auto',
    quality: 95,
    format: 'JPEG',
    rotationDegrees: 180, // Fix upside-down mount by default
  },
  scheduling: {
    enabled: false,
    intervalSeconds: 300, // 5 minutes
    durationMinutes: 60,
    goldenHourMode: false,
    blueHourMode: false,
    nightMode: false,
  },
  intelligent: {
    enabled: true,
    adaptiveInterval: true,
    weatherAdaptation: true,
    lightConditionOptimization: true,
    autoHDR: false,
  },
};

const CAPTURE_PRESETS: CapturePreset[] = [
  {
    id: 'golden-hour',
    name: 'Golden Hour',
    description: 'Optimized for sunrise and sunset captures',
    icon: '🌅',
    conditions: ['Low light', 'Warm tones', 'High contrast'],
    settings: {
      ...DEFAULT_SETTINGS,
      manual: {
        ...DEFAULT_SETTINGS.manual,
        iso: 100,
        exposureTime: 0.008, // 1/125s
        hdrBracketing: true,
        bracketStops: 5,
        quality: 100,
        format: 'RAW+JPEG',
      },
      scheduling: {
        ...DEFAULT_SETTINGS.scheduling,
        enabled: true,
        intervalSeconds: 120, // 2 minutes
        goldenHourMode: true,
      },
      intelligent: {
        ...DEFAULT_SETTINGS.intelligent,
        autoHDR: true,
        lightConditionOptimization: true,
      },
    },
  },
  {
    id: 'storm-clouds',
    name: 'Storm Clouds',
    description: 'Dramatic weather and cloud movement',
    icon: '⛈️',
    conditions: ['Dynamic weather', 'Fast movement', 'High contrast'],
    settings: {
      ...DEFAULT_SETTINGS,
      manual: {
        ...DEFAULT_SETTINGS.manual,
        iso: 200,
        exposureTime: 0.002, // 1/500s
        exposureCompensation: -0.3,
        hdrBracketing: true,
        bracketStops: 3,
      },
      scheduling: {
        ...DEFAULT_SETTINGS.scheduling,
        enabled: true,
        intervalSeconds: 30, // 30 seconds for fast clouds
      },
      intelligent: {
        ...DEFAULT_SETTINGS.intelligent,
        weatherAdaptation: true,
        adaptiveInterval: true,
      },
    },
  },
  {
    id: 'night-sky',
    name: 'Night Sky',
    description: 'Star trails and night photography',
    icon: '🌌',
    conditions: ['Very low light', 'Long exposure', 'Star movement'],
    settings: {
      ...DEFAULT_SETTINGS,
      manual: {
        ...DEFAULT_SETTINGS.manual,
        iso: 1600,
        exposureTime: 30, // 30 seconds
        exposureCompensation: 0,
        hdrBracketing: false,
        autofocus: false,
        focusDistance: Infinity,
        quality: 100,
        format: 'RAW',
      },
      scheduling: {
        ...DEFAULT_SETTINGS.scheduling,
        enabled: true,
        intervalSeconds: 60, // 1 minute
        nightMode: true,
      },
      intelligent: {
        ...DEFAULT_SETTINGS.intelligent,
        autoHDR: false,
        lightConditionOptimization: true,
      },
    },
  },
  {
    id: 'blue-hour',
    name: 'Blue Hour',
    description: 'Twilight photography with balanced exposure',
    icon: '🌆',
    conditions: ['Twilight', 'Balanced light', 'Urban/landscape'],
    settings: {
      ...DEFAULT_SETTINGS,
      manual: {
        ...DEFAULT_SETTINGS.manual,
        iso: 400,
        exposureTime: 0.033, // 1/30s
        exposureCompensation: -0.7,
        hdrBracketing: true,
        bracketStops: 3,
      },
      scheduling: {
        ...DEFAULT_SETTINGS.scheduling,
        enabled: true,
        intervalSeconds: 180, // 3 minutes
        blueHourMode: true,
      },
    },
  },
  {
    id: 'landscape-daylight',
    name: 'Landscape Daylight',
    description: 'General landscape photography in good light',
    icon: '🏔️',
    conditions: ['Good light', 'Landscape', 'General purpose'],
    settings: {
      ...DEFAULT_SETTINGS,
      manual: {
        ...DEFAULT_SETTINGS.manual,
        iso: 100,
        exposureTime: 0.008, // 1/125s
        exposureCompensation: -0.3,
        quality: 95,
      },
      scheduling: {
        ...DEFAULT_SETTINGS.scheduling,
        enabled: true,
        intervalSeconds: 600, // 10 minutes
      },
    },
  },
];

export const CaptureSettingsInterface: React.FC = () => {
  const [settings, setSettings] = useState<CaptureSettings>(DEFAULT_SETTINGS);
  const [activePreset, setActivePreset] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'manual' | 'presets' | 'intelligent'>('presets');

  // Load current settings on mount
  useEffect(() => {
    loadCurrentSettings();
  }, []);

  const loadCurrentSettings = async () => {
    try {
      setIsLoading(true);
      setError(null);

      // Use capture service directly instead of processing service
      const response = await fetch('http://helios.local:8080/api/settings');
      const data = await response.json();
      console.log('🔍 Raw API response:', data);

      if (response.ok && data) {
        // Convert API format to UI format
        const apiData = data;
        console.log('🔍 API data rotation_degrees:', apiData.rotation_degrees);
        const loadedSettings: CaptureSettings = {
          ...DEFAULT_SETTINGS,
          manual: {
            ...DEFAULT_SETTINGS.manual,
            iso: apiData.iso || DEFAULT_SETTINGS.manual.iso,
            exposureTime: apiData.exposure_time_us ? apiData.exposure_time_us / 1000000 : DEFAULT_SETTINGS.manual.exposureTime,
            exposureCompensation: apiData.exposure_compensation || DEFAULT_SETTINGS.manual.exposureCompensation,
            hdrBracketing: Array.isArray(apiData.hdr_bracket_stops) && apiData.hdr_bracket_stops.length > 1,
            bracketStops: Array.isArray(apiData.hdr_bracket_stops) ? apiData.hdr_bracket_stops.length : DEFAULT_SETTINGS.manual.bracketStops,
            focusDistance: apiData.focus_distance_mm || DEFAULT_SETTINGS.manual.focusDistance,
            autofocus: apiData.autofocus_enabled ?? DEFAULT_SETTINGS.manual.autofocus,
            whiteBalance: apiData.white_balance_mode || DEFAULT_SETTINGS.manual.whiteBalance,
            quality: apiData.quality || DEFAULT_SETTINGS.manual.quality,
            format: apiData.format || DEFAULT_SETTINGS.manual.format,
            rotationDegrees: apiData.rotation_degrees !== undefined ? apiData.rotation_degrees : DEFAULT_SETTINGS.manual.rotationDegrees,
          },
        };

        console.log('🔍 Final UI rotationDegrees:', loadedSettings.manual.rotationDegrees);
        setSettings(loadedSettings);
        console.log('🔍 Settings state updated to:', loadedSettings.manual.rotationDegrees);
        console.log('Settings loaded from API:', loadedSettings);
      }

    } catch (err) {
      console.warn('Could not load current settings, using defaults:', err);
      // Keep using defaults if API fails
    } finally {
      setIsLoading(false);
    }
  };

  const applyPreset = (preset: CapturePreset) => {
    setSettings(preset.settings);
    setActivePreset(preset.id);
    setError(null);
  };

  const saveSettings = async () => {
    try {
      setIsSaving(true);
      setError(null);

      // Convert UI settings to API format
      const apiSettings = {
        iso: settings.manual.iso,
        exposure_time_us: Math.round(settings.manual.exposureTime * 1000000), // Convert to microseconds
        exposure_compensation: settings.manual.exposureCompensation,
        hdr_bracket_stops: settings.manual.hdrBracketing ?
          Array.from({length: settings.manual.bracketStops}, (_, i) => i - Math.floor(settings.manual.bracketStops / 2)) : [],
        focus_distance_mm: settings.manual.focusDistance,
        autofocus_enabled: settings.manual.autofocus,
        white_balance_mode: settings.manual.whiteBalance,
        quality: settings.manual.quality,
        format: settings.manual.format,
        rotation_degrees: settings.manual.rotationDegrees,
      };

      const response = await apiClient.capture.updateCameraSettings(apiSettings);

      if (response.data.success) {
        console.log('Settings saved successfully:', response.data.data);
        // Critical fix: Immediately reload settings from backend to ensure UI shows actual values
        try {
          await loadCurrentSettings();
        } catch (loadError) {
          console.warn('Failed to reload settings after save:', loadError);
          // Don't throw error here - save was successful, just warn about reload failure
        }
      } else {
        throw new Error(response.data.error?.message || 'Failed to save settings');
      }

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save settings');
    } finally {
      setIsSaving(false);
    }
  };

  const testCapture = async () => {
    try {
      setError(null);

      // Trigger a test capture with current settings
      const response = await apiClient.capture.manualCapture();

      if (response.data) {
        console.log('Test capture successful:', response.data);
      }

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Test capture failed');
    }
  };

  const updateManualSettings = (field: string, value: any) => {
    setSettings(prev => ({
      ...prev,
      manual: {
        ...prev.manual,
        [field]: value,
      },
    }));
    setActivePreset(null); // Clear preset when manually adjusting
  };

  const updateSchedulingSettings = (field: string, value: any) => {
    setSettings(prev => ({
      ...prev,
      scheduling: {
        ...prev.scheduling,
        [field]: value,
      },
    }));
  };

  const updateIntelligentSettings = (field: string, value: any) => {
    setSettings(prev => ({
      ...prev,
      intelligent: {
        ...prev.intelligent,
        [field]: value,
      },
    }));
  };

  const formatExposureTime = (seconds: number): string => {
    if (seconds >= 1) {
      return `${seconds}s`;
    } else {
      return `1/${Math.round(1 / seconds)}s`;
    }
  };

  return (
    <div className="min-h-screen bg-mountain-50 p-6">
      {/* Header */}
      <div className="max-w-7xl mx-auto mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-mountain-900">
              📷 Capture Settings
            </h1>
            <p className="text-mountain-600 mt-2">
              Professional camera controls for mountain timelapse photography
            </p>
          </div>

          <div className="flex items-center space-x-4">
            <button
              onClick={testCapture}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
            >
              Test Capture
            </button>
            <button
              onClick={saveSettings}
              disabled={isSaving}
              className={cn(
                'px-6 py-2 rounded-lg font-medium transition-colors',
                isSaving
                  ? 'bg-mountain-400 text-mountain-200 cursor-not-allowed'
                  : 'bg-golden-600 hover:bg-golden-700 text-white'
              )}
            >
              {isSaving ? 'Saving...' : 'Save Settings'}
            </button>
          </div>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="max-w-7xl mx-auto mb-6">
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="flex items-center">
              <span className="text-red-500 text-lg mr-2">⚠️</span>
              <span className="text-red-700">{error}</span>
            </div>
          </div>
        </div>
      )}

      <div className="max-w-7xl mx-auto">
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">

          {/* Settings Panel */}
          <div className="xl:col-span-2 space-y-6">

            {/* Tab Navigation */}
            <Card>
              <div className="border-b border-mountain-200">
                <nav className="flex space-x-8 px-6 py-4">
                  {[
                    { id: 'presets', label: 'Presets', icon: '⚡' },
                    { id: 'manual', label: 'Manual Settings', icon: '⚙️' },
                    { id: 'intelligent', label: 'Intelligent Mode', icon: '🧠' },
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
                {/* Presets Tab */}
                {activeTab === 'presets' && (
                  <div className="space-y-6">
                    <div>
                      <h3 className="text-lg font-semibold text-mountain-900 mb-4">
                        Professional Capture Presets
                      </h3>
                      <p className="text-mountain-600 mb-6">
                        Optimized settings for common mountain photography scenarios
                      </p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {CAPTURE_PRESETS.map((preset) => (
                        <div
                          key={preset.id}
                          className={cn(
                            'p-4 border-2 rounded-lg cursor-pointer transition-all hover:shadow-md',
                            activePreset === preset.id
                              ? 'border-golden-500 bg-golden-50'
                              : 'border-mountain-200 hover:border-mountain-300'
                          )}
                          onClick={() => applyPreset(preset)}
                        >
                          <div className="flex items-start space-x-3">
                            <div className="text-2xl">{preset.icon}</div>
                            <div className="flex-1">
                              <h4 className="font-semibold text-mountain-900">
                                {preset.name}
                              </h4>
                              <p className="text-sm text-mountain-600 mt-1">
                                {preset.description}
                              </p>
                              <div className="flex flex-wrap gap-1 mt-2">
                                {preset.conditions.map((condition) => (
                                  <span
                                    key={condition}
                                    className="px-2 py-1 bg-mountain-100 text-mountain-700 text-xs rounded"
                                  >
                                    {condition}
                                  </span>
                                ))}
                              </div>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Manual Settings Tab */}
                {activeTab === 'manual' && (
                  <div className="space-y-8">
                    <div>
                      <h3 className="text-lg font-semibold text-mountain-900 mb-4">
                        Manual Camera Controls
                      </h3>
                      <p className="text-mountain-600 mb-6">
                        Precise control over all camera parameters
                      </p>
                    </div>

                    {/* Exposure Settings */}
                    <div className="space-y-4">
                      <h4 className="font-medium text-mountain-800">Exposure</h4>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                          <label className="block text-sm font-medium text-mountain-700 mb-2">
                            ISO
                          </label>
                          <select
                            value={settings.manual.iso}
                            onChange={(e) => updateManualSettings('iso', parseInt(e.target.value))}
                            className="w-full px-3 py-2 border border-mountain-300 rounded-lg focus:ring-2 focus:ring-golden-500 focus:border-golden-500"
                          >
                            {[100, 200, 400, 800, 1600, 3200, 6400].map((iso) => (
                              <option key={iso} value={iso}>ISO {iso}</option>
                            ))}
                          </select>
                        </div>

                        <div>
                          <label className="block text-sm font-medium text-mountain-700 mb-2">
                            Shutter Speed
                          </label>
                          <select
                            value={settings.manual.exposureTime}
                            onChange={(e) => updateManualSettings('exposureTime', parseFloat(e.target.value))}
                            className="w-full px-3 py-2 border border-mountain-300 rounded-lg focus:ring-2 focus:ring-golden-500 focus:border-golden-500"
                          >
                            {[30, 15, 8, 4, 2, 1, 0.5, 0.25, 0.125, 0.033, 0.008, 0.004, 0.002, 0.001].map((time) => (
                              <option key={time} value={time}>{formatExposureTime(time)}</option>
                            ))}
                          </select>
                        </div>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-mountain-700 mb-2">
                          Exposure Compensation: {settings.manual.exposureCompensation > 0 ? '+' : ''}{settings.manual.exposureCompensation} EV
                        </label>
                        <input
                          type="range"
                          min="-2"
                          max="2"
                          step="0.3"
                          value={settings.manual.exposureCompensation}
                          onChange={(e) => updateManualSettings('exposureCompensation', parseFloat(e.target.value))}
                          className="w-full"
                        />
                      </div>
                    </div>

                    {/* HDR Settings */}
                    <div className="space-y-4">
                      <h4 className="font-medium text-mountain-800">HDR Bracketing</h4>

                      <div className="flex items-center space-x-3">
                        <input
                          type="checkbox"
                          id="hdr-enabled"
                          checked={settings.manual.hdrBracketing}
                          onChange={(e) => updateManualSettings('hdrBracketing', e.target.checked)}
                          className="w-4 h-4 text-golden-600 focus:ring-golden-500 border-mountain-300 rounded"
                        />
                        <label htmlFor="hdr-enabled" className="text-sm font-medium text-mountain-700">
                          Enable HDR Bracketing
                        </label>
                      </div>

                      {settings.manual.hdrBracketing && (
                        <div>
                          <label className="block text-sm font-medium text-mountain-700 mb-2">
                            Bracket Stops: {settings.manual.bracketStops}
                          </label>
                          <input
                            type="range"
                            min="3"
                            max="7"
                            step="2"
                            value={settings.manual.bracketStops}
                            onChange={(e) => updateManualSettings('bracketStops', parseInt(e.target.value))}
                            className="w-full"
                          />
                          <div className="flex justify-between text-xs text-mountain-500 mt-1">
                            <span>3 stops</span>
                            <span>5 stops</span>
                            <span>7 stops</span>
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Focus & White Balance */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div className="space-y-4">
                        <h4 className="font-medium text-mountain-800">Focus</h4>

                        <div className="flex items-center space-x-3">
                          <input
                            type="checkbox"
                            id="autofocus"
                            checked={settings.manual.autofocus}
                            onChange={(e) => updateManualSettings('autofocus', e.target.checked)}
                            className="w-4 h-4 text-golden-600 focus:ring-golden-500 border-mountain-300 rounded"
                          />
                          <label htmlFor="autofocus" className="text-sm font-medium text-mountain-700">
                            Autofocus
                          </label>
                        </div>

                        {!settings.manual.autofocus && (
                          <div>
                            <label className="block text-sm font-medium text-mountain-700 mb-2">
                              Focus Distance (mm)
                            </label>
                            <input
                              type="number"
                              value={settings.manual.focusDistance || ''}
                              onChange={(e) => updateManualSettings('focusDistance', e.target.value ? parseFloat(e.target.value) : null)}
                              placeholder="Infinity"
                              className="w-full px-3 py-2 border border-mountain-300 rounded-lg focus:ring-2 focus:ring-golden-500 focus:border-golden-500"
                            />
                          </div>
                        )}
                      </div>

                      <div className="space-y-4">
                        <h4 className="font-medium text-mountain-800">White Balance</h4>

                        <select
                          value={settings.manual.whiteBalance}
                          onChange={(e) => updateManualSettings('whiteBalance', e.target.value)}
                          className="w-full px-3 py-2 border border-mountain-300 rounded-lg focus:ring-2 focus:ring-golden-500 focus:border-golden-500"
                        >
                          <option value="auto">Auto</option>
                          <option value="daylight">Daylight</option>
                          <option value="cloudy">Cloudy</option>
                          <option value="tungsten">Tungsten</option>
                          <option value="fluorescent">Fluorescent</option>
                        </select>
                      </div>
                    </div>

                    {/* File Format & Quality */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div>
                        <label className="block text-sm font-medium text-mountain-700 mb-2">
                          File Format
                        </label>
                        <select
                          value={settings.manual.format}
                          onChange={(e) => updateManualSettings('format', e.target.value)}
                          className="w-full px-3 py-2 border border-mountain-300 rounded-lg focus:ring-2 focus:ring-golden-500 focus:border-golden-500"
                        >
                          <option value="JPEG">JPEG</option>
                          <option value="RAW">RAW</option>
                          <option value="RAW+JPEG">RAW + JPEG</option>
                        </select>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-mountain-700 mb-2">
                          JPEG Quality: {settings.manual.quality}%
                        </label>
                        <input
                          type="range"
                          min="50"
                          max="100"
                          step="5"
                          value={settings.manual.quality}
                          onChange={(e) => updateManualSettings('quality', parseInt(e.target.value))}
                          className="w-full"
                        />
                      </div>
                    </div>

                    {/* Image Orientation */}
                    <div className="space-y-4">
                      <h4 className="font-medium text-mountain-800">Image Orientation</h4>

                      <div>
                        <label className="block text-sm font-medium text-mountain-700 mb-2">
                          Rotation
                        </label>
                        <select
                          value={settings.manual.rotationDegrees}
                          onChange={(e) => updateManualSettings('rotationDegrees', parseInt(e.target.value))}
                          className="w-full px-3 py-2 border border-mountain-300 rounded-lg focus:ring-2 focus:ring-golden-500 focus:border-golden-500"
                        >
                          <option value={0}>0° (Normal)</option>
                          <option value={90}>90° (Portrait Left)</option>
                          <option value={180}>180° (Upside Down)</option>
                          <option value={270}>270° (Portrait Right)</option>
                        </select>
                        <p className="text-xs text-mountain-500 mt-1">
                          Adjust for camera mounting orientation
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Intelligent Mode Tab */}
                {activeTab === 'intelligent' && (
                  <div className="space-y-6">
                    <div>
                      <h3 className="text-lg font-semibold text-mountain-900 mb-4">
                        Intelligent Capture Features
                      </h3>
                      <p className="text-mountain-600 mb-6">
                        AI-powered optimization for changing conditions
                      </p>
                    </div>

                    <div className="space-y-4">
                      <div className="flex items-center justify-between p-4 bg-mountain-50 rounded-lg">
                        <div>
                          <h4 className="font-medium text-mountain-800">Enable Intelligent Mode</h4>
                          <p className="text-sm text-mountain-600">Automatically optimize settings based on conditions</p>
                        </div>
                        <input
                          type="checkbox"
                          checked={settings.intelligent.enabled}
                          onChange={(e) => updateIntelligentSettings('enabled', e.target.checked)}
                          className="w-5 h-5 text-golden-600 focus:ring-golden-500 border-mountain-300 rounded"
                        />
                      </div>

                      {settings.intelligent.enabled && (
                        <div className="space-y-4 pl-4 border-l-2 border-golden-200">
                          <div className="flex items-center justify-between">
                            <div>
                              <h5 className="font-medium text-mountain-700">Adaptive Interval</h5>
                              <p className="text-sm text-mountain-600">Adjust capture frequency based on scene change</p>
                            </div>
                            <input
                              type="checkbox"
                              checked={settings.intelligent.adaptiveInterval}
                              onChange={(e) => updateIntelligentSettings('adaptiveInterval', e.target.checked)}
                              className="w-4 h-4 text-golden-600 focus:ring-golden-500 border-mountain-300 rounded"
                            />
                          </div>

                          <div className="flex items-center justify-between">
                            <div>
                              <h5 className="font-medium text-mountain-700">Weather Adaptation</h5>
                              <p className="text-sm text-mountain-600">Adjust settings for weather conditions</p>
                            </div>
                            <input
                              type="checkbox"
                              checked={settings.intelligent.weatherAdaptation}
                              onChange={(e) => updateIntelligentSettings('weatherAdaptation', e.target.checked)}
                              className="w-4 h-4 text-golden-600 focus:ring-golden-500 border-mountain-300 rounded"
                            />
                          </div>

                          <div className="flex items-center justify-between">
                            <div>
                              <h5 className="font-medium text-mountain-700">Light Condition Optimization</h5>
                              <p className="text-sm text-mountain-600">Optimize exposure for changing light</p>
                            </div>
                            <input
                              type="checkbox"
                              checked={settings.intelligent.lightConditionOptimization}
                              onChange={(e) => updateIntelligentSettings('lightConditionOptimization', e.target.checked)}
                              className="w-4 h-4 text-golden-600 focus:ring-golden-500 border-mountain-300 rounded"
                            />
                          </div>

                          <div className="flex items-center justify-between">
                            <div>
                              <h5 className="font-medium text-mountain-700">Auto HDR</h5>
                              <p className="text-sm text-mountain-600">Enable HDR automatically for high contrast scenes</p>
                            </div>
                            <input
                              type="checkbox"
                              checked={settings.intelligent.autoHDR}
                              onChange={(e) => updateIntelligentSettings('autoHDR', e.target.checked)}
                              className="w-4 h-4 text-golden-600 focus:ring-golden-500 border-mountain-300 rounded"
                            />
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </Card>

            {/* Scheduling Settings */}
            <Card>
              <div className="p-6">
                <h3 className="text-lg font-semibold text-mountain-900 mb-4">
                  📅 Capture Scheduling
                </h3>

                <div className="space-y-4">
                  <div className="flex items-center space-x-3">
                    <input
                      type="checkbox"
                      id="scheduling-enabled"
                      checked={settings.scheduling.enabled}
                      onChange={(e) => updateSchedulingSettings('enabled', e.target.checked)}
                      className="w-4 h-4 text-golden-600 focus:ring-golden-500 border-mountain-300 rounded"
                    />
                    <label htmlFor="scheduling-enabled" className="text-sm font-medium text-mountain-700">
                      Enable Automatic Scheduling
                    </label>
                  </div>

                  {settings.scheduling.enabled && (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4 border-t border-mountain-200">
                      <div>
                        <label className="block text-sm font-medium text-mountain-700 mb-2">
                          Interval (seconds)
                        </label>
                        <select
                          value={settings.scheduling.intervalSeconds}
                          onChange={(e) => updateSchedulingSettings('intervalSeconds', parseInt(e.target.value))}
                          className="w-full px-3 py-2 border border-mountain-300 rounded-lg focus:ring-2 focus:ring-golden-500 focus:border-golden-500"
                        >
                          <option value={30}>30 seconds</option>
                          <option value={60}>1 minute</option>
                          <option value={120}>2 minutes</option>
                          <option value={300}>5 minutes</option>
                          <option value={600}>10 minutes</option>
                          <option value={1800}>30 minutes</option>
                          <option value={3600}>1 hour</option>
                        </select>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-mountain-700 mb-2">
                          Duration (minutes)
                        </label>
                        <select
                          value={settings.scheduling.durationMinutes}
                          onChange={(e) => updateSchedulingSettings('durationMinutes', parseInt(e.target.value))}
                          className="w-full px-3 py-2 border border-mountain-300 rounded-lg focus:ring-2 focus:ring-golden-500 focus:border-golden-500"
                        >
                          <option value={30}>30 minutes</option>
                          <option value={60}>1 hour</option>
                          <option value={120}>2 hours</option>
                          <option value={180}>3 hours</option>
                          <option value={360}>6 hours</option>
                          <option value={720}>12 hours</option>
                          <option value={1440}>24 hours</option>
                        </select>
                      </div>

                      <div className="md:col-span-2">
                        <h4 className="font-medium text-mountain-700 mb-3">Time-based Modes</h4>
                        <div className="flex flex-wrap gap-4">
                          <label className="flex items-center space-x-2">
                            <input
                              type="checkbox"
                              checked={settings.scheduling.goldenHourMode}
                              onChange={(e) => updateSchedulingSettings('goldenHourMode', e.target.checked)}
                              className="w-4 h-4 text-golden-600 focus:ring-golden-500 border-mountain-300 rounded"
                            />
                            <span className="text-sm text-mountain-700">🌅 Golden Hour</span>
                          </label>

                          <label className="flex items-center space-x-2">
                            <input
                              type="checkbox"
                              checked={settings.scheduling.blueHourMode}
                              onChange={(e) => updateSchedulingSettings('blueHourMode', e.target.checked)}
                              className="w-4 h-4 text-golden-600 focus:ring-golden-500 border-mountain-300 rounded"
                            />
                            <span className="text-sm text-mountain-700">🌆 Blue Hour</span>
                          </label>

                          <label className="flex items-center space-x-2">
                            <input
                              type="checkbox"
                              checked={settings.scheduling.nightMode}
                              onChange={(e) => updateSchedulingSettings('nightMode', e.target.checked)}
                              className="w-4 h-4 text-golden-600 focus:ring-golden-500 border-mountain-300 rounded"
                            />
                            <span className="text-sm text-mountain-700">🌌 Night Mode</span>
                          </label>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </Card>
          </div>

          {/* Live Preview Panel */}
          <div className="space-y-6">
            <Card className="sticky top-6">
              <div className="p-6">
                <h3 className="text-lg font-semibold text-mountain-900 mb-4">
                  📸 Live Preview
                </h3>
                <CameraPreview
                  showControls={false}
                  showOverlay={true}
                  autoStart={true}
                />
              </div>
            </Card>

            {/* Current Settings Summary */}
            <Card>
              <div className="p-6">
                <h3 className="text-lg font-semibold text-mountain-900 mb-4">
                  📋 Current Settings
                </h3>

                <div className="space-y-3 text-sm">
                  <div className="flex justify-between">
                    <span className="text-mountain-600">ISO</span>
                    <span className="font-medium">{settings.manual.iso}</span>
                  </div>

                  <div className="flex justify-between">
                    <span className="text-mountain-600">Shutter</span>
                    <span className="font-medium">{formatExposureTime(settings.manual.exposureTime)}</span>
                  </div>

                  <div className="flex justify-between">
                    <span className="text-mountain-600">Exposure Comp</span>
                    <span className="font-medium">
                      {settings.manual.exposureCompensation > 0 ? '+' : ''}{settings.manual.exposureCompensation} EV
                    </span>
                  </div>

                  <div className="flex justify-between">
                    <span className="text-mountain-600">HDR</span>
                    <span className="font-medium">
                      {settings.manual.hdrBracketing ? `${settings.manual.bracketStops} stops` : 'Off'}
                    </span>
                  </div>

                  <div className="flex justify-between">
                    <span className="text-mountain-600">Format</span>
                    <span className="font-medium">{settings.manual.format}</span>
                  </div>

                  <div className="flex justify-between">
                    <span className="text-mountain-600">White Balance</span>
                    <span className="font-medium capitalize">{settings.manual.whiteBalance}</span>
                  </div>

                  <div className="flex justify-between">
                    <span className="text-mountain-600">Rotation</span>
                    <span className="font-medium">{settings.manual.rotationDegrees}°</span>
                  </div>

                  {settings.scheduling.enabled && (
                    <>
                      <hr className="border-mountain-200" />
                      <div className="flex justify-between">
                        <span className="text-mountain-600">Interval</span>
                        <span className="font-medium">{settings.scheduling.intervalSeconds}s</span>
                      </div>

                      <div className="flex justify-between">
                        <span className="text-mountain-600">Duration</span>
                        <span className="font-medium">{settings.scheduling.durationMinutes}m</span>
                      </div>
                    </>
                  )}
                </div>
              </div>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CaptureSettingsInterface;
