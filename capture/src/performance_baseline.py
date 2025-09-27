"""Performance baseline measurement for hardware validation."""

import asyncio
import logging
import statistics
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from .camera_types import CaptureResult, CaptureSettings

logger = logging.getLogger(__name__)


@dataclass
class BaselineMetrics:
    """Performance baseline measurement results."""

    mean_ms: float
    std_ms: float
    min_ms: float
    max_ms: float
    p95_ms: float
    p99_ms: float
    measurements: List[float] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    iterations: int = 0
    success_rate: float = 0.0

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "mean_ms": self.mean_ms,
            "std_ms": self.std_ms,
            "min_ms": self.min_ms,
            "max_ms": self.max_ms,
            "p95_ms": self.p95_ms,
            "p99_ms": self.p99_ms,
            "iterations": self.iterations,
            "success_rate": self.success_rate,
            "timestamp": self.timestamp.isoformat(),
            "measurements": self.measurements,
        }


class PerformanceBaseline:
    """Hardware performance baseline measurement system."""

    def __init__(self, camera_controller):
        self.camera = camera_controller
        self.baseline_cache: Optional[BaselineMetrics] = None

    async def measure_current_performance(
        self, iterations: int = 10, settings: Optional[CaptureSettings] = None
    ) -> BaselineMetrics:
        """
        Measure current capture performance for baseline.

        Args:
            iterations: Number of capture measurements to take
            settings: Capture settings to use (default: standard settings)

        Returns:
            BaselineMetrics with statistical analysis
        """
        if settings is None:
            settings = CaptureSettings(quality=95, format="JPEG", iso=100, autofocus_enabled=True)

        logger.info(f"Starting performance baseline measurement: {iterations} iterations")

        times = []
        successful_captures = 0

        for i in range(iterations):
            logger.info(f"Baseline measurement {i+1}/{iterations}")

            try:
                start_time = time.time()
                result = await self.camera.capture_single_image(settings)
                end_time = time.time()

                capture_time_ms = (end_time - start_time) * 1000
                times.append(capture_time_ms)
                successful_captures += 1

                logger.info(f"Capture {i+1}: {capture_time_ms:.1f}ms")

                # Small delay between captures to avoid hardware stress
                await asyncio.sleep(1.0)

            except Exception as e:
                logger.error(f"Capture {i+1} failed: {e}")
                # Continue with remaining measurements

        if not times:
            raise RuntimeError("No successful captures for baseline measurement")

        # Calculate statistics
        mean_ms = statistics.mean(times)
        std_ms = statistics.stdev(times) if len(times) > 1 else 0.0
        min_ms = min(times)
        max_ms = max(times)

        # Calculate percentiles
        sorted_times = sorted(times)
        p95_idx = int(0.95 * len(sorted_times))
        p99_idx = int(0.99 * len(sorted_times))
        p95_ms = sorted_times[min(p95_idx, len(sorted_times) - 1)]
        p99_ms = sorted_times[min(p99_idx, len(sorted_times) - 1)]

        success_rate = successful_captures / iterations

        baseline = BaselineMetrics(
            mean_ms=mean_ms,
            std_ms=std_ms,
            min_ms=min_ms,
            max_ms=max_ms,
            p95_ms=p95_ms,
            p99_ms=p99_ms,
            measurements=times,
            iterations=iterations,
            success_rate=success_rate,
        )

        # Cache the baseline for comparison
        self.baseline_cache = baseline

        logger.info(f"Baseline measurement complete:")
        logger.info(f"  Mean: {mean_ms:.1f}ms ± {std_ms:.1f}ms")
        logger.info(f"  Range: {min_ms:.1f}ms - {max_ms:.1f}ms")
        logger.info(f"  P95: {p95_ms:.1f}ms, P99: {p99_ms:.1f}ms")
        logger.info(f"  Success rate: {success_rate:.1%}")

        return baseline

    async def compare_performance(
        self, new_measurements: List[float], baseline: Optional[BaselineMetrics] = None
    ) -> Dict:
        """
        Compare new performance measurements against baseline.

        Args:
            new_measurements: List of capture times in milliseconds
            baseline: Baseline to compare against (uses cached if None)

        Returns:
            Dictionary with comparison analysis
        """
        if baseline is None:
            baseline = self.baseline_cache

        if baseline is None:
            raise ValueError("No baseline available for comparison")

        if not new_measurements:
            raise ValueError("No new measurements provided")

        new_mean = statistics.mean(new_measurements)
        improvement_factor = baseline.mean_ms / new_mean
        improvement_percent = ((baseline.mean_ms - new_mean) / baseline.mean_ms) * 100

        comparison = {
            "baseline_mean_ms": baseline.mean_ms,
            "new_mean_ms": new_mean,
            "improvement_factor": improvement_factor,
            "improvement_percent": improvement_percent,
            "faster": new_mean < baseline.mean_ms,
            "target_achieved": {
                "18x_faster": improvement_factor >= 18.0,
                "24x_faster": improvement_factor >= 24.0,
                "300_400ms": 300 <= new_mean <= 400,
                "sub_500ms": new_mean < 500,
            },
        }

        logger.info(f"Performance comparison:")
        logger.info(f"  Baseline: {baseline.mean_ms:.1f}ms")
        logger.info(f"  New: {new_mean:.1f}ms")
        logger.info(
            f"  Improvement: {improvement_factor:.1f}x faster ({improvement_percent:+.1f}%)"
        )

        return comparison

    async def validate_optimization_claims(self) -> Dict:
        """
        Validate the theoretical optimization claims against baseline.

        Returns:
            Dictionary with claim validation results
        """
        if self.baseline_cache is None:
            raise ValueError("No baseline measurement available")

        baseline = self.baseline_cache

        # Theoretical targets from intelligent capture system
        targets = {
            "cached_capture": {"min": 300, "max": 400, "frequency": 0.70},
            "light_adapt": {"min": 600, "max": 800, "frequency": 0.25},
            "full_recalc": {"min": 1000, "max": 1200, "frequency": 0.04},
            "refocus": {"min": 2000, "max": 2500, "frequency": 0.01},
        }

        validation = {"baseline_mean_ms": baseline.mean_ms, "targets": {}, "overall_assessment": {}}

        weighted_improvement = 0.0

        for strategy, target in targets.items():
            target_mean = (target["min"] + target["max"]) / 2
            improvement_factor = baseline.mean_ms / target_mean
            frequency = target["frequency"]

            validation["targets"][strategy] = {
                "target_range_ms": f"{target['min']}-{target['max']}",
                "target_mean_ms": target_mean,
                "improvement_factor": improvement_factor,
                "frequency": frequency,
                "achievable": improvement_factor >= 1.0,
            }

            weighted_improvement += improvement_factor * frequency

        validation["overall_assessment"] = {
            "weighted_improvement_factor": weighted_improvement,
            "theoretical_speedup": f"{weighted_improvement:.1f}x faster",
            "claims_realistic": weighted_improvement >= 10.0,  # Conservative threshold
            "baseline_supports_optimization": baseline.mean_ms >= 5000,  # Need sufficient baseline
        }

        logger.info(f"Optimization claim validation:")
        logger.info(f"  Baseline: {baseline.mean_ms:.1f}ms")
        logger.info(f"  Weighted improvement: {weighted_improvement:.1f}x")
        logger.info(f"  Claims realistic: {validation['overall_assessment']['claims_realistic']}")

        return validation

    def get_baseline_summary(self) -> Optional[Dict]:
        """Get summary of current baseline measurements."""
        if self.baseline_cache is None:
            return None

        return self.baseline_cache.to_dict()


class HardwareValidator:
    """Hardware validation and deployment helper."""

    def __init__(self, camera_controller):
        self.camera = camera_controller
        self.baseline = PerformanceBaseline(camera_controller)

    async def run_comprehensive_validation(self) -> Dict:
        """
        Run comprehensive hardware validation suite.

        Returns:
            Complete validation report
        """
        logger.info("Starting comprehensive hardware validation")

        validation_report = {
            "timestamp": datetime.now().isoformat(),
            "hardware_info": await self._get_hardware_info(),
            "baseline_measurement": None,
            "optimization_validation": None,
            "recommendations": [],
        }

        try:
            # Measure baseline performance
            baseline = await self.baseline.measure_current_performance(iterations=15)
            validation_report["baseline_measurement"] = baseline.to_dict()

            # Validate optimization claims
            optimization_validation = await self.baseline.validate_optimization_claims()
            validation_report["optimization_validation"] = optimization_validation

            # Generate recommendations
            recommendations = self._generate_recommendations(baseline, optimization_validation)
            validation_report["recommendations"] = recommendations

        except Exception as e:
            logger.error(f"Hardware validation failed: {e}")
            validation_report["error"] = str(e)

        return validation_report

    async def _get_hardware_info(self) -> Dict:
        """Get hardware information for validation context."""
        try:
            camera_status = await self.camera.get_camera_status()
            return {
                "camera_model": camera_status.get("camera_model", "Unknown"),
                "capabilities": camera_status.get("capabilities", []),
                "initialized": camera_status.get("initialized", False),
            }
        except Exception as e:
            logger.warning(f"Could not get hardware info: {e}")
            return {"error": str(e)}

    def _generate_recommendations(self, baseline: BaselineMetrics, validation: Dict) -> List[str]:
        """Generate recommendations based on validation results."""
        recommendations = []

        if baseline.mean_ms > 10000:  # > 10 seconds
            recommendations.append(
                "Baseline performance is very slow - optimization will have high impact"
            )
        elif baseline.mean_ms < 1000:  # < 1 second
            recommendations.append(
                "Baseline performance is already fast - optimization gains may be limited"
            )

        if baseline.success_rate < 0.9:
            recommendations.append("Low success rate detected - investigate hardware reliability")

        if baseline.std_ms > baseline.mean_ms * 0.2:
            recommendations.append(
                "High performance variability - consider system stability improvements"
            )

        overall = validation.get("overall_assessment", {})
        if overall.get("claims_realistic", False):
            recommendations.append(
                "Optimization claims appear realistic based on baseline measurements"
            )
        else:
            recommendations.append(
                "Optimization claims may be overly ambitious - consider more conservative targets"
            )

        return recommendations
