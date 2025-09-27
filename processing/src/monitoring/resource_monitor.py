"""Resource monitoring for processing operations."""

import asyncio
import logging
import psutil
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ResourceSnapshot:
    """Single point-in-time resource measurement."""
    timestamp: float
    cpu_percent: float
    memory_mb: float
    memory_percent: float
    disk_usage_percent: float
    temperature_c: Optional[float] = None
    process_count: int = 0


@dataclass
class ResourceMetrics:
    """Aggregated resource metrics over monitoring period."""
    duration_seconds: float
    snapshots: List[ResourceSnapshot] = field(default_factory=list)
    peak_cpu_percent: float = 0.0
    peak_memory_mb: float = 0.0
    peak_temperature_c: Optional[float] = None
    average_cpu_percent: float = 0.0
    average_memory_mb: float = 0.0
    thermal_throttling_detected: bool = False
    memory_warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "duration_seconds": self.duration_seconds,
            "peak_cpu_percent": self.peak_cpu_percent,
            "peak_memory_mb": self.peak_memory_mb,
            "peak_temperature_c": self.peak_temperature_c,
            "average_cpu_percent": self.average_cpu_percent,
            "average_memory_mb": self.average_memory_mb,
            "thermal_throttling_detected": self.thermal_throttling_detected,
            "memory_warnings": self.memory_warnings,
            "snapshot_count": len(self.snapshots),
            "timestamp": datetime.now().isoformat()
        }


class ResourceMonitor:
    """Monitor system resources during processing operations."""
    
    def __init__(self, sample_interval: float = 1.0):
        """Initialize resource monitor."""
        self.sample_interval = sample_interval
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._snapshots: List[ResourceSnapshot] = []
        
        # Resource thresholds
        self.memory_warning_threshold_mb = 1500  # 1.5GB
        self.memory_critical_threshold_mb = 2000  # 2GB
        self.cpu_warning_threshold = 90.0  # 90%
        self.temperature_warning_threshold = 75.0  # 75°C
        self.temperature_critical_threshold = 80.0  # 80°C
        
    async def start_monitoring(self) -> None:
        """Start resource monitoring."""
        if self._monitoring:
            return
            
        self._monitoring = True
        self._snapshots = []
        self._monitor_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Resource monitoring started")
        
    async def stop_monitoring(self) -> ResourceMetrics:
        """Stop monitoring and return aggregated metrics."""
        if not self._monitoring:
            return ResourceMetrics(duration_seconds=0.0)
            
        self._monitoring = False
        
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
                
        metrics = self._calculate_metrics()
        logger.info(f"Resource monitoring stopped. Peak memory: {metrics.peak_memory_mb:.1f}MB, "
                   f"Peak CPU: {metrics.peak_cpu_percent:.1f}%")
        
        return metrics
        
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        start_time = time.time()
        
        try:
            while self._monitoring:
                snapshot = await self._take_snapshot()
                self._snapshots.append(snapshot)
                
                # Check for warnings
                self._check_resource_warnings(snapshot)
                
                await asyncio.sleep(self.sample_interval)
                
        except asyncio.CancelledError:
            logger.debug("Resource monitoring loop cancelled")
        except Exception as e:
            logger.error(f"Resource monitoring error: {e}")
            
    async def _take_snapshot(self) -> ResourceSnapshot:
        """Take a single resource measurement snapshot."""
        # CPU and memory from psutil
        cpu_percent = psutil.cpu_percent(interval=None)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Temperature (Pi-specific)
        temperature = await self._get_cpu_temperature()
        
        # Process count
        process_count = len(psutil.pids())
        
        return ResourceSnapshot(
            timestamp=time.time(),
            cpu_percent=cpu_percent,
            memory_mb=memory.used / 1024 / 1024,
            memory_percent=memory.percent,
            disk_usage_percent=disk.percent,
            temperature_c=temperature,
            process_count=process_count
        )
        
    async def _get_cpu_temperature(self) -> Optional[float]:
        """Get CPU temperature (Raspberry Pi specific)."""
        try:
            # Try Pi-specific thermal zone
            thermal_file = Path('/sys/class/thermal/thermal_zone0/temp')
            if thermal_file.exists():
                temp_str = thermal_file.read_text().strip()
                # Pi reports temperature in millidegrees
                return float(temp_str) / 1000.0
                
            # Try alternative methods
            sensors = psutil.sensors_temperatures()
            if 'cpu_thermal' in sensors:
                return sensors['cpu_thermal'][0].current
            elif 'coretemp' in sensors:
                return sensors['coretemp'][0].current
                
        except Exception as e:
            logger.debug(f"Could not read CPU temperature: {e}")
            
        return None
        
    def _check_resource_warnings(self, snapshot: ResourceSnapshot) -> None:
        """Check snapshot for resource warnings."""
        # Memory warnings
        if snapshot.memory_mb > self.memory_critical_threshold_mb:
            logger.error(f"CRITICAL: Memory usage {snapshot.memory_mb:.1f}MB exceeds "
                        f"{self.memory_critical_threshold_mb}MB threshold")
        elif snapshot.memory_mb > self.memory_warning_threshold_mb:
            logger.warning(f"Memory usage {snapshot.memory_mb:.1f}MB exceeds "
                          f"{self.memory_warning_threshold_mb}MB threshold")
            
        # CPU warnings
        if snapshot.cpu_percent > self.cpu_warning_threshold:
            logger.warning(f"High CPU usage: {snapshot.cpu_percent:.1f}%")
            
        # Temperature warnings
        if snapshot.temperature_c:
            if snapshot.temperature_c > self.temperature_critical_threshold:
                logger.error(f"CRITICAL: CPU temperature {snapshot.temperature_c:.1f}°C "
                           f"exceeds {self.temperature_critical_threshold}°C")
            elif snapshot.temperature_c > self.temperature_warning_threshold:
                logger.warning(f"CPU temperature {snapshot.temperature_c:.1f}°C "
                             f"exceeds {self.temperature_warning_threshold}°C")
                
    def _calculate_metrics(self) -> ResourceMetrics:
        """Calculate aggregated metrics from snapshots."""
        if not self._snapshots:
            return ResourceMetrics(duration_seconds=0.0)
            
        start_time = self._snapshots[0].timestamp
        end_time = self._snapshots[-1].timestamp
        duration = end_time - start_time
        
        # Calculate peaks and averages
        cpu_values = [s.cpu_percent for s in self._snapshots]
        memory_values = [s.memory_mb for s in self._snapshots]
        temp_values = [s.temperature_c for s in self._snapshots if s.temperature_c is not None]
        
        peak_cpu = max(cpu_values) if cpu_values else 0.0
        peak_memory = max(memory_values) if memory_values else 0.0
        peak_temp = max(temp_values) if temp_values else None
        
        avg_cpu = sum(cpu_values) / len(cpu_values) if cpu_values else 0.0
        avg_memory = sum(memory_values) / len(memory_values) if memory_values else 0.0
        
        # Detect thermal throttling (temperature drops after being high)
        thermal_throttling = False
        if temp_values and len(temp_values) > 5:
            # Look for temperature drops of >5°C after being >75°C
            for i in range(1, len(temp_values)):
                if (temp_values[i-1] > 75.0 and 
                    temp_values[i] < temp_values[i-1] - 5.0):
                    thermal_throttling = True
                    break
                    
        # Collect memory warnings
        memory_warnings = []
        for snapshot in self._snapshots:
            if snapshot.memory_mb > self.memory_critical_threshold_mb:
                memory_warnings.append(f"Critical memory usage: {snapshot.memory_mb:.1f}MB")
            elif snapshot.memory_mb > self.memory_warning_threshold_mb:
                memory_warnings.append(f"High memory usage: {snapshot.memory_mb:.1f}MB")
                
        return ResourceMetrics(
            duration_seconds=duration,
            snapshots=self._snapshots.copy(),
            peak_cpu_percent=peak_cpu,
            peak_memory_mb=peak_memory,
            peak_temperature_c=peak_temp,
            average_cpu_percent=avg_cpu,
            average_memory_mb=avg_memory,
            thermal_throttling_detected=thermal_throttling,
            memory_warnings=list(set(memory_warnings))  # Remove duplicates
        )
        
    async def get_current_status(self) -> Dict:
        """Get current resource status snapshot."""
        if not self._monitoring:
            return {"monitoring": False}
            
        snapshot = await self._take_snapshot()
        
        return {
            "monitoring": True,
            "current_cpu_percent": snapshot.cpu_percent,
            "current_memory_mb": snapshot.memory_mb,
            "current_temperature_c": snapshot.temperature_c,
            "snapshots_collected": len(self._snapshots),
            "monitoring_duration_seconds": time.time() - self._snapshots[0].timestamp if self._snapshots else 0
        }


class ProcessingResourceMonitor:
    """Context manager for monitoring resources during processing operations."""
    
    def __init__(self, operation_name: str, sample_interval: float = 1.0):
        self.operation_name = operation_name
        self.monitor = ResourceMonitor(sample_interval)
        self.metrics: Optional[ResourceMetrics] = None
        
    async def __aenter__(self):
        await self.monitor.start_monitoring()
        logger.info(f"Started resource monitoring for: {self.operation_name}")
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.metrics = await self.monitor.stop_monitoring()
        
        # Log summary
        if self.metrics:
            logger.info(f"Resource monitoring complete for {self.operation_name}: "
                       f"Peak memory: {self.metrics.peak_memory_mb:.1f}MB, "
                       f"Peak CPU: {self.metrics.peak_cpu_percent:.1f}%, "
                       f"Duration: {self.metrics.duration_seconds:.1f}s")
                       
            # Log warnings
            if self.metrics.thermal_throttling_detected:
                logger.warning(f"Thermal throttling detected during {self.operation_name}")
                
            for warning in self.metrics.memory_warnings:
                logger.warning(f"{self.operation_name}: {warning}")
                
    def get_metrics(self) -> Optional[ResourceMetrics]:
        """Get the collected metrics after monitoring is complete."""
        return self.metrics
