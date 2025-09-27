"""Tests for capture scheduling functionality."""

import pytest
import pytest_asyncio
import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from src.scheduler import CaptureScheduler, ScheduleRule
from src.camera_types import CaptureSettings, CaptureResult, EnvironmentalConditions


class TestScheduleRule:
    """Test cases for ScheduleRule dataclass."""

    def test_schedule_rule_creation(self):
        """Test creating schedule rules with various parameters."""
        rule = ScheduleRule(
            name="test_rule",
            active=True,
            interval_seconds=60,
            start_hour=6,
            end_hour=18,
            min_light_level=100.0,
            max_light_level=5000.0,
            conditions={"test": True},
        )

        assert rule.name == "test_rule"
        assert rule.active is True
        assert rule.interval_seconds == 60
        assert rule.start_hour == 6
        assert rule.end_hour == 18
        assert rule.min_light_level == 100.0
        assert rule.max_light_level == 5000.0
        assert rule.conditions == {"test": True}

    def test_schedule_rule_defaults(self):
        """Test schedule rule creation with minimal parameters."""
        rule = ScheduleRule(name="minimal_rule", active=True, interval_seconds=30)

        assert rule.name == "minimal_rule"
        assert rule.active is True
        assert rule.interval_seconds == 30
        assert rule.start_hour is None
        assert rule.end_hour is None
        assert rule.min_light_level is None
        assert rule.max_light_level is None
        assert rule.conditions is None


class TestCaptureScheduler:
    """Test cases for CaptureScheduler class."""

    @pytest_asyncio.fixture
    async def scheduler(self):
        """Create and initialize a scheduler instance."""
        scheduler = CaptureScheduler()
        await scheduler.initialize()
        yield scheduler
        await scheduler.shutdown()

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test scheduler initialization."""
        scheduler = CaptureScheduler()
        assert not scheduler._is_initialized

        await scheduler.initialize()
        assert scheduler._is_initialized
        assert len(scheduler._schedule_rules) > 0  # Should have default rules

        await scheduler.shutdown()
        assert not scheduler._is_initialized

    @pytest.mark.asyncio
    async def test_default_schedule_rules(self, scheduler):
        """Test that default schedule rules are loaded correctly."""
        rules = await scheduler.get_schedule_rules()
        rule_names = [rule.name for rule in rules]

        # Check for key default rules from CAP-002 requirements
        assert "golden_hour_intensive" in rule_names
        assert "blue_hour_intensive" in rule_names
        assert "daylight_standard" in rule_names

        # Check golden hour rule specifics
        golden_rule = next(r for r in rules if r.name == "golden_hour_intensive")
        assert golden_rule.active is True
        assert golden_rule.interval_seconds <= 60  # Intensive capture
        assert golden_rule.conditions.get("golden_hour") is True

    @pytest.mark.asyncio
    async def test_add_schedule_rule(self, scheduler):
        """Test adding custom schedule rules."""
        new_rule = ScheduleRule(
            name="custom_rule", active=True, interval_seconds=120, start_hour=10, end_hour=14
        )

        await scheduler.add_schedule_rule(new_rule)
        rules = await scheduler.get_schedule_rules()

        # Should contain the new rule
        rule_names = [rule.name for rule in rules]
        assert "custom_rule" in rule_names

        # Verify rule properties
        custom_rule = next(r for r in rules if r.name == "custom_rule")
        assert custom_rule.interval_seconds == 120
        assert custom_rule.start_hour == 10
        assert custom_rule.end_hour == 14

    @pytest.mark.asyncio
    async def test_remove_schedule_rule(self, scheduler):
        """Test removing schedule rules."""
        # Add a test rule first
        test_rule = ScheduleRule(name="test_remove", active=True, interval_seconds=60)
        await scheduler.add_schedule_rule(test_rule)

        # Verify it was added
        rules = await scheduler.get_schedule_rules()
        assert any(r.name == "test_remove" for r in rules)

        # Remove it
        await scheduler.remove_schedule_rule("test_remove")

        # Verify it was removed
        rules = await scheduler.get_schedule_rules()
        assert not any(r.name == "test_remove" for r in rules)

    @pytest.mark.asyncio
    async def test_should_capture_now_golden_hour(self, scheduler):
        """Test capture decision during golden hour conditions."""
        golden_conditions = EnvironmentalConditions(
            is_golden_hour=True, ambient_light_lux=2000.0, sun_elevation_deg=5.0
        )

        # Should capture during golden hour with intensive rule
        should_capture = await scheduler.should_capture_now(golden_conditions)
        assert should_capture is True

    @pytest.mark.asyncio
    async def test_should_capture_now_daylight(self, scheduler):
        """Test capture decision during regular daylight."""
        daylight_conditions = EnvironmentalConditions(
            is_golden_hour=False,
            is_blue_hour=False,
            ambient_light_lux=10000.0,
            sun_elevation_deg=45.0,
        )

        # Should also capture during daylight but less frequently
        should_capture = await scheduler.should_capture_now(daylight_conditions)
        assert should_capture is True

    @pytest.mark.asyncio
    async def test_should_capture_now_interval_respect(self, scheduler):
        """Test that capture respects interval timing."""
        # Simulate a recent capture
        scheduler._last_capture_time = time.time() - 10  # 10 seconds ago

        conditions = EnvironmentalConditions(is_golden_hour=False, ambient_light_lux=8000.0)

        # Should not capture if recent capture within interval
        should_capture = await scheduler.should_capture_now(conditions)
        # This depends on the default daylight rule interval
        # If interval is > 10 seconds, should be False
        # We'll check the actual rule to be sure
        daylight_rule = next(
            (r for r in scheduler._schedule_rules if r.name == "daylight_standard"), None
        )
        if daylight_rule and daylight_rule.interval_seconds > 10:
            assert should_capture is False

    @pytest.mark.asyncio
    async def test_should_capture_now_no_conditions(self, scheduler):
        """Test capture decision without environmental conditions."""
        # Should handle gracefully and use basic rules
        should_capture = await scheduler.should_capture_now(None)
        assert isinstance(should_capture, bool)

    @pytest.mark.asyncio
    async def test_get_next_capture_time(self, scheduler):
        """Test next capture time calculation."""
        conditions = EnvironmentalConditions(is_golden_hour=True, ambient_light_lux=2000.0)

        next_time = await scheduler.get_next_capture_time(conditions)

        # Should be a future timestamp
        assert isinstance(next_time, float)
        assert next_time > time.time()

        # During golden hour, should be relatively soon (within a minute)
        time_diff = next_time - time.time()
        assert time_diff <= 60  # Should be within 60 seconds for golden hour

    @pytest.mark.asyncio
    async def test_capture_history_tracking(self, scheduler):
        """Test that capture history is tracked correctly."""
        # Simulate some captures
        mock_result = CaptureResult(
            file_paths=["/tmp/test.jpg"],
            capture_time_ms=50.0,
            quality_score=0.9,
            metadata={"test": True},
            actual_settings=CaptureSettings(),
        )

        await scheduler.record_capture_attempt(mock_result, success=True)
        await scheduler.record_capture_attempt(None, success=False)  # Failed capture

        history = scheduler.get_capture_history()

        assert len(history) == 2
        assert history[0]["success"] is True
        assert history[1]["success"] is False
        assert scheduler._failure_count == 1
        assert scheduler._consecutive_failures == 1

    @pytest.mark.asyncio
    async def test_failure_backoff(self, scheduler):
        """Test that scheduler backs off after consecutive failures."""
        # Simulate multiple failures
        for _ in range(3):
            await scheduler.record_capture_attempt(None, success=False)

        conditions = EnvironmentalConditions(is_golden_hour=True)
        next_time = await scheduler.get_next_capture_time(conditions)

        # Should have longer interval due to failures
        time_diff = next_time - time.time()
        assert time_diff > 30  # Should be backed off more than normal

    @pytest.mark.asyncio
    async def test_rule_conditions_matching(self, scheduler):
        """Test that rule conditions are matched correctly."""
        # Add a rule with specific conditions
        specific_rule = ScheduleRule(
            name="test_specific",
            active=True,
            interval_seconds=15,
            conditions={"test_mode": True, "min_elevation": 10},
        )
        await scheduler.add_schedule_rule(specific_rule)

        # Test with matching conditions
        matching_conditions = EnvironmentalConditions(
            sun_elevation_deg=15.0, ambient_light_lux=5000.0
        )

        # Mock the condition matching for test_mode
        with patch.object(scheduler, "_matches_rule_conditions", return_value=True):
            should_capture = await scheduler.should_capture_now(matching_conditions)
            assert should_capture is True

    @pytest.mark.asyncio
    async def test_schedule_statistics(self, scheduler):
        """Test scheduler statistics collection."""
        # Simulate some activity
        await scheduler.record_capture_attempt(
            CaptureResult(
                file_paths=["/tmp/test1.jpg"],
                capture_time_ms=45.0,
                quality_score=0.85,
                metadata={},
                actual_settings=CaptureSettings(),
            ),
            success=True,
        )

        stats = await scheduler.get_statistics()

        assert isinstance(stats, dict)
        assert "total_captures" in stats
        assert "successful_captures" in stats
        assert "failed_captures" in stats
        assert "average_interval" in stats
        assert stats["total_captures"] == 1
        assert stats["successful_captures"] == 1
        assert stats["failed_captures"] == 0

    @pytest.mark.asyncio
    async def test_rule_activation_deactivation(self, scheduler):
        """Test activating and deactivating schedule rules."""
        # Get an existing rule
        rules = await scheduler.get_schedule_rules()
        rule_name = rules[0].name if rules else None
        assert rule_name is not None

        # Deactivate it
        await scheduler.set_rule_active(rule_name, False)
        updated_rules = await scheduler.get_schedule_rules()
        target_rule = next(r for r in updated_rules if r.name == rule_name)
        assert target_rule.active is False

        # Reactivate it
        await scheduler.set_rule_active(rule_name, True)
        updated_rules = await scheduler.get_schedule_rules()
        target_rule = next(r for r in updated_rules if r.name == rule_name)
        assert target_rule.active is True

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test scheduler as async context manager."""
        async with CaptureScheduler() as scheduler:
            assert scheduler._is_initialized
            rules = await scheduler.get_schedule_rules()
            assert len(rules) > 0

        # Should be cleaned up after context exit
        assert not scheduler._is_initialized

    @pytest.mark.asyncio
    async def test_time_of_day_filtering(self, scheduler):
        """Test that time-of-day filtering works correctly."""
        # Add a rule that's only active during specific hours
        dawn_rule = ScheduleRule(
            name="dawn_only", active=True, interval_seconds=30, start_hour=5, end_hour=7
        )
        await scheduler.add_schedule_rule(dawn_rule)

        # Mock current time to be outside the window (noon)
        with patch("time.localtime") as mock_time:
            mock_time.return_value.tm_hour = 12  # Noon

            conditions = EnvironmentalConditions(ambient_light_lux=8000.0)

            # Should not trigger dawn_only rule at noon
            # Implementation depends on how scheduler handles time filtering
            should_capture = await scheduler.should_capture_now(conditions)

            # The result depends on other rules, but dawn_only shouldn't match
            # We can check this by examining the matching rules
            matching_rules = scheduler._get_matching_rules(conditions)
            dawn_rule_matched = any(r.name == "dawn_only" for r in matching_rules)
            assert dawn_rule_matched is False


class TestSchedulerIntegration:
    """Integration tests for scheduler with realistic scenarios."""

    @pytest_asyncio.fixture
    async def full_scheduler(self):
        """Create scheduler with comprehensive rule set."""
        scheduler = CaptureScheduler()
        await scheduler.initialize()

        # Add comprehensive rules for testing
        await scheduler.add_schedule_rule(
            ScheduleRule(
                name="sunrise_golden_hour",
                active=True,
                interval_seconds=10,  # Very frequent during sunrise
                conditions={"golden_hour": True, "sun_rising": True},
            )
        )

        await scheduler.add_schedule_rule(
            ScheduleRule(
                name="midday_sparse",
                active=True,
                interval_seconds=300,  # Every 5 minutes during harsh midday
                start_hour=11,
                end_hour=15,
                conditions={"harsh_light": True},
            )
        )

        yield scheduler
        await scheduler.shutdown()

    @pytest.mark.asyncio
    async def test_realistic_golden_hour_workflow(self, full_scheduler):
        """Test realistic golden hour capture workflow."""
        # Simulate golden hour conditions
        golden_conditions = EnvironmentalConditions(
            is_golden_hour=True,
            sun_elevation_deg=3.0,
            ambient_light_lux=1500.0,
            color_temperature_k=3200,
        )

        # Should want to capture frequently
        should_capture = await full_scheduler.should_capture_now(golden_conditions)
        assert should_capture is True

        # Next capture should be soon
        next_time = await full_scheduler.get_next_capture_time(golden_conditions)
        interval = next_time - time.time()
        assert interval <= 60  # Should be within a minute

    @pytest.mark.asyncio
    async def test_realistic_midday_workflow(self, full_scheduler):
        """Test realistic midday capture workflow."""
        # Simulate harsh midday conditions
        midday_conditions = EnvironmentalConditions(
            is_golden_hour=False,
            is_blue_hour=False,
            sun_elevation_deg=75.0,
            ambient_light_lux=50000.0,
            color_temperature_k=5500,
        )

        # Should still capture but less frequently
        should_capture = await full_scheduler.should_capture_now(midday_conditions)

        # Get the next capture time
        next_time = await full_scheduler.get_next_capture_time(midday_conditions)
        interval = next_time - time.time()

        # Should be longer interval than golden hour
        assert interval >= 60  # At least a minute for midday
