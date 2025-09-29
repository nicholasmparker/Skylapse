/**
 * Environmental Conditions Panel - Astronomical and weather data
 * Professional Mountain Timelapse Camera System
 */

import React from 'react';
import { Card } from '../../design-system/components';
import { LOCATION } from '../../config/environment';
import {
  SunIcon,
  MoonIcon,
  CloudIcon,
  MapPinIcon
} from '@heroicons/react/24/outline';

interface EnvironmentalData {
  sunElevation: number;
  sunAzimuth: number;
  isGoldenHour: boolean;
  isBluHour: boolean;
  nextGoldenHour: string | null;
  temperature: number;
  humidity: number;
  cloudCover: number;
  windSpeed: number;
}

interface EnvironmentalConditionsPanelProps {
  data: EnvironmentalData | null;
  isConnected: boolean;
}

export const EnvironmentalConditionsPanel: React.FC<EnvironmentalConditionsPanelProps> = ({
  data,
  isConnected
}) => {
  const formatNextGoldenHour = (timestamp: string | null) => {
    if (!timestamp) return 'Unknown';

    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = date.getTime() - now.getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffMinutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));

    if (diffMs < 0) return 'In progress';
    if (diffHours > 0) return `${diffHours}h ${diffMinutes}m`;
    return `${diffMinutes}m`;
  };

  const getSunPhaseIcon = () => {
    if (!data) return <SunIcon className="w-6 h-6 text-mountain-400" />;

    if (data.isGoldenHour) {
      return <SunIcon className="w-6 h-6 text-golden-500" />;
    } else if (data.isBluHour) {
      return <MoonIcon className="w-6 h-6 text-blue-500" />;
    } else if (data.sunElevation > 0) {
      return <SunIcon className="w-6 h-6 text-yellow-500" />;
    } else {
      return <MoonIcon className="w-6 h-6 text-mountain-600" />;
    }
  };

  const getSunPhaseText = () => {
    if (!data) return 'Unknown';

    if (data.isGoldenHour) return 'Golden Hour';
    if (data.isBluHour) return 'Blue Hour';
    if (data.sunElevation > 6) return 'Daylight';
    if (data.sunElevation > -6) return 'Twilight';
    return 'Night';
  };

  const getSunPhaseColor = () => {
    if (!data) return 'text-mountain-400';

    if (data.isGoldenHour) return 'text-golden-600';
    if (data.isBluHour) return 'text-blue-600';
    if (data.sunElevation > 0) return 'text-yellow-600';
    return 'text-mountain-600';
  };

  const getVisibilityStatus = () => {
    if (!data) return { text: 'Unknown', color: 'text-mountain-400' };

    if (data.cloudCover < 25) {
      return { text: 'Excellent', color: 'text-green-600' };
    } else if (data.cloudCover < 50) {
      return { text: 'Good', color: 'text-blue-600' };
    } else if (data.cloudCover < 75) {
      return { text: 'Fair', color: 'text-yellow-600' };
    } else {
      return { text: 'Poor', color: 'text-red-600' };
    }
  };

  const visibility = getVisibilityStatus();

  return (
    <Card
      title="Environmental Conditions"
      subtitle="Astronomical events and weather data"
      className="h-full"
      data-testid="environmental-conditions-panel"
    >
      <div className="space-y-6">

        {/* Current Sun Phase */}
        <div className="flex items-center justify-between p-4 bg-mountain-50 rounded-lg">
          <div className="flex items-center space-x-3">
            {getSunPhaseIcon()}
            <div>
              <div className={`font-semibold ${getSunPhaseColor()}`}>
                {getSunPhaseText()}
              </div>
              <div className="text-sm text-mountain-600">
                Current lighting condition
              </div>
            </div>
          </div>

          {data && (
            <div className="text-right">
              <div className="text-sm font-medium text-mountain-900">
                {data.sunElevation.toFixed(1)}°
              </div>
              <div className="text-xs text-mountain-500">
                Elevation
              </div>
            </div>
          )}
        </div>

        {/* Astronomical Data */}
        {data && (
          <div className="grid grid-cols-2 gap-4">

            {/* Sun Position */}
            <div className="p-3 bg-white border border-mountain-200 rounded-lg" data-testid="sun-position">
              <div className="flex items-center space-x-2 mb-2">
                <SunIcon className="w-4 h-4 text-golden-500" />
                <span className="text-sm font-medium text-mountain-700">Sun Position</span>
              </div>
              <div className="space-y-1">
                <div className="flex justify-between text-sm">
                  <span className="text-mountain-600">Elevation:</span>
                  <span className="font-medium" data-testid="sun-elevation">{data.sunElevation.toFixed(1)}°</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-mountain-600">Azimuth:</span>
                  <span className="font-medium" data-testid="sun-azimuth">{data.sunAzimuth.toFixed(1)}°</span>
                </div>
              </div>
            </div>

            {/* Next Golden Hour */}
            <div className="p-3 bg-white border border-mountain-200 rounded-lg">
              <div className="flex items-center space-x-2 mb-2">
                <SunIcon className="w-4 h-4 text-golden-500" />
                <span className="text-sm font-medium text-mountain-700">Next Golden Hour</span>
              </div>
              <div className="text-center">
                <div className="text-lg font-semibold text-golden-600" data-testid="next-golden-hour">
                  {formatNextGoldenHour(data.nextGoldenHour)}
                </div>
                <div className="text-xs text-mountain-500" data-testid="golden-hour-status">
                  {data.isGoldenHour ? 'Currently active' : 'Time remaining'}
                </div>
                <div className="hidden" data-testid="blue-hour-status">
                  {data.isBluHour ? 'Blue hour active' : 'Blue hour inactive'}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Weather Conditions */}
        {data && (
          <div className="space-y-3" data-testid="weather-data">
            <h4 className="font-medium text-mountain-900 flex items-center space-x-2">
              <CloudIcon className="w-4 h-4" />
              <span>Weather Conditions</span>
            </h4>

            <div className="grid grid-cols-2 gap-3">

              {/* Temperature & Humidity */}
              <div className="p-3 bg-mountain-50 rounded-lg">
                <div className="text-center">
                  <div className="text-lg font-semibold text-mountain-900" data-testid="temperature">
                    {data.temperature.toFixed(1)}°C
                  </div>
                  <div className="text-sm text-mountain-600">Temperature</div>
                  <div className="text-xs text-mountain-500 mt-1" data-testid="humidity">
                    {data.humidity.toFixed(0)}%
                  </div>
                </div>
              </div>

              {/* Wind & Visibility */}
              <div className="p-3 bg-mountain-50 rounded-lg">
                <div className="text-center">
                  <div className="text-lg font-semibold text-mountain-900" data-testid="wind-speed">
                    {data.windSpeed.toFixed(1)} m/s
                  </div>
                  <div className="text-sm text-mountain-600">Wind Speed</div>
                  <div className={`text-xs mt-1 ${visibility.color}`}>
                    {visibility.text} visibility
                  </div>
                </div>
              </div>
            </div>

            {/* Cloud Cover Bar */}
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-mountain-600">Cloud Cover</span>
                <span className="font-medium" data-testid="cloud-cover">{data.cloudCover.toFixed(0)}%</span>
              </div>
              <div className="w-full bg-mountain-200 rounded-full h-2">
                <div
                  className="bg-gradient-to-r from-blue-400 to-mountain-400 h-2 rounded-full transition-all duration-500"
                  style={{ width: `${data.cloudCover}%` }}
                />
              </div>
            </div>
          </div>
        )}

        {/* Location Info */}
        <div className="pt-4 border-t border-mountain-200">
          <div className="flex items-center space-x-2 text-sm text-mountain-600" data-testid="location-info">
            <MapPinIcon className="w-4 h-4" />
            <span>{LOCATION.name} ({Math.abs(LOCATION.latitude).toFixed(2)}°{LOCATION.latitude >= 0 ? 'N' : 'S'}, {Math.abs(LOCATION.longitude).toFixed(2)}°{LOCATION.longitude >= 0 ? 'E' : 'W'})</span>
          </div>
        </div>

        {/* Connection Status */}
        {!isConnected && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
            <div className="flex items-center space-x-2 text-red-700">
              <div className="w-2 h-2 bg-red-500 rounded-full" />
              <span className="text-sm font-medium">
                Environmental data unavailable
              </span>
            </div>
            <div className="text-xs text-red-600 mt-1">
              Reconnect to view current conditions
            </div>
          </div>
        )}
      </div>
    </Card>
  );
};
