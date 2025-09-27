"""Intelligent adaptive capture system for performance optimization."""

import asyncio
import logging
import statistics
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from .camera_types import CaptureResult, CaptureSettings

logger = logging.getLogger(__name__)


class CaptureStrategy(Enum):
    """Capture optimization strategies based on environmental conditions."""

    CACHED = "cached"  # Use cached settings (fastest)
    LIGHT_ADAPT = "light_adapt"  # Update exposure/WB only
    FULL_RECALC = "full_recalc"  # Full metering cycle
    REFOCUS = "refocus"  # Full autofocus + recalc


@dataclass
class LightConditions:
    """Current light condition measurements."""

    ambient_lux: Optional[float] = None
    color_temp_k: Optional[float] = None
    ev_reading: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def get_change_magnitude(self, previous: "LightConditions") -> float:
        """Calculate EV change magnitude from previous reading."""
        if not previous or not self.ev_reading or not previous.ev_reading:
            return float("inf")  # Force recalculation if no baseline
        return abs(self.ev_reading - previous.ev_reading)


@dataclass
class TriggerThresholds:
    """Thresholds for capture strategy decisions."""

    LIGHT_ADAPT_EV: float = 0.5  # 0.5 EV change triggers exposure update
    MAJOR_CHANGE_EV: float = 2.0  # 2 EV change triggers full recalc
    COLOR_TEMP_SHIFT_K: float = 500  # 500K shift triggers WB update
    FOCUS_AGE_HOURS: float = 24.0  # Refocus every 24 hours
    TEMP_DRIFT_CELSIUS: float = 10.0  # Temperature change for refocus


@dataclass
class CachedSettings:
    """Cached camera settings for optimization."""

    focus_distance_mm: Optional[float] = None
    focus_timestamp: Optional[datetime] = None
    exposure_baseline_us: Optional[int] = None
    iso_baseline: Optional[int] = None
    white_balance_k: Optional[float] = None
    last_light_conditions: Optional[LightConditions] = None

    @property
    def focus_age(self) -> timedelta:
        """Age of cached focus settings."""
        if not self.focus_timestamp:
            return timedelta(days=999)  # Very old if never set
        return datetime.now() - self.focus_timestamp

    def is_focus_valid(self, max_age_hours: float = 24.0) -> bool:
        """Check if cached focus is still valid."""
        return (
            self.focus_distance_mm is not None
            and self.focus_age.total_seconds() < max_age_hours * 3600
        )


class CaptureSettingsCache:
    """Manages cached camera settings for optimization."""

    def __init__(self):
        self.settings = CachedSettings()
        self.performance_history = deque(maxlen=1000)  # Last 1000 captures

    def cache_focus_settings(self, focus_distance_mm: float) -> None:
        """Cache focus distance (typically infinity for mountains)."""
        self.settings.focus_distance_mm = focus_distance_mm
        self.settings.focus_timestamp = datetime.now()
        logger.info(f"Cached focus distance: {focus_distance_mm}mm")

    def update_exposure_baseline(self, exposure_us: int, iso: int) -> None:
        """Update exposure baseline from successful capture."""
        self.settings.exposure_baseline_us = exposure_us
        self.settings.iso_baseline = iso
        logger.debug(f"Updated exposure baseline: {exposure_us}μs, ISO {iso}")

    def update_white_balance(self, wb_k: float) -> None:
        """Update white balance baseline."""
        self.settings.white_balance_k = wb_k
        logger.debug(f"Updated white balance: {wb_k}K")

    def get_optimized_settings(self, base_settings: CaptureSettings) -> CaptureSettings:
        """Generate optimized settings using cache."""
        optimized = CaptureSettings(
            # Use cached focus if available
            focus_distance_mm=self.settings.focus_distance_mm or base_settings.focus_distance_mm,
            autofocus_enabled=(
                False if self.settings.focus_distance_mm else base_settings.autofocus_enabled
            ),
            # Use cached exposure baseline with adjustments
            exposure_time_us=self.settings.exposure_baseline_us or base_settings.exposure_time_us,
            iso=self.settings.iso_baseline or base_settings.iso,
            # Use cached white balance
            white_balance_k=self.settings.white_balance_k or base_settings.white_balance_k,
            # Preserve other settings
            quality=base_settings.quality,
            format=base_settings.format,
            hdr_bracket_stops=base_settings.hdr_bracket_stops,
        )
        return optimized


class BackgroundLightMonitor:
    """Continuous environmental monitoring for light changes."""

    def __init__(self, sampling_interval: float = 5.0):
        self.sampling_interval = sampling_interval
        self.current_conditions = LightConditions()
        self.history = deque(maxlen=100)  # ~8 minutes of history at 5s intervals
        self._monitoring_task: Optional[asyncio.Task] = None
        self._running = False

    async def start_monitoring(self) -> None:
        """Start background light monitoring task."""
        if self._monitoring_task and not self._monitoring_task.done():
            logger.warning("Light monitoring already running")
            return

        self._running = True
        self._monitoring_task = asyncio.create_task(self._monitor_loop())
        logger.info("Started background light monitoring")

    async def stop_monitoring(self) -> None:
        """Stop background light monitoring."""
        self._running = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info("Stopped background light monitoring")

    async def _monitor_loop(self) -> None:
        """Continuous monitoring loop."""
        while self._running:
            try:
                # Quick light reading (~10ms)
                reading = await self._quick_light_sample()
                self.history.append(reading)
                self.current_conditions = reading

                logger.debug(f"Light reading: {reading.ev_reading:.1f}EV, {reading.color_temp_k}K")

            except Exception as e:
                logger.warning(f"Light monitoring error: {e}")

            await asyncio.sleep(self.sampling_interval)

    async def _quick_light_sample(self) -> LightConditions:
        """Quick light sampling without full camera metering."""
        # TODO: Implement actual light sensor reading
        # For now, simulate with reasonable values
        import random

        # Simulate realistic light variations
        base_ev = 12.0  # Daylight baseline
        ev_variation = random.uniform(-1.0, 1.0)  # ±1 EV variation

        return LightConditions(
            ambient_lux=1000.0 * (2 ** (base_ev + ev_variation - 10)),
            color_temp_k=5500 + random.uniform(-500, 500),
            ev_reading=base_ev + ev_variation,
            timestamp=datetime.now(),
        )

    def get_change_magnitude(self) -> float:
        """Get magnitude of recent light change."""
        if len(self.history) < 2:
            return 0.0

        recent = self.history[-1]
        baseline = self.history[-min(10, len(self.history))]  # 50s ago baseline

        return recent.get_change_magnitude(baseline)


class SmartTriggerSystem:
    """Decision engine for capture optimization strategy."""

    def __init__(self, cache_manager: CaptureSettingsCache, light_monitor: BackgroundLightMonitor):
        self.cache = cache_manager
        self.light_monitor = light_monitor
        self.thresholds = TriggerThresholds()

    async def determine_strategy(self) -> CaptureStrategy:
        """Determine optimal capture strategy based on current conditions."""

        # Check if focus needs updating (rare - mountains don't move)
        if self._needs_refocus():
            logger.info("Refocus required - focus cache expired or environmental drift")
            return CaptureStrategy.REFOCUS

        # Check for major environmental changes
        light_change = self.light_monitor.get_change_magnitude()

        if light_change > self.thresholds.MAJOR_CHANGE_EV:
            logger.info(f"Major light change detected: {light_change:.1f}EV - full recalculation")
            return CaptureStrategy.FULL_RECALC

        # Check for moderate light changes
        if light_change > self.thresholds.LIGHT_ADAPT_EV:
            logger.info(f"Light adaptation needed: {light_change:.1f}EV - exposure update")
            return CaptureStrategy.LIGHT_ADAPT

        # Use cached settings for stable conditions
        logger.debug("Stable conditions - using cached settings")
        return CaptureStrategy.CACHED

    def _needs_refocus(self) -> bool:
        """Determine if refocus is needed."""
        # For mountains, focus should rarely change (infinity focus)
        return (
            not self.cache.settings.is_focus_valid(self.thresholds.FOCUS_AGE_HOURS)
            or self._temperature_drift_significant()
        )

    def _temperature_drift_significant(self) -> bool:
        """Check if temperature drift requires refocus."""
        # TODO: Implement actual temperature monitoring
        # For now, assume no significant drift
        return False


class PerformanceMetrics:
    """Performance tracking and analysis for capture optimization."""

    def __init__(self):
        self.capture_times: Dict[CaptureStrategy, List[float]] = {
            strategy: deque(maxlen=100) for strategy in CaptureStrategy
        }
        self.total_captures = 0
        self.successful_captures = 0

    def record_capture(self, strategy: CaptureStrategy, duration_ms: float, success: bool) -> None:
        """Record capture performance metrics."""
        self.capture_times[strategy].append(duration_ms)
        self.total_captures += 1
        if success:
            self.successful_captures += 1

        logger.debug(f"Capture {strategy.value}: {duration_ms:.1f}ms, success: {success}")

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        summary = {
            "total_captures": self.total_captures,
            "success_rate": self.successful_captures / max(1, self.total_captures),
            "strategy_performance": {},
        }

        for strategy, times in self.capture_times.items():
            if times:
                summary["strategy_performance"][strategy.value] = {
                    "count": len(times),
                    "mean_ms": statistics.mean(times),
                    "p95_ms": (
                        statistics.quantiles(times, n=20)[18] if len(times) >= 20 else max(times)
                    ),
                    "min_ms": min(times),
                    "max_ms": max(times),
                }

        return summary


class IntelligentCaptureManager:
    """Main orchestrator for adaptive capture optimization."""

    def __init__(self, camera_controller):
        self.camera = camera_controller
        self.cache_manager = CaptureSettingsCache()
        self.light_monitor = BackgroundLightMonitor()
        self.trigger_system = SmartTriggerSystem(self.cache_manager, self.light_monitor)
        self.performance_tracker = PerformanceMetrics()
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the intelligent capture system."""
        if self._initialized:
            return

        # Start background light monitoring
        await self.light_monitor.start_monitoring()

        # Initialize with infinity focus for mountain photography
        self.cache_manager.cache_focus_settings(float("inf"))  # Infinity focus

        self._initialized = True
        logger.info("Intelligent capture system initialized")

    async def shutdown(self) -> None:
        """Shutdown the intelligent capture system."""
        await self.light_monitor.stop_monitoring()
        self._initialized = False
        logger.info("Intelligent capture system shutdown")

    async def capture_optimized(self, base_settings: CaptureSettings) -> CaptureResult:
        """Main optimized capture method with adaptive strategy."""
        if not self._initialized:
            await self.initialize()

        start_time = time.time()

        try:
            # Determine optimal capture strategy
            strategy = await self.trigger_system.determine_strategy()

            # Execute capture based on strategy
            if strategy == CaptureStrategy.CACHED:
                result = await self._fast_capture(base_settings)
            elif strategy == CaptureStrategy.LIGHT_ADAPT:
                result = await self._adaptive_capture(base_settings)
            elif strategy == CaptureStrategy.FULL_RECALC:
                result = await self._full_capture(base_settings)
            else:  # REFOCUS
                result = await self._refocus_capture(base_settings)

            # Record performance metrics
            duration_ms = (time.time() - start_time) * 1000
            self.performance_tracker.record_capture(strategy, duration_ms, True)

            # Update cache with successful settings
            self._update_cache_from_result(result)

            return result

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.performance_tracker.record_capture(CaptureStrategy.CACHED, duration_ms, False)
            logger.error(f"Optimized capture failed: {e}")
            raise

    async def _fast_capture(self, base_settings: CaptureSettings) -> CaptureResult:
        """Fast capture using cached settings (~300-400ms)."""
        optimized_settings = self.cache_manager.get_optimized_settings(base_settings)
        return await self.camera.capture_single(optimized_settings)

    async def _adaptive_capture(self, base_settings: CaptureSettings) -> CaptureResult:
        """Adaptive capture with exposure update (~600-800ms)."""
        # TODO: Implement light-adaptive exposure calculation
        # For now, use optimized settings with minor adjustments
        optimized_settings = self.cache_manager.get_optimized_settings(base_settings)
        return await self.camera.capture_single(optimized_settings)

    async def _full_capture(self, base_settings: CaptureSettings) -> CaptureResult:
        """Full capture with complete metering (~1000-1200ms)."""
        # Use original settings but skip autofocus if we have cached focus
        settings = base_settings
        if self.cache_manager.settings.is_focus_valid():
            settings.focus_distance_mm = self.cache_manager.settings.focus_distance_mm
            settings.autofocus_enabled = False

        return await self.camera.capture_single(settings)

    async def _refocus_capture(self, base_settings: CaptureSettings) -> CaptureResult:
        """Full capture with refocus (~2000-2500ms)."""
        # Force autofocus and full recalculation
        settings = base_settings
        settings.autofocus_enabled = True

        result = await self.camera.capture_single(settings)

        # Cache the new focus distance (should be infinity for mountains)
        self.cache_manager.cache_focus_settings(float("inf"))

        return result

    def _update_cache_from_result(self, result: CaptureResult) -> None:
        """Update cache with settings from successful capture."""
        if result.actual_settings:
            if result.actual_settings.exposure_time_us:
                self.cache_manager.update_exposure_baseline(
                    result.actual_settings.exposure_time_us, result.actual_settings.iso or 100
                )
            if result.actual_settings.white_balance_k:
                self.cache_manager.update_white_balance(result.actual_settings.white_balance_k)

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        return self.performance_tracker.get_performance_summary()

    def get_cache_status(self) -> Dict[str, Any]:
        """Get current cache status."""
        return {
            "focus_distance_mm": self.cache_manager.settings.focus_distance_mm,
            "focus_age_hours": self.cache_manager.settings.focus_age.total_seconds() / 3600,
            "focus_valid": self.cache_manager.settings.is_focus_valid(),
            "exposure_baseline_us": self.cache_manager.settings.exposure_baseline_us,
            "iso_baseline": self.cache_manager.settings.iso_baseline,
            "white_balance_k": self.cache_manager.settings.white_balance_k,
            "light_conditions": {
                "current_ev": self.light_monitor.current_conditions.ev_reading,
                "current_temp_k": self.light_monitor.current_conditions.color_temp_k,
                "change_magnitude": self.light_monitor.get_change_magnitude(),
            },
        }
