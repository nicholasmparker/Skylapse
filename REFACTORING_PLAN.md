# Skylapse Technical Debt Refactoring Plan

## Overview

This document outlines the plan to eliminate technical debt identified in the codebase review. Work is organized into phases with estimated effort and priority.

## Executive Summary

**Total Issues Identified:** 28 (from GONZO review) + 5 (from embarrassing code review)
**Total Estimated Effort:** ~30-35 hours
**Status:** Phase 1 complete (6 quick wins, ~1.5 hours)

---

## Phase 1: Quick Wins ✅ COMPLETE

**Status:** Merged to main
**Effort:** 1.5 hours
**Branch:** `tech-debt/refactor-review`

### Completed
1. ✅ Fixed duplicate `/latest-image` endpoint (renamed to `serve_latest_image`)
2. ✅ Created `CameraControls` class with semantic constants
3. ✅ Extracted path helpers (`_get_profile_dir`, `_get_focus_test_dir`)
4. ✅ Added validation to profile executor for schedule_type
5. ✅ Removed duplicate imports in `pi/main.py`
6. ✅ Created `VALID_ISO_VALUES` constant (eliminated duplication)

**Impact:** Improved code readability, eliminated 8+ instances of duplication, replaced magic numbers with semantic constants.

---

## Phase 2: God Function Refactoring (HIGH PRIORITY)

**Estimated Effort:** 6-8 hours
**Risk Level:** Medium (extensive testing required)
**Priority:** HIGH

### 2.1 Break Down `generate_timelapse()` (282 lines → ~50 lines)

**File:** `backend/tasks.py:148-429`
**Embarrassment Level:** 10/10 - Most embarrassing code in codebase

**Current Structure:**
```python
def generate_timelapse(...):  # 282 lines of chaos
    # Database queries
    # File discovery
    # Quality preset selection
    # FFmpeg command building (2 modes!)
    # Filter construction
    # Subprocess execution
    # Thumbnail generation
    # Database recording
    # Error handling
```

**Proposed Refactoring:**

```python
# New classes
class TimelapseSession:
    def __init__(self, session_id, profile, schedule, date)
    def get_images(self) -> List[Path]
    def get_filters(self) -> List[str]
    def record(self, result: VideoResult)
    def error(self, message: str) -> dict

class VideoBuilder:
    def __init__(self, images, fps, quality, quality_tier)
    def add_filters(self, filters: List[str])
    def build(self) -> VideoResult

class VideoResult:
    def generate_thumbnail(self)
    def to_dict(self) -> dict

# Refactored main function
def generate_timelapse(...) -> dict:
    """Coordinate timelapse generation pipeline."""
    session = TimelapseSession(session_id, profile, schedule, date)

    images = session.get_images()
    if not images:
        return session.error("No images found")

    video = VideoBuilder(images, fps, quality, quality_tier)
    video.add_filters(session.get_filters())

    result = video.build()
    result.generate_thumbnail()
    session.record(result)

    return result.to_dict()
```

**Sub-tasks:**
1. Extract `TimelapseSession` class (database + metadata)
2. Extract `QualityPreset` class (quality settings)
3. Extract `FFmpegCommandBuilder` class
4. Extract `VideoFilterBuilder` class
5. Extract `ThumbnailGenerator` class
6. Refactor main function to orchestrate
7. Write unit tests for each class
8. Integration test full pipeline

**Estimated Effort:** 4 hours

---

### 2.2 Break Down `capture_photo()` (232 lines → ~40 lines)

**File:** `pi/main.py:371-602`
**Embarrassment Level:** 9/10

**Current Structure:**
```python
async def capture_photo(settings):  # 232 lines
    # Backend authorization
    # Profile execution mode
    # Settings mutation
    # Mock mode check
    # Directory creation
    # Bracketing vs single shot
    # Control building (5-6 levels of nesting!)
    # Focus management
    # Camera capture
```

**Proposed Refactoring:**

```python
def _validate_backend_authorization(settings: CaptureSettings) -> None:
    """Raise HTTPException if backend not authorized."""

def _apply_profile_settings(settings: CaptureSettings) -> CaptureSettings:
    """Calculate settings from deployed profile."""

def _build_camera_controls(settings: CaptureSettings) -> Dict[str, Any]:
    """Build camera control dictionary."""

def _capture_bracketed(settings: CaptureSettings) -> CaptureResponse:
    """Capture HDR bracket sequence."""

def _capture_single(settings: CaptureSettings) -> CaptureResponse:
    """Capture single photo."""

async def capture_photo(settings: CaptureSettings) -> CaptureResponse:
    """Capture photo with provided settings (orchestrator)."""
    _validate_backend_authorization(settings)

    if settings.use_deployed_profile:
        settings = _apply_profile_settings(settings)

    if USE_MOCK_CAMERA:
        return _mock_capture()

    if settings.bracket_count > 1:
        return _capture_bracketed(settings)

    return _capture_single(settings)
```

**Sub-tasks:**
1. Extract `_validate_backend_authorization()`
2. Extract `_apply_profile_settings()`
3. Extract `_build_camera_controls()` (split from main logic)
4. Extract `_capture_bracketed()`
5. Extract `_capture_single()`
6. Refactor main function
7. Test all capture modes

**Estimated Effort:** 2.5 hours

---

### 2.3 Simplify `scheduler_loop()` (189 lines → ~80 lines)

**File:** `backend/main.py:145-333`
**Embarrassment Level:** 8/10

**Proposed Refactoring:**

```python
def _check_schedule_window(schedule_name, schedule_config):
    """Check if schedule is currently active."""

def _handle_schedule_end(schedule_name, schedule_profiles, date_str):
    """Handle session completion and job enqueueing."""

def _trigger_capture(schedule_name, schedule_config, schedule_profiles):
    """Trigger capture for active schedule."""

async def scheduler_loop(app: FastAPI):
    """Main scheduling loop."""
    while True:
        try:
            schedules = config.get_schedules()

            for schedule_name, schedule_config in schedules.items():
                if not schedule_config.get("enabled", False):
                    continue

                is_active = _check_schedule_window(schedule_name, schedule_config)

                if was_active and not is_active:
                    _handle_schedule_end(schedule_name, ...)

                if is_active:
                    _trigger_capture(schedule_name, ...)

                _update_was_active_state(schedule_name, is_active)

            await asyncio.sleep(SCHEDULER_INTERVAL)
        except Exception as e:
            logger.error(f"Scheduler error: {e}", exc_info=True)
            await asyncio.sleep(SCHEDULER_INTERVAL)
```

**Estimated Effort:** 1.5 hours

---

## Phase 3: Database Transaction Pattern

**Estimated Effort:** 1 hour
**Priority:** HIGH (prevents future bugs)

### 3.1 Extract Database Transaction Context Manager

**File:** `backend/database.py`

**Current Pattern (repeated 3 times):**
```python
try:
    conn.execute("BEGIN IMMEDIATE")
    # ... operations
    conn.commit()
except Exception as e:
    conn.rollback()
    logger.error(...)
    raise
```

**Proposed:**
```python
@contextmanager
def _transaction(self, conn):
    """Context manager for database transactions with automatic rollback."""
    try:
        conn.execute("BEGIN IMMEDIATE")
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Transaction failed: {e}", exc_info=True)
        raise

# Usage:
def record_capture(self, session_id, filename, timestamp, settings):
    with self._get_connection() as conn:
        with self._transaction(conn):
            conn.execute("INSERT INTO captures ...")
            self._update_session_stats(conn, session_id, ...)
```

---

## Phase 4: Eliminate Copy-Paste Duplication

**Estimated Effort:** 2 hours
**Priority:** MEDIUM

### 4.1 Create Session ID Builder

**Current:** Same logic in 4 places
```python
session_id = f"{profile}_{date.replace('-', '')}_{schedule}"
```

**Proposed:**
```python
# In database.py or utils.py
def build_session_id(profile: str, date: str, schedule: str) -> str:
    """
    Construct standardized session ID.

    Format: {profile}_{YYYYMMDD}_{schedule}
    Example: a_20251002_sunset
    """
    date_compact = date.replace('-', '')
    return f"{profile}_{date_compact}_{schedule}"
```

**Locations to replace:**
1. `backend/main.py:237`
2. `backend/database.py:208`
3. `backend/database.py:465`
4. `backend/database.py:491`

---

### 4.2 Extract Duplicate Lux-Based WB Calculation

**Files:** `backend/exposure.py`, `pi/profile_executor.py`

Both call `interpolate_wb_from_lux()` but have different surrounding logic. Consolidate to single shared helper.

---

### 4.3 Extract `datetime.utcnow().isoformat()` Pattern

**Current:** Appears 7+ times in `backend/database.py`

**Proposed:**
```python
def now_iso() -> str:
    """Get current UTC timestamp in ISO format."""
    return datetime.utcnow().isoformat()
```

---

## Phase 5: Error Handling & Robustness

**Estimated Effort:** 2 hours
**Priority:** MEDIUM

### 5.1 Fix Bare `except:` Blocks

**Location:** `backend/main.py:863-864`

**Current:**
```python
except:  # Catches EVERYTHING!
    pi_status = "offline"
```

**Proposed:**
```python
except (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError) as e:
    logger.debug(f"Pi health check failed: {e}")
    pi_status = "offline"
except Exception as e:
    logger.error(f"Unexpected error checking Pi health: {e}", exc_info=True)
    pi_status = "unknown"
```

---

### 5.2 Add Exposure History Cleanup

**File:** `backend/exposure.py:19-70`

**Issue:** ExposureHistory grows indefinitely (memory leak)

**Proposed:**
```python
class ExposureHistory:
    def __init__(self, max_sessions: int = 50):
        self._history: Dict[str, deque] = {}
        self._max_sessions = max_sessions
        self._session_order: deque = deque(maxlen=max_sessions)

    def add_frame(self, session_id: str, settings: Dict):
        if session_id not in self._history:
            self._session_order.append(session_id)

            # Evict oldest session if limit exceeded
            if len(self._history) > self._max_sessions:
                oldest = self._session_order[0]
                if oldest in self._history:
                    del self._history[oldest]

        # ... rest of logic
```

---

## Phase 6: Code Quality & Consistency

**Estimated Effort:** 4 hours
**Priority:** LOW

### 6.1 Standardize Logging Format

Create `logger_utils.py` with consistent emoji prefixes:
```python
class LogPrefix:
    SUCCESS = "✓"
    CAPTURE = "📸"
    PROFILE = "🎯"
    WB_ADJUST = "🎨"
    VIDEO = "🎬"
    METER = "📊"
    SECURITY = "🔒"

def log_capture(logger, message: str):
    logger.info(f"{LogPrefix.CAPTURE} {message}")
```

---

### 6.2 Extract Quality Presets to Dataclass

**File:** `backend/tasks.py:226-242`

**Current:** Nested dictionaries

**Proposed:**
```python
@dataclass
class QualityPreset:
    crf: str
    preset: str
    pixel_format: str
    description: str

QUALITY_PRESETS = {
    "preview": {
        "low": QualityPreset("28", "fast", "yuv420p", "Low quality preview"),
        "medium": QualityPreset("23", "medium", "yuv420p", "Medium quality"),
        # ...
    }
}
```

---

### 6.3 Add Missing Type Hints

Files needing type hints:
- `parse_shutter_speed()` (pi/main.py:232)
- `_update_session_stats()` (database.py:311)
- Various helper functions

---

### 6.4 Consistent Variable Naming

Standardize date variable names:
- `date_iso` for "YYYY-MM-DD"
- `date_compact` for "YYYYMMDD"
- `date_dt` for datetime objects
- `timestamp_str` for ISO timestamps

---

## Phase 7: Performance & Architecture

**Estimated Effort:** Variable
**Priority:** LOW (future work)

### 7.1 Decouple Config from Exposure

**File:** `backend/exposure.py:365`

Current: Imports Config inside function (circular dependency smell)

Proposed: Pass profile data as parameter instead of loading inside function

---

### 7.2 Long Parameter Lists

**Example:** `record_timelapse()` has 11 parameters

**Proposed:** Use dataclass for metadata:
```python
@dataclass
class TimelapseMetadata:
    session_id: str
    filename: str
    file_path: str
    profile: str
    schedule: str
    date: str
    # ... etc

def record_timelapse(self, metadata: TimelapseMetadata):
    # Use metadata.session_id, etc.
```

---

## Testing Strategy

### For Each Phase:

1. **Unit Tests**
   - Test extracted functions in isolation
   - Mock dependencies
   - Test edge cases

2. **Integration Tests**
   - Test refactored code with real dependencies
   - Verify behavior unchanged

3. **Regression Tests**
   - Run existing Playwright tests
   - Manual testing of critical paths
   - Capture photos, generate timelapses

4. **Performance Testing**
   - Ensure refactoring doesn't degrade performance
   - Benchmark before/after

---

## Deployment Strategy

### For Each Phase:

1. Create feature branch (`tech-debt/phase-X`)
2. Implement refactorings
3. Run QA validation (automated + manual)
4. Code review
5. Merge to main
6. Deploy to laptop (dev environment)
7. Test with real Pi captures
8. Deploy to dagon (production)
9. Monitor for issues

---

## Risk Mitigation

### High-Risk Refactorings:
- `generate_timelapse()` - Core video generation
- `capture_photo()` - Core capture logic
- `scheduler_loop()` - Orchestration brain

### Mitigation:
1. **Extensive testing** before deployment
2. **Deploy to dev first**, test thoroughly
3. **Monitor production** after deployment
4. **Quick rollback plan** (git revert)
5. **Feature flags** for new code paths (if needed)

---

## Success Metrics

### Code Quality
- **Lines of Code:** Reduce god functions by 60-70%
- **Cyclomatic Complexity:** Reduce from 15+ to <10 per function
- **Duplication:** Eliminate all copy-paste duplication
- **Test Coverage:** Increase to 80%+

### Maintainability
- **Time to Add Feature:** Reduce by 30%
- **Bug Fix Time:** Reduce by 40%
- **Onboarding Time:** New developers understand faster

### Performance
- **No Regression:** Maintain current performance
- **Potential Gains:** Better separation may enable optimization

---

## Timeline (Estimated)

| Phase | Effort | Dependency | Status |
|-------|--------|------------|--------|
| Phase 1 | 1.5h | None | ✅ Complete |
| Phase 2 | 8h | None | 📋 Planned |
| Phase 3 | 1h | None | 📋 Planned |
| Phase 4 | 2h | None | 📋 Planned |
| Phase 5 | 2h | None | 📋 Planned |
| Phase 6 | 4h | None | 📋 Planned |
| Phase 7 | Variable | Future | 📋 Planned |

**Total Estimated Effort:** 18.5+ hours (excluding Phase 7)

---

## Next Steps

1. ✅ Complete Phase 1 (DONE)
2. Review and approve this plan
3. Schedule Phase 2 work (god function refactoring)
4. Create branch and begin implementation
5. QA validation and testing
6. Deploy to production

---

## Notes

- This plan is a living document - adjust as needed
- Prioritize high-impact, low-risk changes first
- Don't refactor for the sake of refactoring - focus on maintainability
- Get user feedback before major architectural changes

---

**Document Version:** 1.0
**Created:** 2025-10-08
**Last Updated:** 2025-10-08
**Author:** Claude Code (Technical Debt Review)
