# Technical Debt Analysis - Sprint 4

**Date**: 2025-10-01
**Codebase**: Skylapse Timelapse System
**Analyzed by**: Technical Debt & Maintainability Expert
**Total Lines of Code**: ~3,454 (Python backend/Pi services)

---

## Executive Summary

This analysis covers technical debt accumulated across the Skylapse codebase with emphasis on recently implemented features (transfer service, Docker volumes, hybrid image serving, profile deployment). Overall code quality is **GOOD** with solid architecture, but several critical DRY violations and maintainability concerns require immediate attention.

**Priority Distribution**:

- CRITICAL: 2 issues (must fix)
- HIGH: 8 issues (fix soon)
- MEDIUM: 7 issues (plan to fix)
- LOW: 4 issues (nice to have)

**Estimated Total Effort**: 3-4 days of focused work

---

## CRITICAL Issues

### C1: Massive Code Duplication in Profile WB Calculation Logic

**Severity**: CRITICAL
**Effort**: Large (4-6 hours)
**Files**:

- `/Users/nicholasmparker/Projects/skylapse/backend/exposure.py` (lines 217-350)
- `/Users/nicholasmparker/Projects/skylapse/pi/profile_executor.py` (lines 151-191)

**Problem**:
The `_interpolate_wb_from_lux()` function is duplicated between backend and Pi with identical logic. This is a severe DRY violation where:

- Backend has `_calculate_adaptive_wb_temp()` with 3 curve variants (balanced/conservative/warm)
- Pi has `_interpolate_wb_from_lux()` with the same interpolation algorithm
- Backend has 133 lines of hardcoded lux→temp control points (lines 242-304)
- Any bug fix requires changes in TWO places
- Profile curves cannot be tested independently

**Impact**:

- Bug fixes must be applied twice (high risk of inconsistency)
- Testing requires mocking both implementations
- Profile curve adjustments require editing multiple files
- Deployment risk: Backend and Pi could diverge

**Recommended Fix**:

1. Extract WB curve logic to shared module: `backend/wb_curves.py`
2. Define curves as data structures (not code):

```python
# backend/wb_curves.py
WB_CURVES = {
    "balanced": [
        (10000, 5500),
        (8000, 5500),
        (6000, 5450),
        # ... rest of curve
    ],
    "conservative": [...],
    "warm": [...]
}

def interpolate_wb_from_lux(lux: float, curve_name: str = "balanced") -> int:
    """Linear interpolation of WB temp from lux value."""
    control_points = WB_CURVES[curve_name]
    # ... interpolation logic (ONE place)
```

3. Use this in both backend and Pi (import from shared location)
4. Profile deployment sends curve data, not logic

**Benefits**:

- Single source of truth for WB curves
- Easy to test curve behavior
- Can add new curves without code changes
- Profile snapshots include curve data

---

### C2: Hardcoded URL Construction Pattern Throughout Codebase

**Severity**: CRITICAL
**Effort**: Medium (3-4 hours)
**Files**:

- `/Users/nicholasmparker/Projects/skylapse/backend/main.py` (lines 266, 443, 453)
- `/Users/nicholasmparker/Projects/skylapse/backend/exposure.py` (line 32)
- Multiple test files and scripts

**Problem**:
URL construction is scattered with inconsistent patterns:

```python
# Pattern 1: Direct string formatting
pi_url = f"http://{pi_config['host']}:{pi_config['port']}/capture"

# Pattern 2: Hardcoded localhost
"image_url": f"http://localhost:8082/images/..."

# Pattern 3: Environment variables
PI_HOST = os.getenv("PI_HOST", "helios.local")

# Pattern 4: Config with fallback
pi_host = pi_config.get("host", "192.168.0.124")
```

Issues:

- No centralized URL builder
- Hardcoded `localhost:8082` breaks in production
- Mixed use of hostname vs IP address
- No URL validation or sanity checking
- Port numbers scattered across codebase

**Impact**:

- Deployment failures in production environments
- Cannot easily switch between dev/staging/prod
- URL changes require global search-and-replace
- Testing requires mocking multiple URL patterns

**Recommended Fix**:
Create URL builder utility:

```python
# backend/services/url_builder.py
from typing import Optional
from config import Config

class URLBuilder:
    def __init__(self, config: Config):
        self.config = config

    def pi_url(self, endpoint: str = "") -> str:
        """Build Pi service URL"""
        pi = self.config.get_pi_config()
        return f"http://{pi['host']}:{pi['port']}{endpoint}"

    def backend_url(self, endpoint: str = "") -> str:
        """Build backend URL (from env or config)"""
        host = os.getenv("BACKEND_HOST", "localhost")
        port = os.getenv("BACKEND_PORT", "8082")
        return f"http://{host}:{port}{endpoint}"

    def image_url(self, profile: str, filename: str, source: str = "local") -> str:
        """Build image URL (local or Pi fallback)"""
        if source == "local":
            return self.backend_url(f"/images/profile-{profile}/{filename}")
        else:
            return self.pi_url(f"/images/profile-{profile}/{filename}")
```

Replace all URL construction with:

```python
url_builder = URLBuilder(config)
pi_url = url_builder.pi_url("/capture")
image_url = url_builder.image_url(profile, filename)
```

---

## HIGH Priority Issues

### H1: Duplicate Pi Host Configuration Pattern

**Severity**: HIGH
**Effort**: Quick (1 hour)
**Files**:

- `/Users/nicholasmparker/Projects/skylapse/docker-compose.yml` (lines 14, 25)
- `/Users/nicholasmparker/Projects/skylapse/backend/config.json` (line 34)
- `/Users/nicholasmparker/Projects/skylapse/backend/services/transfer.py` (line 21)

**Problem**:
Pi host configured in THREE different places with DIFFERENT values:

```yaml
# docker-compose.yml - backend service
PI_HOST=helios.local

# docker-compose.yml - transfer service
PI_HOST=192.168.0.124  # Use IP instead of hostname

# backend/config.json
"host": "192.168.0.124"

# transfer.py
PI_HOST = os.getenv("PI_HOST", "helios.local")
```

**Impact**:

- Backend and transfer service may target different hosts
- Comment says "use IP instead of hostname" but only applies to transfer
- Configuration changes must be made in 3 places
- Unclear which is the "source of truth"

**Recommended Fix**:

1. Single source: Use `.env` file for environment-specific config

```bash
# .env (git-ignored)
PI_HOST=helios.local
PI_PORT=8080
PI_USER=nicholasmparker
```

2. Docker compose reads from .env:

```yaml
services:
  backend:
    env_file: .env
  transfer:
    env_file: .env
```

3. Remove hardcoded defaults from config.json
4. Add `.env.example` template

---

### H2: Missing Error Handling in Transfer Service

**Severity**: HIGH
**Effort**: Medium (2-3 hours)
**Files**: `/Users/nicholasmparker/Projects/skylapse/backend/services/transfer.py`

**Problem**:
Transfer service has minimal error handling:

- Line 71: Generic `except Exception` catches all errors
- Line 75: Only logs error, doesn't track failure count
- No retry logic for transient network failures
- No alerting when transfers fail repeatedly
- No graceful degradation (keeps running with failures)

**Impact**:

- Silent failures: transfer fails but service continues
- No visibility into chronic issues
- Network blips cause permanent failures
- No way to know if images are being transferred

**Recommended Fix**:

```python
# backend/services/transfer.py
import time
from collections import deque

class TransferService:
    def __init__(self):
        self.failure_count = 0
        self.recent_failures = deque(maxlen=10)
        self.max_retries = 3

    def run_rsync_transfer(self) -> bool:
        """Transfer with retry logic"""
        for attempt in range(self.max_retries):
            try:
                result = subprocess.run(...)
                if result.returncode == 0:
                    self.failure_count = 0  # Reset on success
                    return True
                else:
                    logger.warning(f"Transfer failed (attempt {attempt+1}/{self.max_retries})")
                    if attempt < self.max_retries - 1:
                        time.sleep(5 * (attempt + 1))  # Exponential backoff

            except subprocess.TimeoutExpired:
                logger.error(f"Transfer timeout (attempt {attempt+1})")
                if attempt < self.max_retries - 1:
                    time.sleep(10)

        # All retries failed
        self.failure_count += 1
        self.recent_failures.append(datetime.now())

        # Alert if failures exceed threshold
        if self.failure_count >= 5:
            self.send_alert("Transfer service: 5 consecutive failures")

        return False
```

---

### H3: Inconsistent Profile Validation Between Backend and Pi

**Severity**: HIGH
**Effort**: Medium (2-3 hours)
**Files**:

- `/Users/nicholasmparker/Projects/skylapse/backend/exposure.py` (line 352-454)
- `/Users/nicholasmparker/Projects/skylapse/pi/main.py` (line 117-194)

**Problem**:
Profile settings validation is duplicated and inconsistent:

**Backend** (exposure.py):

- Validates profile letter in `_apply_profile_settings()`
- No formal validation, just falls through to default
- Profile logic embedded in 100+ line function

**Pi** (main.py):

- Pydantic validator on `CaptureSettings.profile`
- Validates against `["default", "a", "b", "c", "d", "e", "f"]`
- But backend only uses `["a", "b", "c", "d", "e", "f"]`

**Impact**:

- Backend accepts profiles Pi rejects (or vice versa)
- No shared validation logic
- Profile changes require updates in multiple places
- Cannot guarantee profile compatibility

**Recommended Fix**:
Create shared validation module:

```python
# Shared between backend and Pi
# backend/profile_schema.py (symlink from pi/)

from pydantic import BaseModel, validator
from enum import Enum

class ProfileID(str, Enum):
    """Valid profile identifiers"""
    A = "a"
    B = "b"
    C = "c"
    D = "d"
    E = "e"
    F = "f"

class ProfileSettings(BaseModel):
    """Validated profile settings schema"""
    iso: int
    shutter_speed: str
    exposure_compensation: float
    awb_mode: int
    # ... all profile fields

    @validator("iso")
    def validate_iso(cls, v):
        if v == 0:  # Auto mode
            return v
        valid = [100, 200, 400, 800, 1600, 3200]
        if v not in valid:
            raise ValueError(f"ISO must be 0 or one of {valid}")
        return v
```

Use in both locations:

```python
# backend/exposure.py
from profile_schema import ProfileID, ProfileSettings

def _apply_profile_settings(base, profile: ProfileID):
    if profile == ProfileID.A:
        # ...
```

---

### H4: parse_time_range() Function Duplicated

**Severity**: HIGH
**Effort**: Quick (30 minutes)
**Files**:

- `/Users/nicholasmparker/Projects/skylapse/backend/main.py` (lines 180-203)
- Used in lines 243, 353, 506

**Problem**:
`parse_time_range()` is a utility function defined inside `main.py` and called from 3 different endpoints. It's not reusable by other modules and violates single responsibility.

**Impact**:

- Cannot test parse_time_range() independently
- Cannot reuse in other services
- Clutters main.py namespace

**Recommended Fix**:
Extract to utilities module:

```python
# backend/utils/time_utils.py
from datetime import time
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)

def parse_time_range(
    schedule_config: dict,
    schedule_name: str
) -> Tuple[Optional[time], Optional[time]]:
    """
    Parse start_time and end_time from schedule config.

    Returns (start_time, end_time) or (None, None) if invalid.
    """
    start_str = schedule_config.get("start_time", "09:00")
    end_str = schedule_config.get("end_time", "15:00")

    try:
        return (time.fromisoformat(start_str), time.fromisoformat(end_str))
    except ValueError as e:
        logger.error(f"Invalid time in {schedule_name}: {e}")
        return (None, None)
```

Replace in main.py:

```python
from utils.time_utils import parse_time_range
```

---

### H5: No Validation of Docker Volume Paths

**Severity**: HIGH
**Effort**: Medium (2 hours)
**Files**: `/Users/nicholasmparker/Projects/skylapse/docker-compose.yml` (lines 54-66)

**Problem**:
Docker volumes use bind mounts with environment variable fallbacks:

```yaml
volumes:
  skylapse-images:
    driver_opts:
      device: ${SKYLAPSE_IMAGES_PATH:-./data/images}
```

Issues:

- No validation that paths exist
- No error if env var points to invalid location
- Services start even if volumes fail to mount
- Silent failures if permissions are wrong

**Impact**:

- Transfer service writes to /data/images but it might not be mounted
- Images could be lost if volume mount fails
- No early warning of misconfiguration

**Recommended Fix**:
Add startup validation:

```python
# backend/services/transfer.py
def validate_storage():
    """Validate storage paths are accessible before starting"""
    required_paths = [
        Path(LOCAL_DEST),
        Path("/data/images"),
        Path("/data/timelapses")
    ]

    for path in required_paths:
        if not path.exists():
            raise RuntimeError(f"Required storage path missing: {path}")
        if not os.access(path, os.W_OK):
            raise RuntimeError(f"No write permission for: {path}")

        logger.info(f"✓ Storage validated: {path}")

# Call at startup
validate_storage()
```

---

### H6: Hardcoded Profile Descriptions Duplicated

**Severity**: HIGH
**Effort**: Quick (30 minutes)
**Files**:

- `/Users/nicholasmparker/Projects/skylapse/backend/main.py` (lines 416-423)
- Likely duplicated in frontend (not reviewed)

**Problem**:
Profile descriptions hardcoded in endpoint:

```python
descriptions = {
    "a": "Auto + Center-Weighted",
    "b": "Daylight WB Fixed",
    # ... 4 more
}
```

**Impact**:

- Changes to profile descriptions require code changes
- Cannot be translated/localized
- Duplicated in multiple places
- Not included in profile deployment payload

**Recommended Fix**:
Move to configuration:

```python
# backend/profile_metadata.py
PROFILE_METADATA = {
    "a": {
        "name": "Auto + Center-Weighted",
        "description": "General purpose auto-exposure, biased toward center of frame",
        "use_case": "Quick setup, reliable results",
        "metering": "center-weighted"
    },
    "b": {
        "name": "Daylight WB Fixed",
        "description": "Fixed white balance for consistent colors",
        "use_case": "Bright daylight, consistent WB across timelapse",
        "metering": "matrix"
    },
    # ... etc
}

def get_profile_info(profile: str) -> dict:
    """Get metadata for a profile"""
    return PROFILE_METADATA.get(profile, {})
```

Include in API responses and profile deployment payloads.

---

### H7: No Centralized Logging Configuration

**Severity**: HIGH
**Effort**: Medium (2 hours)
**Files**:

- `/Users/nicholasmparker/Projects/skylapse/backend/main.py` (lines 32-35)
- `/Users/nicholasmparker/Projects/skylapse/pi/main.py` (lines 26-28)
- `/Users/nicholasmparker/Projects/skylapse/backend/services/transfer.py` (lines 15-18)

**Problem**:
Every module has its own logging setup:

```python
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
```

Issues:

- No centralized log level control
- Cannot change format without editing all files
- No structured logging (JSON) for production
- No log aggregation configuration

**Recommended Fix**:
Create logging utility:

```python
# backend/utils/logging_config.py
import logging
import os
from pathlib import Path

def setup_logging(
    service_name: str,
    level: str = None,
    log_file: Path = None
):
    """Configure logging for a service"""
    level = level or os.getenv("LOG_LEVEL", "INFO")

    handlers = []

    # Console handler
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))
    handlers.append(console)

    # File handler (optional)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        ))
        handlers.append(file_handler)

    logging.basicConfig(
        level=getattr(logging, level.upper()),
        handlers=handlers
    )

    logger = logging.getLogger(service_name)
    logger.info(f"Logging initialized for {service_name} at {level} level")
    return logger
```

Use everywhere:

```python
# main.py
from utils.logging_config import setup_logging
logger = setup_logging("backend")
```

---

### H8: Scheduler Loop Has No Health Monitoring

**Severity**: HIGH
**Effort**: Medium (2-3 hours)
**Files**: `/Users/nicholasmparker/Projects/skylapse/backend/main.py` (lines 96-178)

**Problem**:
The core scheduler loop runs continuously but has no health monitoring:

- No heartbeat/pulse indicator
- No tracking of successful vs failed captures
- No metrics on schedule execution
- Cannot tell if loop is stuck or healthy
- Exception handling continues silently (line 176)

**Impact**:

- Silent failures: scheduler could be broken but service appears "up"
- No visibility into capture success rate
- Cannot alert on scheduler health
- Difficult to debug "why didn't it capture?"

**Recommended Fix**:
Add health tracking:

```python
class SchedulerHealth:
    def __init__(self):
        self.last_loop_time = None
        self.total_loops = 0
        self.successful_captures = 0
        self.failed_captures = 0
        self.last_error = None

    def record_loop(self):
        self.last_loop_time = datetime.now()
        self.total_loops += 1

    def record_capture(self, success: bool, error: Exception = None):
        if success:
            self.successful_captures += 1
        else:
            self.failed_captures += 1
            self.last_error = str(error)

    def is_healthy(self) -> bool:
        """Check if scheduler is healthy"""
        if not self.last_loop_time:
            return False
        # Loop should run at least every 60 seconds
        age = (datetime.now() - self.last_loop_time).seconds
        return age < 120  # 2 minutes grace period

    def get_stats(self) -> dict:
        return {
            "last_loop": self.last_loop_time.isoformat() if self.last_loop_time else None,
            "total_loops": self.total_loops,
            "successful_captures": self.successful_captures,
            "failed_captures": self.failed_captures,
            "success_rate": self.successful_captures / (self.successful_captures + self.failed_captures) if (self.successful_captures + self.failed_captures) > 0 else 0,
            "last_error": self.last_error,
            "is_healthy": self.is_healthy()
        }

# Add to app state
app.state.scheduler_health = SchedulerHealth()

# Add endpoint
@app.get("/health/scheduler")
async def get_scheduler_health(request: Request):
    health = request.app.state.scheduler_health
    return health.get_stats()
```

---

## MEDIUM Priority Issues

### M1: Config.get() Returns None for Missing Nested Keys

**Severity**: MEDIUM
**Effort**: Quick (1 hour)
**Files**: `/Users/nicholasmparker/Projects/skylapse/backend/config.py` (lines 131-153)

**Problem**:
`Config.get("key.nested", default)` returns None if intermediate key is missing, ignoring the default value.

Example:

```python
config.get("missing.nested.key", "default")  # Returns None, not "default"
```

**Impact**:

- Defaults don't work as expected
- Code defensively checks for None even when default provided
- Inconsistent with dict.get() behavior

**Recommended Fix**:

```python
def get(self, key: str, default: Any = None) -> Any:
    keys = key.split(".")
    value = self.config

    for k in keys:
        if not isinstance(value, dict):
            return default  # Not a dict, return default
        value = value.get(k)
        if value is None:
            return default  # Missing key, return default

    return value
```

---

### M2: No Tests for Transfer Service

**Severity**: MEDIUM
**Effort**: Medium (3-4 hours)
**Files**: `/Users/nicholasmparker/Projects/skylapse/backend/services/transfer.py`

**Problem**:
Transfer service has zero test coverage:

- No unit tests for rsync command building
- No integration tests for transfer flow
- No mocking of Pi connectivity
- Cannot validate transfer logic without real Pi

**Impact**:

- Regressions in transfer logic go undetected
- Cannot safely refactor
- No confidence in changes

**Recommended Fix**:
Create test suite:

```python
# backend/services/test_transfer.py
import pytest
from unittest.mock import Mock, patch
from services.transfer import run_rsync_transfer, cleanup_old_images_on_pi

def test_rsync_command_construction():
    """Test rsync command is built correctly"""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        result = run_rsync_transfer()

        # Verify rsync was called with correct args
        call_args = mock_run.call_args[0][0]
        assert "rsync" in call_args
        assert "-avh" in call_args
        assert "--progress" in call_args

def test_transfer_retry_on_failure():
    """Test transfer retries on failure"""
    # Test retry logic

def test_cleanup_respects_retention_days():
    """Test cleanup only deletes old files"""
    # Test cleanup logic
```

---

### M3: Inconsistent Use of Async/Await

**Severity**: MEDIUM
**Effort**: Medium (2-3 hours)
**Files**: Multiple

**Problem**:
Mixing async and sync code inconsistently:

- `main.py` has async endpoints but sync helper functions
- `exposure.py` has async `calculate_settings()` but sync `_apply_profile_settings()`
- `transfer.py` is entirely synchronous (uses subprocess.run not asyncio.subprocess)

**Impact**:

- Blocking calls in async context hurt performance
- Mixing paradigms is confusing
- Cannot use concurrent operations where beneficial

**Recommended Fix**:
Audit and standardize:

1. Make file I/O async where beneficial
2. Use `asyncio.subprocess` in transfer service
3. Document which parts must be sync (picamera2)
4. Use `asyncio.to_thread()` for unavoidable blocking

---

### M4: Magic Numbers in Scheduler Loop

**Severity**: MEDIUM
**Effort**: Quick (30 minutes)
**Files**: `/Users/nicholasmparker/Projects/skylapse/backend/main.py` (lines 118, 157, 173, 177)

**Problem**:
Hardcoded numbers with no explanation:

```python
profiles = ["a", "b", "c", "d", "e", "f"]  # Line 118
await asyncio.sleep(0.5)  # Line 157 - why 0.5?
min_interval = min((...), default=30)  # Line 164 - why 30?
await asyncio.sleep(30)  # Line 177 - why 30?
```

**Impact**:

- Cannot easily tune scheduler behavior
- Numbers should be configurable
- No documentation of why these values

**Recommended Fix**:
Extract to constants:

```python
# Constants at top of file
PROFILES = ["a", "b", "c", "d", "e", "f"]
INTER_PROFILE_DELAY_SECONDS = 0.5  # Delay between profile captures (camera settling)
DEFAULT_SCHEDULE_INTERVAL = 30  # Default capture interval
ERROR_RETRY_DELAY = 30  # Delay before retrying after error

# Use in code
for profile in PROFILES:
    # ...
    await asyncio.sleep(INTER_PROFILE_DELAY_SECONDS)
```

---

### M5: No Input Sanitization for File Paths

**Severity**: MEDIUM
**Effort**: Quick (1 hour)
**Files**:

- `/Users/nicholasmparker/Projects/skylapse/pi/main.py` (lines 636-726)
- Multiple image serving endpoints

**Problem**:
Profile parameter used directly in path construction:

```python
@app.get("/images/profile-{profile}/latest.jpg")
async def get_latest_image(profile: str):
    profile_dir = home_dir / "skylapse-images" / f"profile-{profile}"
```

Issues:

- No validation of `profile` parameter
- Path traversal vulnerability: `profile="../../../etc/passwd"`
- Could access arbitrary files

**Impact**:

- Security vulnerability (path traversal)
- Could expose sensitive files
- Should validate profile is in allowed set

**Recommended Fix**:

```python
from profile_schema import ProfileID  # H3 fix

@app.get("/images/profile-{profile}/latest.jpg")
async def get_latest_image(profile: str):
    # Validate profile is in allowed set
    try:
        profile_enum = ProfileID(profile)
    except ValueError:
        raise HTTPException(400, f"Invalid profile: {profile}")

    # Use validated enum value
    profile_dir = home_dir / "skylapse-images" / f"profile-{profile_enum.value}"

    # Additional check: ensure path is within images directory
    if not profile_dir.resolve().is_relative_to(home_dir / "skylapse-images"):
        raise HTTPException(403, "Path traversal detected")
```

---

### M6: Verbose Logging of Control Points

**Severity**: MEDIUM
**Effort**: Quick (30 minutes)
**Files**: `/Users/nicholasmparker/Projects/skylapse/backend/exposure.py` (lines 242-304)

**Problem**:
WB curve control points are 63 lines of hardcoded lists. This clutters the code and makes it hard to see the actual logic.

**Recommended Fix**:
Move to separate data file:

```python
# backend/wb_curves.json
{
  "balanced": [
    [10000, 5500],
    [8000, 5500],
    ...
  ],
  "conservative": [...],
  "warm": [...]
}

# Load in exposure.py
with open("wb_curves.json") as f:
    WB_CURVES = json.load(f)
```

---

### M7: Camera Initialization Side Effects at Module Load

**Severity**: MEDIUM
**Effort**: Quick (1 hour)
**Files**: `/Users/nicholasmparker/Projects/skylapse/pi/main.py` (line 114)

**Problem**:
Camera is initialized at module load time:

```python
# Line 114
initialize_camera()  # Called at import time!
```

**Impact**:

- Cannot import module without initializing camera
- Testing requires mocking camera at import time
- Cannot control when initialization happens
- Side effects during imports are anti-pattern

**Recommended Fix**:
Use FastAPI lifespan:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    initialize_camera()  # Initialize here, not at module load
    yield
    # Shutdown
    if camera:
        camera.close()

app = FastAPI(lifespan=lifespan)
```

---

## LOW Priority Issues

### L1: No Type Hints on Several Functions

**Severity**: LOW
**Effort**: Quick (1 hour)
**Files**: `/Users/nicholasmparker/Projects/skylapse/backend/services/transfer.py`

**Problem**:
Transfer service functions lack type hints:

```python
def run_rsync_transfer():  # Should be -> bool
def get_transfer_stats():  # Should be -> Tuple[int, int]
```

**Recommended Fix**: Add type hints throughout.

---

### L2: Inconsistent Docstring Format

**Severity**: LOW
**Effort**: Quick (1 hour)
**Files**: Multiple

**Problem**:
Mix of Google-style, NumPy-style, and no docstrings.

**Recommended Fix**: Standardize on Google-style docstrings.

---

### L3: No Docker Health Checks Defined

**Severity**: LOW
**Effort**: Quick (30 minutes)
**Files**: `/Users/nicholasmparker/Projects/skylapse/docker-compose.yml`

**Problem**:
No health checks in docker-compose:

```yaml
services:
  backend:
    # No healthcheck defined
```

**Recommended Fix**:

```yaml
services:
  backend:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8082/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

---

### L4: Version Information Not Exposed

**Severity**: LOW
**Effort**: Quick (30 minutes)
**Files**: Multiple

**Problem**:
No way to query service version from API.

**Recommended Fix**:
Add version endpoint:

```python
@app.get("/version")
async def get_version():
    return {
        "service": "backend",
        "version": "2.0.0",
        "commit": os.getenv("GIT_COMMIT", "unknown")
    }
```

---

## Positive Observations

**Good Practices Observed**:

1. Clear separation of concerns (exposure, solar, config)
2. Pydantic validation on API endpoints
3. Atomic config saves using temp file pattern
4. Comprehensive docstrings in key modules
5. ScheduleType enum eliminates magic strings
6. Docker-based architecture with proper volumes
7. Profile execution architecture is well-designed
8. Error handling in most critical paths

---

## Recommended Implementation Order

### Phase 1: Critical Fixes (Week 1)

1. **C1**: Extract WB curve logic to shared module (4-6 hours)
2. **C2**: Create URL builder utility (3-4 hours)
3. **H1**: Centralize Pi host configuration (1 hour)
4. **H2**: Add error handling to transfer service (2-3 hours)

**Total Phase 1**: ~12-15 hours (2 days)

### Phase 2: High Priority (Week 2)

5. **H3**: Shared profile validation (2-3 hours)
6. **H4**: Extract parse_time_range utility (30 min)
7. **H5**: Validate Docker volumes (2 hours)
8. **H6**: Centralize profile metadata (30 min)
9. **H7**: Centralized logging config (2 hours)
10. **H8**: Scheduler health monitoring (2-3 hours)

**Total Phase 2**: ~10-12 hours (1.5 days)

### Phase 3: Medium Priority (Week 3)

11. **M1-M7**: Address medium issues as time permits

**Total Phase 3**: ~12-15 hours (2 days)

---

## Impact on Sprint Goals

**Current Sprint Deliverables**: All achievable with these fixes

- Transfer service works (needs H2 error handling)
- Docker volumes work (needs H5 validation)
- Hybrid image serving works (needs C2 URL builder)
- Profile deployment works (needs H3 validation)

**Blockers**: None of these issues block current functionality.

**Risk Assessment**:

- **HIGH RISK**: C2 (URL hardcoding) could cause production deployment issues
- **MEDIUM RISK**: H2 (transfer errors) could cause silent data loss
- **LOW RISK**: Most other issues are code quality/maintainability

---

## Testing Strategy

After implementing fixes, verify with:

1. **Unit Tests** (add/update):

   - WB curve interpolation
   - URL builder
   - Profile validation
   - Time parsing

2. **Integration Tests**:

   - Transfer service with retry
   - Scheduler health monitoring
   - Profile deployment end-to-end

3. **Docker Tests**:
   - Volume mount validation
   - Service health checks
   - Cross-service communication

---

## Metrics Tracking

Recommend tracking these metrics post-fix:

- Code duplication percentage (expect 15% reduction)
- Test coverage (target: 75%+)
- Configuration errors at startup (expect reduction)
- Transfer success rate (should be visible)

---

## Conclusion

The Skylapse codebase is in **good shape overall** with solid architecture and clear separation of concerns. The identified issues are primarily:

1. **DRY violations** (WB curves, validation, URLs)
2. **Configuration scattered** (Pi host, profile metadata)
3. **Missing observability** (health checks, metrics)
4. **Incomplete error handling** (transfer service)

All issues are fixable within 3-4 days of focused work, and **none block current sprint goals**. The recommended phased approach allows for incremental improvement while maintaining velocity.

**Priority**: Start with Critical issues (C1, C2) as they have the highest impact on maintainability and production readiness.
