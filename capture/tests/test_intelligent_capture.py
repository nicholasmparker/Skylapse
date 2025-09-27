"""Tests for intelligent adaptive capture system."""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from src.camera_types import CaptureResult, CaptureSettings
from src.intelligent_capture import (
    BackgroundLightMonitor,
    CaptureSettingsCache,
    CaptureStrategy,
    IntelligentCaptureManager,
    LightConditions,
    PerformanceMetrics,
    SmartTriggerSystem,
)


class TestLightConditions:
    """Test light condition measurements and change detection."""

    def test_light_conditions_creation(self):
        """Test creating light conditions with default values."""
        conditions = LightConditions()
        assert conditions.ambient_lux is None
        assert conditions.color_temp_k is None
        assert conditions.ev_reading is None
        assert isinstance(conditions.timestamp, datetime)

    def test_change_magnitude_calculation(self):
        """Test EV change magnitude calculation."""
        baseline = LightConditions(ev_reading=12.0)
        current = LightConditions(ev_reading=13.5)

        change = current.get_change_magnitude(baseline)
        assert change == 1.5

    def test_change_magnitude_no_baseline(self):
        """Test change magnitude with missing baseline."""
        current = LightConditions(ev_reading=12.0)
        change = current.get_change_magnitude(None)
        assert change == float("inf")


class TestCaptureSettingsCache:
    """Test capture settings caching functionality."""

    def test_cache_initialization(self):
        """Test cache starts empty."""
        cache = CaptureSettingsCache()
        assert cache.settings.focus_distance_mm is None
        assert cache.settings.focus_timestamp is None
        assert not cache.settings.is_focus_valid()

    def test_focus_caching(self):
        """Test focus distance caching."""
        cache = CaptureSettingsCache()
        cache.cache_focus_settings(float("inf"))

        assert cache.settings.focus_distance_mm == float("inf")
        assert cache.settings.focus_timestamp is not None
        assert cache.settings.is_focus_valid()

    def test_focus_age_calculation(self):
        """Test focus age calculation."""
        cache = CaptureSettingsCache()
        cache.cache_focus_settings(1000.0)

        # Should be very recent
        assert cache.settings.focus_age.total_seconds() < 1.0

    def test_exposure_baseline_update(self):
        """Test exposure baseline caching."""
        cache = CaptureSettingsCache()
        cache.update_exposure_baseline(1000, 200)

        assert cache.settings.exposure_baseline_us == 1000
        assert cache.settings.iso_baseline == 200

    def test_optimized_settings_generation(self):
        """Test generating optimized settings from cache."""
        cache = CaptureSettingsCache()
        cache.cache_focus_settings(float("inf"))
        cache.update_exposure_baseline(2000, 100)
        cache.update_white_balance(5500)

        base_settings = CaptureSettings(quality=95)
        optimized = cache.get_optimized_settings(base_settings)

        assert optimized.focus_distance_mm == float("inf")
        assert optimized.autofocus_enabled is False
        assert optimized.exposure_time_us == 2000
        assert optimized.iso == 100
        assert optimized.white_balance_k == 5500
        assert optimized.quality == 95


class TestBackgroundLightMonitor:
    """Test background light monitoring system."""

    @pytest.fixture
    def monitor(self):
        """Create light monitor for testing."""
        return BackgroundLightMonitor(sampling_interval=0.1)  # Fast for testing

    @pytest.mark.asyncio
    async def test_monitor_start_stop(self, monitor):
        """Test starting and stopping light monitoring."""
        await monitor.start_monitoring()
        assert monitor._running
        assert monitor._monitoring_task is not None

        await asyncio.sleep(0.2)  # Let it run briefly

        await monitor.stop_monitoring()
        assert not monitor._running

    @pytest.mark.asyncio
    async def test_light_sampling(self, monitor):
        """Test light sampling functionality."""
        reading = await monitor._quick_light_sample()

        assert isinstance(reading, LightConditions)
        assert reading.ambient_lux is not None
        assert reading.color_temp_k is not None
        assert reading.ev_reading is not None

    @pytest.mark.asyncio
    async def test_change_detection(self, monitor):
        """Test light change magnitude detection."""
        # Start monitoring to build history
        await monitor.start_monitoring()
        await asyncio.sleep(0.3)  # Build some history

        change_magnitude = monitor.get_change_magnitude()
        assert isinstance(change_magnitude, float)
        assert change_magnitude >= 0.0

        await monitor.stop_monitoring()


class TestSmartTriggerSystem:
    """Test smart trigger decision system."""

    @pytest.fixture
    def cache_manager(self):
        """Create mock cache manager."""
        cache = CaptureSettingsCache()
        cache.cache_focus_settings(float("inf"))  # Valid focus
        return cache

    @pytest.fixture
    def light_monitor(self):
        """Create mock light monitor."""
        monitor = MagicMock()
        monitor.get_change_magnitude.return_value = 0.3  # Small change
        return monitor

    @pytest.fixture
    def trigger_system(self, cache_manager, light_monitor):
        """Create trigger system for testing."""
        return SmartTriggerSystem(cache_manager, light_monitor)

    @pytest.mark.asyncio
    async def test_cached_strategy_stable_conditions(self, trigger_system, light_monitor):
        """Test cached strategy for stable conditions."""
        light_monitor.get_change_magnitude.return_value = 0.3  # Below threshold

        strategy = await trigger_system.determine_strategy()
        assert strategy == CaptureStrategy.CACHED

    @pytest.mark.asyncio
    async def test_light_adapt_strategy(self, trigger_system, light_monitor):
        """Test light adaptation strategy."""
        light_monitor.get_change_magnitude.return_value = 1.0  # Above light adapt threshold

        strategy = await trigger_system.determine_strategy()
        assert strategy == CaptureStrategy.LIGHT_ADAPT

    @pytest.mark.asyncio
    async def test_full_recalc_strategy(self, trigger_system, light_monitor):
        """Test full recalculation strategy."""
        light_monitor.get_change_magnitude.return_value = 3.0  # Above major change threshold

        strategy = await trigger_system.determine_strategy()
        assert strategy == CaptureStrategy.FULL_RECALC

    @pytest.mark.asyncio
    async def test_refocus_strategy_expired_cache(self, trigger_system, cache_manager):
        """Test refocus strategy when focus cache is expired."""
        # Make focus cache very old
        cache_manager.settings.focus_timestamp = datetime.now() - timedelta(hours=25)

        strategy = await trigger_system.determine_strategy()
        assert strategy == CaptureStrategy.REFOCUS


class TestPerformanceMetrics:
    """Test performance tracking system."""

    @pytest.fixture
    def metrics(self):
        """Create performance metrics tracker."""
        return PerformanceMetrics()

    def test_capture_recording(self, metrics):
        """Test recording capture performance."""
        metrics.record_capture(CaptureStrategy.CACHED, 350.0, True)
        metrics.record_capture(CaptureStrategy.LIGHT_ADAPT, 750.0, True)
        metrics.record_capture(CaptureStrategy.CACHED, 400.0, False)

        assert metrics.total_captures == 3
        assert metrics.successful_captures == 2

        summary = metrics.get_performance_summary()
        assert summary["total_captures"] == 3
        assert summary["success_rate"] == 2 / 3

        cached_perf = summary["strategy_performance"]["cached"]
        assert cached_perf["count"] == 2
        assert cached_perf["mean_ms"] == 375.0  # (350 + 400) / 2


class TestIntelligentCaptureManager:
    """Test main intelligent capture manager."""

    @pytest.fixture
    def mock_camera_controller(self):
        """Create mock camera controller."""
        controller = MagicMock()
        controller.capture_single = AsyncMock()
        controller.capture_single.return_value = CaptureResult(
            file_paths=["/tmp/test.jpg"],
            metadata={"test": True},
            actual_settings=CaptureSettings(exposure_time_us=1000, iso=100),
            capture_time_ms=350.0,
            quality_score=0.9,
        )
        return controller

    @pytest.fixture
    def capture_manager(self, mock_camera_controller):
        """Create intelligent capture manager for testing."""
        return IntelligentCaptureManager(mock_camera_controller)

    @pytest.mark.asyncio
    async def test_initialization(self, capture_manager):
        """Test capture manager initialization."""
        await capture_manager.initialize()

        assert capture_manager._initialized
        assert capture_manager.light_monitor._running
        assert capture_manager.cache_manager.settings.focus_distance_mm == float("inf")

        await capture_manager.shutdown()

    @pytest.mark.asyncio
    async def test_optimized_capture_cached_strategy(self, capture_manager, mock_camera_controller):
        """Test optimized capture with cached strategy."""
        await capture_manager.initialize()

        # Mock trigger system to return cached strategy
        with patch.object(capture_manager.trigger_system, "determine_strategy") as mock_strategy:
            mock_strategy.return_value = CaptureStrategy.CACHED

            settings = CaptureSettings(quality=95)
            result = await capture_manager.capture_optimized(settings)

            assert result is not None
            assert mock_camera_controller.capture_single.called

        await capture_manager.shutdown()

    @pytest.mark.asyncio
    async def test_performance_metrics_collection(self, capture_manager):
        """Test performance metrics are collected."""
        await capture_manager.initialize()

        with patch.object(capture_manager.trigger_system, "determine_strategy") as mock_strategy:
            mock_strategy.return_value = CaptureStrategy.CACHED

            settings = CaptureSettings()
            await capture_manager.capture_optimized(settings)

            metrics = capture_manager.get_performance_metrics()
            assert metrics["total_captures"] == 1
            assert metrics["success_rate"] == 1.0

        await capture_manager.shutdown()

    @pytest.mark.asyncio
    async def test_cache_status_reporting(self, capture_manager):
        """Test cache status reporting."""
        await capture_manager.initialize()

        status = capture_manager.get_cache_status()

        assert "focus_distance_mm" in status
        assert "focus_age_hours" in status
        assert "focus_valid" in status
        assert "light_conditions" in status

        await capture_manager.shutdown()

    @pytest.mark.asyncio
    async def test_cache_update_from_result(self, capture_manager):
        """Test cache updates from successful capture results."""
        await capture_manager.initialize()

        result = CaptureResult(
            file_paths=["/tmp/test.jpg"],
            metadata={},
            actual_settings=CaptureSettings(exposure_time_us=2000, iso=200, white_balance_k=5500),
            capture_time_ms=400.0,
            quality_score=0.9,
        )

        capture_manager._update_cache_from_result(result)

        assert capture_manager.cache_manager.settings.exposure_baseline_us == 2000
        assert capture_manager.cache_manager.settings.iso_baseline == 200
        assert capture_manager.cache_manager.settings.white_balance_k == 5500

        await capture_manager.shutdown()


class TestIntegrationScenarios:
    """Integration tests for realistic capture scenarios."""

    @pytest.fixture
    def mock_camera_controller(self):
        """Create realistic mock camera controller."""
        controller = MagicMock()

        # Simulate different capture times based on strategy
        async def mock_capture(settings):
            if settings.autofocus_enabled:
                capture_time = 2500.0  # Refocus scenario
            elif hasattr(settings, "_strategy_hint"):
                if settings._strategy_hint == "cached":
                    capture_time = 350.0
                elif settings._strategy_hint == "light_adapt":
                    capture_time = 750.0
                else:
                    capture_time = 1100.0
            else:
                capture_time = 400.0  # Default

            return CaptureResult(
                file_paths=["/tmp/test.jpg"],
                metadata={"strategy": getattr(settings, "_strategy_hint", "unknown")},
                actual_settings=settings,
                capture_time_ms=capture_time,
                quality_score=0.9,
            )

        controller.capture_single = AsyncMock(side_effect=mock_capture)
        return controller

    @pytest.mark.asyncio
    async def test_mountain_photography_workflow(self, mock_camera_controller):
        """Test complete mountain photography workflow."""
        manager = IntelligentCaptureManager(mock_camera_controller)
        await manager.initialize()

        # Simulate typical mountain photography session
        base_settings = CaptureSettings(quality=95, format="JPEG")

        # First capture - should use cached strategy after initialization
        result1 = await manager.capture_optimized(base_settings)
        assert result1.capture_time_ms < 500  # Fast cached capture

        # Simulate light change
        manager.light_monitor.current_conditions = LightConditions(ev_reading=14.0)
        manager.light_monitor.history.append(LightConditions(ev_reading=12.0))

        # Second capture - should adapt to light change
        with patch.object(manager.light_monitor, "get_change_magnitude", return_value=1.0):
            await manager.capture_optimized(base_settings)
            # Should be slower due to light adaptation but faster than full recalc

        # Check performance metrics
        metrics = manager.get_performance_metrics()
        assert metrics["total_captures"] == 2

        await manager.shutdown()

    @pytest.mark.asyncio
    async def test_performance_target_validation(self, mock_camera_controller):
        """Validate performance targets are achievable."""
        manager = IntelligentCaptureManager(mock_camera_controller)
        await manager.initialize()

        # Test multiple capture scenarios
        scenarios = [
            (CaptureStrategy.CACHED, 10),  # 70% of captures
            (CaptureStrategy.LIGHT_ADAPT, 3),  # 25% of captures
            (CaptureStrategy.FULL_RECALC, 1),  # 4% of captures
            (CaptureStrategy.REFOCUS, 1),  # 1% of captures
        ]

        for strategy, count in scenarios:
            with patch.object(manager.trigger_system, "determine_strategy", return_value=strategy):
                for _ in range(count):
                    await manager.capture_optimized(CaptureSettings())

        # Validate performance targets
        metrics = manager.get_performance_metrics()
        perf = metrics["strategy_performance"]

        # Validate target times (allowing some tolerance)
        if "cached" in perf:
            assert perf["cached"]["mean_ms"] <= 450  # Target: 300-400ms
        if "light_adapt" in perf:
            assert perf["light_adapt"]["mean_ms"] <= 850  # Target: 600-800ms
        if "full_recalc" in perf:
            assert perf["full_recalc"]["mean_ms"] <= 1300  # Target: 1000-1200ms
        if "refocus" in perf:
            assert perf["refocus"]["mean_ms"] <= 2600  # Target: 2000-2500ms

        await manager.shutdown()


if __name__ == "__main__":
    pytest.main([__file__])
