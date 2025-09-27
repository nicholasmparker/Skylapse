"""Performance benchmark tests for capture system."""

import asyncio
import statistics
import tempfile
import time
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
import pytest_asyncio
from src.camera_controller import CameraController
from src.camera_types import CameraCapability, CaptureSettings
from src.cameras.mock_camera import MockCamera
from src.scheduler import CaptureScheduler
from src.storage_manager import StorageManager


@pytest.mark.performance
class TestPerformanceBenchmarks:
    """Performance benchmark tests to validate system requirements."""

    @pytest_asyncio.fixture
    async def performance_camera_controller(self):
        """Create camera controller optimized for performance testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create optimized mock camera config
            config_dir = Path(temp_dir)
            config_dir.mkdir(exist_ok=True)

            performance_config = {
                "sensor": {"model": "Performance Test Camera", "base_iso": 100, "max_iso": 800},
                "optical": {"focal_length_mm": 4.28, "hyperfocal_distance_mm": 1830},
                "mock": {
                    "capture_delay_ms": 1,  # Minimal delay for performance testing
                    "simulate_failures": False,
                    "failure_rate": 0.0,
                    "output_dir": temp_dir,
                },
                "performance": {
                    "capture_buffer_size": 1,
                    "max_capture_latency_ms": 50,
                    "focus_timeout_ms": 2000,
                },
                "capabilities": [
                    "AUTOFOCUS",
                    "MANUAL_FOCUS",
                    "HDR_BRACKETING",
                    "FOCUS_STACKING",
                    "RAW_CAPTURE",
                    "LIVE_PREVIEW",
                ],
            }

            import yaml

            with open(config_dir / "mock_camera.yaml", "w") as f:
                yaml.dump(performance_config, f)

            controller = CameraController(config_dir=temp_dir)
            await controller.initialize_camera()
            yield controller
            await controller.shutdown()

    @pytest_asyncio.fixture
    async def benchmarking_timer(self):
        """Utility for precise timing measurements."""

        class BenchmarkTimer:
            def __init__(self):
                self.measurements = []

            @asynccontextmanager
            async def time_operation(self, name: str):
                start_time = time.perf_counter()
                try:
                    yield
                finally:
                    end_time = time.perf_counter()
                    duration_ms = (end_time - start_time) * 1000
                    self.measurements.append(
                        {"operation": name, "duration_ms": duration_ms, "timestamp": time.time()}
                    )

            def get_stats(self, operation_name: str = None):
                if operation_name:
                    measurements = [
                        m for m in self.measurements if m["operation"] == operation_name
                    ]
                else:
                    measurements = self.measurements

                if not measurements:
                    return {}

                durations = [m["duration_ms"] for m in measurements]
                return {
                    "count": len(durations),
                    "min_ms": min(durations),
                    "max_ms": max(durations),
                    "avg_ms": statistics.mean(durations),
                    "median_ms": statistics.median(durations),
                    "p95_ms": (
                        statistics.quantiles(durations, n=20)[18]
                        if len(durations) >= 20
                        else max(durations)
                    ),
                    "p99_ms": (
                        statistics.quantiles(durations, n=100)[98]
                        if len(durations) >= 100
                        else max(durations)
                    ),
                }

            def assert_performance_target(
                self, operation_name: str, target_ms: float, percentile: str = "avg"
            ):
                stats = self.get_stats(operation_name)
                actual_ms = stats.get(f"{percentile}_ms", float("inf"))
                assert (
                    actual_ms <= target_ms
                ), f"{operation_name} {percentile} time {actual_ms:.2f}ms exceeds target {target_ms}ms"

        return BenchmarkTimer()

    @pytest.mark.asyncio
    async def test_capture_latency_benchmark(
        self, performance_camera_controller, benchmarking_timer
    ):
        """Test capture latency meets <50ms requirement."""
        controller = performance_camera_controller

        # Warm up the camera
        await controller.capture_single_image(CaptureSettings(quality=85))

        # Run capture latency benchmark
        iterations = 50
        settings = CaptureSettings(
            quality=90,
            format="JPEG",
            iso=100,
            autofocus_enabled=False,  # Disable AF for consistent timing
        )

        for i in range(iterations):
            async with benchmarking_timer.time_operation("single_capture"):
                result = await controller.capture_single_image(settings)
                assert len(result.file_paths) == 1

        # Validate performance requirements
        stats = benchmarking_timer.get_stats("single_capture")

        # Primary requirement: <50ms average capture latency
        benchmarking_timer.assert_performance_target("single_capture", 50.0, "avg")

        # Additional requirements for system reliability
        benchmarking_timer.assert_performance_target(
            "single_capture", 100.0, "p95"
        )  # 95th percentile

        print(f"Capture Latency Benchmark Results:")
        print(f"  Average: {stats['avg_ms']:.2f}ms (target: <50ms)")
        print(f"  95th percentile: {stats['p95_ms']:.2f}ms (target: <100ms)")
        print(f"  Min: {stats['min_ms']:.2f}ms, Max: {stats['max_ms']:.2f}ms")
        print(f"  Iterations: {stats['count']}")

    @pytest.mark.asyncio
    async def test_focus_acquisition_benchmark(
        self, performance_camera_controller, benchmarking_timer
    ):
        """Test focus acquisition meets <2s requirement."""
        controller = performance_camera_controller

        # Test autofocus performance
        iterations = 20

        for i in range(iterations):
            async with benchmarking_timer.time_operation("autofocus"):
                success = await controller.camera.autofocus(timeout_ms=2000)
                assert success is True

        # Validate focus speed requirement
        benchmarking_timer.assert_performance_target("autofocus", 2000.0, "avg")  # <2s requirement

        stats = benchmarking_timer.get_stats("autofocus")
        print(f"Focus Acquisition Benchmark Results:")
        print(f"  Average: {stats['avg_ms']:.0f}ms (target: <2000ms)")
        print(f"  95th percentile: {stats['p95_ms']:.0f}ms")
        print(f"  Success rate: 100% (all attempts successful)")

    @pytest.mark.asyncio
    async def test_hdr_sequence_performance(
        self, performance_camera_controller, benchmarking_timer
    ):
        """Test HDR sequence capture performance."""
        controller = performance_camera_controller

        # Test HDR bracketing performance
        hdr_stops = [-1, 0, 1]  # 3-shot bracket
        base_settings = CaptureSettings(exposure_time_us=1000, iso=100, autofocus_enabled=False)

        iterations = 10

        for i in range(iterations):
            async with benchmarking_timer.time_operation("hdr_sequence"):
                result = await controller.capture_hdr_sequence(hdr_stops, base_settings)
                assert len(result.file_paths) == 3

        # HDR should complete within reasonable time (target: <500ms for 3 shots)
        benchmarking_timer.assert_performance_target("hdr_sequence", 500.0, "avg")

        stats = benchmarking_timer.get_stats("hdr_sequence")
        print(f"HDR Sequence Benchmark Results:")
        print(f"  Average: {stats['avg_ms']:.2f}ms (target: <500ms for 3 shots)")
        print(f"  Per shot: {stats['avg_ms']/3:.2f}ms average")

    @pytest.mark.asyncio
    async def test_continuous_capture_performance(
        self, performance_camera_controller, benchmarking_timer
    ):
        """Test sustained capture performance over time."""
        controller = performance_camera_controller

        # Simulate continuous timelapse capture for 30 seconds
        duration_seconds = 30
        capture_interval = 2.0  # Every 2 seconds

        settings = CaptureSettings(quality=85, format="JPEG", iso=100)
        start_time = time.time()
        capture_count = 0

        while (time.time() - start_time) < duration_seconds:
            async with benchmarking_timer.time_operation("continuous_capture"):
                result = await controller.capture_single_image(settings)
                assert len(result.file_paths) == 1
                capture_count += 1

            # Wait for next capture interval
            await asyncio.sleep(capture_interval)

        # Validate sustained performance
        stats = benchmarking_timer.get_stats("continuous_capture")

        # Capture latency should remain consistent under load
        benchmarking_timer.assert_performance_target(
            "continuous_capture", 75.0, "avg"
        )  # Slightly relaxed under load

        # Verify we maintained target capture rate
        expected_captures = duration_seconds / capture_interval
        capture_rate = capture_count / duration_seconds

        print(f"Continuous Capture Benchmark Results:")
        print(f"  Duration: {duration_seconds}s")
        print(f"  Captures: {capture_count} (expected: ~{expected_captures:.0f})")
        print(f"  Capture rate: {capture_rate:.2f} fps")
        print(f"  Average latency: {stats['avg_ms']:.2f}ms")

        assert capture_count >= (expected_captures * 0.9)  # Allow 10% margin for timing

    @pytest.mark.asyncio
    async def test_storage_write_performance(self):
        """Test storage write speed meets requirements."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_manager = StorageManager(temp_dir)
            await storage_manager.initialize()

            try:
                # Test writing multiple files quickly
                file_sizes = [1024 * 50, 1024 * 100, 1024 * 200]  # 50KB, 100KB, 200KB
                write_times = []

                for i, size in enumerate(file_sizes):
                    # Create test file
                    test_data = b"X" * size
                    test_file = Path(temp_dir) / f"perf_test_{i}.jpg"
                    test_file.write_bytes(test_data)

                    # Measure storage operation time
                    from src.camera_types import CaptureResult, CaptureSettings

                    capture_result = CaptureResult(
                        file_paths=[str(test_file)],
                        capture_time_ms=30.0,
                        quality_score=0.8,
                        metadata={},
                        actual_settings=CaptureSettings(),
                    )

                    start_time = time.perf_counter()
                    stored_paths = await storage_manager.store_capture_result(capture_result)
                    end_time = time.perf_counter()

                    write_time_ms = (end_time - start_time) * 1000
                    write_times.append(write_time_ms)

                    assert len(stored_paths) == 1
                    assert Path(stored_paths[0]).exists()

                avg_write_time = statistics.mean(write_times)
                max_write_time = max(write_times)

                # Storage writes should be fast (target: <100ms for typical image)
                assert (
                    avg_write_time < 100.0
                ), f"Average write time {avg_write_time:.2f}ms exceeds 100ms target"

                print(f"Storage Write Performance:")
                print(f"  Average write time: {avg_write_time:.2f}ms")
                print(f"  Max write time: {max_write_time:.2f}ms")
                print(f"  File sizes tested: {[s//1024 for s in file_sizes]}KB")

            finally:
                await storage_manager.shutdown()

    @pytest.mark.asyncio
    async def test_scheduler_decision_performance(self):
        """Test scheduler decision-making performance."""
        scheduler = CaptureScheduler()
        await scheduler.initialize()

        try:
            from src.camera_types import EnvironmentalConditions

            # Test conditions
            test_conditions = [
                EnvironmentalConditions(is_golden_hour=True, ambient_light_lux=2000),
                EnvironmentalConditions(is_blue_hour=True, ambient_light_lux=100),
                EnvironmentalConditions(ambient_light_lux=10000, sun_elevation_deg=45),
                EnvironmentalConditions(ambient_light_lux=50000, sun_elevation_deg=75),
            ]

            decision_times = []

            for conditions in test_conditions * 25:  # 100 decisions total
                start_time = time.perf_counter()
                should_capture = await scheduler.should_capture_now(conditions)
                next_time = await scheduler.get_next_capture_time(conditions)
                end_time = time.perf_counter()

                decision_time_ms = (end_time - start_time) * 1000
                decision_times.append(decision_time_ms)

                assert isinstance(should_capture, bool)
                assert isinstance(next_time, (int, float))

            avg_decision_time = statistics.mean(decision_times)
            max_decision_time = max(decision_times)

            # Scheduler decisions should be very fast (target: <10ms)
            assert (
                avg_decision_time < 10.0
            ), f"Average decision time {avg_decision_time:.2f}ms exceeds 10ms target"

            print(f"Scheduler Decision Performance:")
            print(f"  Average decision time: {avg_decision_time:.2f}ms")
            print(f"  Max decision time: {max_decision_time:.2f}ms")
            print(f"  Decisions tested: {len(decision_times)}")

        finally:
            await scheduler.shutdown()

    @pytest.mark.asyncio
    async def test_memory_usage_stability(self, performance_camera_controller):
        """Test that memory usage remains stable under load."""
        import os

        import psutil

        controller = performance_camera_controller
        process = psutil.Process(os.getpid())

        # Get baseline memory usage
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Perform many captures to test for memory leaks
        settings = CaptureSettings(quality=85, format="JPEG")

        for i in range(100):
            result = await controller.capture_single_image(settings)
            assert len(result.file_paths) == 1

            # Check memory periodically
            if i % 25 == 0:
                current_memory = process.memory_info().rss / 1024 / 1024
                memory_growth = current_memory - baseline_memory

                # Memory growth should be reasonable (target: <50MB growth)
                assert (
                    memory_growth < 50.0
                ), f"Memory grew by {memory_growth:.1f}MB after {i} captures"

        final_memory = process.memory_info().rss / 1024 / 1024
        total_growth = final_memory - baseline_memory

        print(f"Memory Usage Stability:")
        print(f"  Baseline: {baseline_memory:.1f}MB")
        print(f"  Final: {final_memory:.1f}MB")
        print(f"  Growth: {total_growth:.1f}MB (target: <50MB)")
        print(f"  Captures: 100")

    @pytest.mark.asyncio
    async def test_system_integration_performance(self):
        """Test integrated system performance with all components."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create integrated system
            storage_manager = StorageManager(temp_dir)
            await storage_manager.initialize()

            scheduler = CaptureScheduler()
            await scheduler.initialize()

            # Create performance config
            config_dir = Path(temp_dir) / "config"
            config_dir.mkdir(exist_ok=True)

            import yaml

            config = {
                "sensor": {"model": "Integration Test Camera"},
                "mock": {"capture_delay_ms": 1, "output_dir": temp_dir, "simulate_failures": False},
                "capabilities": ["AUTOFOCUS", "HDR_BRACKETING"],
            }

            with open(config_dir / "mock_camera.yaml", "w") as f:
                yaml.dump(config, f)

            controller = CameraController(config_dir=str(config_dir))
            await controller.initialize_camera()

            try:
                # Test integrated workflow timing
                from src.camera_types import EnvironmentalConditions

                conditions = EnvironmentalConditions(is_golden_hour=True, ambient_light_lux=2000)

                total_workflow_times = []

                for i in range(10):
                    start_time = time.perf_counter()

                    # Full workflow: decision -> capture -> store
                    should_capture = await scheduler.should_capture_now(conditions)

                    if should_capture:
                        result = await controller.capture_single_image(CaptureSettings())
                        stored_paths = await storage_manager.store_capture_result(result)
                        await scheduler.record_capture_attempt(result, success=True)

                        assert len(stored_paths) == 1

                    end_time = time.perf_counter()
                    workflow_time_ms = (end_time - start_time) * 1000
                    total_workflow_times.append(workflow_time_ms)

                avg_workflow_time = statistics.mean(total_workflow_times)
                max_workflow_time = max(total_workflow_times)

                # Complete workflow should be fast (target: <200ms)
                assert (
                    avg_workflow_time < 200.0
                ), f"Average workflow time {avg_workflow_time:.2f}ms exceeds 200ms target"

                print(f"Integrated System Performance:")
                print(f"  Average workflow time: {avg_workflow_time:.2f}ms")
                print(f"  Max workflow time: {max_workflow_time:.2f}ms")
                print(f"  Target: <200ms per complete capture workflow")

            finally:
                await controller.shutdown()
                await scheduler.shutdown()
                await storage_manager.shutdown()


@pytest.mark.performance
class TestPerformanceRegression:
    """Performance regression tests to ensure system maintains speed over time."""

    @pytest.mark.asyncio
    async def test_capture_performance_regression(self):
        """Baseline test for capture performance regression detection."""
        # This test establishes performance baselines that can be compared
        # across different versions of the system

        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)

            import yaml

            config = {
                "sensor": {"model": "Regression Test Camera"},
                "mock": {"capture_delay_ms": 5, "output_dir": temp_dir},  # Realistic delay
                "capabilities": ["AUTOFOCUS"],
            }

            with open(config_dir / "mock_camera.yaml", "w") as f:
                yaml.dump(config, f)

            controller = CameraController(config_dir=str(temp_dir))
            await controller.initialize_camera()

            try:
                # Baseline performance test
                iterations = 30
                settings = CaptureSettings(quality=90, format="JPEG")

                capture_times = []

                for i in range(iterations):
                    start_time = time.perf_counter()
                    result = await controller.capture_single_image(settings)
                    end_time = time.perf_counter()

                    capture_time_ms = (end_time - start_time) * 1000
                    capture_times.append(capture_time_ms)

                    assert len(result.file_paths) == 1

                avg_time = statistics.mean(capture_times)
                p95_time = (
                    statistics.quantiles(capture_times, n=20)[18]
                    if len(capture_times) >= 20
                    else max(capture_times)
                )

                # Document baseline performance for regression tracking
                baseline_metrics = {
                    "version": "1.0.0",  # Update with actual version
                    "test_date": time.strftime("%Y-%m-%d"),
                    "avg_capture_time_ms": avg_time,
                    "p95_capture_time_ms": p95_time,
                    "iterations": iterations,
                }

                print(f"Performance Baseline Metrics:")
                print(f"  Version: {baseline_metrics['version']}")
                print(f"  Average capture time: {avg_time:.2f}ms")
                print(f"  95th percentile: {p95_time:.2f}ms")
                print(f"  Test date: {baseline_metrics['test_date']}")

                # These values serve as regression baselines
                # Future test runs should compare against these values
                assert avg_time < 100.0  # Reasonable baseline threshold

            finally:
                await controller.shutdown()
