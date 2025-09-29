/**
 * Weather Service - Real weather data integration
 * Professional Mountain Timelapse Camera System
 */

interface WeatherData {
  temperature: number;
  humidity: number;
  cloudCover: number;
  windSpeed: number;
  pressure?: number;
  visibility?: number;
}

interface WeatherServiceError extends Error {
  code: 'NETWORK_ERROR' | 'API_ERROR' | 'PARSING_ERROR';
}

/**
 * Weather service using OpenWeatherMap API
 * Falls back to mock data if API is unavailable
 */
export class WeatherService {
  private static readonly API_KEY = import.meta.env.VITE_OPENWEATHER_API_KEY;
  private static readonly BASE_URL = 'https://api.openweathermap.org/data/2.5';
  private static readonly CACHE_DURATION = 10 * 60 * 1000; // 10 minutes

  private static cache: {
    data: WeatherData | null;
    timestamp: number;
  } = { data: null, timestamp: 0 };

  /**
   * Get current weather data for coordinates
   */
  static async getCurrentWeather(lat: number, lon: number): Promise<WeatherData> {
    try {
      // Check cache first
      if (this.isCacheValid()) {
        return this.cache.data!;
      }

      // If no API key provided, return mock data with warning
      if (!this.API_KEY) {
        console.warn('OpenWeatherMap API key not configured, using mock weather data');
        return this.getMockWeatherData();
      }

      const url = `${this.BASE_URL}/weather?lat=${lat}&lon=${lon}&appid=${this.API_KEY}&units=metric`;

      const response = await fetch(url);

      if (!response.ok) {
        throw new Error(`Weather API error: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();

      const weatherData: WeatherData = {
        temperature: Math.round(data.main.temp * 10) / 10,
        humidity: data.main.humidity,
        cloudCover: data.clouds.all,
        windSpeed: Math.round(data.wind.speed * 10) / 10,
        pressure: data.main.pressure,
        visibility: data.visibility ? data.visibility / 1000 : undefined, // Convert m to km
      };

      // Update cache
      this.cache = {
        data: weatherData,
        timestamp: Date.now(),
      };

      return weatherData;

    } catch (error) {
      console.error('Weather service error:', error);

      // Return cached data if available
      if (this.cache.data && Date.now() - this.cache.timestamp < 60 * 60 * 1000) { // 1 hour stale cache tolerance
        console.warn('Using stale weather data due to API error');
        return this.cache.data;
      }

      // Final fallback to mock data
      console.warn('Falling back to mock weather data');
      return this.getMockWeatherData();
    }
  }

  /**
   * Check if cached data is still valid
   */
  private static isCacheValid(): boolean {
    return this.cache.data !== null &&
           Date.now() - this.cache.timestamp < this.CACHE_DURATION;
  }

  /**
   * Get mock weather data as fallback
   */
  private static getMockWeatherData(): WeatherData {
    // Generate realistic mock data with some variation
    const baseTemp = 18;
    const variation = Math.sin(Date.now() / 1000000) * 5; // Slow variation

    return {
      temperature: Math.round((baseTemp + variation) * 10) / 10,
      humidity: Math.round(65 + Math.sin(Date.now() / 800000) * 15),
      cloudCover: Math.round(30 + Math.sin(Date.now() / 600000) * 40),
      windSpeed: Math.round((8 + Math.sin(Date.now() / 400000) * 4) * 10) / 10,
      pressure: 1013,
      visibility: 10,
    };
  }

  /**
   * Clear the cache (useful for testing)
   */
  static clearCache(): void {
    this.cache = { data: null, timestamp: 0 };
  }
}
