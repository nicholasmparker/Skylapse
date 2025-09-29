/**
 * Astronomical Service - Sun position and golden hour calculations
 * Professional Mountain Timelapse Camera System
 */

interface SolarPosition {
  elevation: number;    // Sun elevation angle in degrees (-90 to 90)
  azimuth: number;     // Sun azimuth angle in degrees (0 to 360)
}

interface GoldenHourData {
  isGoldenHour: boolean;
  isBluHour: boolean;
  nextGoldenHour: string | null;
  nextSunrise: string | null;
  nextSunset: string | null;
}

interface AstronomicalData extends SolarPosition, GoldenHourData {}

/**
 * Astronomical calculations service
 * Uses SunCalc-like algorithms for accurate sun position calculations
 */
export class AstronomicalService {
  private static readonly GOLDEN_HOUR_ANGLE = 6;  // Sun elevation for golden hour
  private static readonly BLUE_HOUR_ANGLE = -6;   // Sun elevation for blue hour
  private static readonly CIVIL_TWILIGHT_ANGLE = -6;

  /**
   * Get comprehensive astronomical data for location and time
   */
  static getAstronomicalData(lat: number, lon: number, date: Date = new Date()): AstronomicalData {
    const solarPosition = this.calculateSolarPosition(lat, lon, date);
    const goldenHourData = this.calculateGoldenHourData(lat, lon, date);

    return {
      ...solarPosition,
      ...goldenHourData,
    };
  }

  /**
   * Calculate current sun position
   */
  static calculateSolarPosition(lat: number, lon: number, date: Date = new Date()): SolarPosition {
    const dayOfYear = this.getDayOfYear(date);
    const hour = date.getHours() + date.getMinutes() / 60;

    // Convert to radians
    const latRad = lat * Math.PI / 180;
    const lonRad = lon * Math.PI / 180;

    // Solar declination angle
    const declination = 23.45 * Math.sin((360 * (284 + dayOfYear) / 365) * Math.PI / 180);
    const declinationRad = declination * Math.PI / 180;

    // Hour angle
    const hourAngle = 15 * (hour - 12) + lon;  // 15 degrees per hour
    const hourAngleRad = hourAngle * Math.PI / 180;

    // Solar elevation angle
    const elevationRad = Math.asin(
      Math.sin(declinationRad) * Math.sin(latRad) +
      Math.cos(declinationRad) * Math.cos(latRad) * Math.cos(hourAngleRad)
    );
    const elevation = elevationRad * 180 / Math.PI;

    // Solar azimuth angle
    const azimuthRad = Math.atan2(
      Math.sin(hourAngleRad),
      Math.cos(hourAngleRad) * Math.sin(latRad) - Math.tan(declinationRad) * Math.cos(latRad)
    );
    let azimuth = azimuthRad * 180 / Math.PI + 180; // Convert to 0-360 range

    // Normalize azimuth to 0-360
    if (azimuth < 0) azimuth += 360;
    if (azimuth >= 360) azimuth -= 360;

    return {
      elevation: Math.round(elevation * 10) / 10,
      azimuth: Math.round(azimuth * 10) / 10,
    };
  }

  /**
   * Calculate golden hour and blue hour data
   */
  static calculateGoldenHourData(lat: number, lon: number, date: Date = new Date()): GoldenHourData {
    const currentPosition = this.calculateSolarPosition(lat, lon, date);

    // Determine current phase
    const isGoldenHour = currentPosition.elevation > this.BLUE_HOUR_ANGLE &&
                        currentPosition.elevation <= this.GOLDEN_HOUR_ANGLE;
    const isBluHour = currentPosition.elevation > -12 &&
                     currentPosition.elevation <= this.BLUE_HOUR_ANGLE;

    // Calculate sunrise and sunset times for today and tomorrow
    const today = new Date(date.getFullYear(), date.getMonth(), date.getDate());
    const tomorrow = new Date(today.getTime() + 24 * 60 * 60 * 1000);

    const todaySunrise = this.calculateSunriseOrSunset(lat, lon, today, true);
    const todaySunset = this.calculateSunriseOrSunset(lat, lon, today, false);
    const tomorrowSunrise = this.calculateSunriseOrSunset(lat, lon, tomorrow, true);
    const tomorrowSunset = this.calculateSunriseOrSunset(lat, lon, tomorrow, false);

    // Find next golden hour
    const nextGoldenHour = this.findNextGoldenHour(
      date,
      todaySunrise,
      todaySunset,
      tomorrowSunrise,
      tomorrowSunset
    );

    return {
      isGoldenHour,
      isBluHour,
      nextGoldenHour: nextGoldenHour ? nextGoldenHour.toISOString() : null,
      nextSunrise: todaySunrise > date ? todaySunrise.toISOString() : tomorrowSunrise.toISOString(),
      nextSunset: todaySunset > date ? todaySunset.toISOString() : tomorrowSunset.toISOString(),
    };
  }

  /**
   * Calculate sunrise or sunset time for a given date
   */
  private static calculateSunriseOrSunset(lat: number, lon: number, date: Date, isSunrise: boolean): Date {
    const dayOfYear = this.getDayOfYear(date);

    // Solar declination
    const declination = 23.45 * Math.sin((360 * (284 + dayOfYear) / 365) * Math.PI / 180);

    // Hour angle at sunrise/sunset (when elevation = 0)
    const latRad = lat * Math.PI / 180;
    const declinationRad = declination * Math.PI / 180;

    const hourAngleRad = Math.acos(-Math.tan(latRad) * Math.tan(declinationRad));
    const hourAngle = hourAngleRad * 180 / Math.PI;

    // Calculate time
    const solarNoon = 12 - lon / 15;
    const sunTime = isSunrise ?
      solarNoon - hourAngle / 15 :
      solarNoon + hourAngle / 15;

    // Create date with calculated time
    const result = new Date(date);
    const hours = Math.floor(sunTime);
    const minutes = Math.floor((sunTime - hours) * 60);
    result.setHours(hours, minutes, 0, 0);

    return result;
  }

  /**
   * Find the next golden hour period
   */
  private static findNextGoldenHour(
    currentTime: Date,
    todaySunrise: Date,
    todaySunset: Date,
    tomorrowSunrise: Date,
    tomorrowSunset: Date
  ): Date | null {
    // Golden hour periods: 1 hour after sunrise, 1 hour before sunset
    const todayMorningGolden = new Date(todaySunrise.getTime() + 0 * 60 * 1000); // Starts at sunrise
    const todayEveningGolden = new Date(todaySunset.getTime() - 60 * 60 * 1000); // 1 hour before sunset
    const tomorrowMorningGolden = new Date(tomorrowSunrise.getTime() + 0 * 60 * 1000);

    // Find next golden hour
    if (currentTime < todayMorningGolden) {
      return todayMorningGolden;
    } else if (currentTime < todayEveningGolden) {
      return todayEveningGolden;
    } else {
      return tomorrowMorningGolden;
    }
  }

  /**
   * Get day of year (1-365/366)
   */
  private static getDayOfYear(date: Date): number {
    const start = new Date(date.getFullYear(), 0, 0);
    const diff = date.getTime() - start.getTime();
    return Math.floor(diff / (1000 * 60 * 60 * 24));
  }

  /**
   * Format time remaining until next golden hour
   */
  static formatTimeUntilGoldenHour(nextGoldenHour: string | null): string {
    if (!nextGoldenHour) return 'Unknown';

    const now = new Date();
    const target = new Date(nextGoldenHour);
    const diffMs = target.getTime() - now.getTime();

    if (diffMs < 0) return 'In progress';

    const hours = Math.floor(diffMs / (1000 * 60 * 60));
    const minutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));

    if (hours > 0) return `${hours}h ${minutes}m`;
    return `${minutes}m`;
  }
}
