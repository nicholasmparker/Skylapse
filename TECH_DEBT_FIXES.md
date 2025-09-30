# Technical Debt Fixes - Checklist

**Principles**: SIMPLE. NOT OVERENGINEERED. MAINTAINABLE.
**Rule**: Only implement what's on this list. No extra features without discussion.

---

## CRITICAL - Do These First

### [ ] C1. Fix Global State in Backend Main

**File**: `backend/main.py`
**Problem**: Global variables initialized as `None`, causes testing/type issues
**Simple Fix**:

```python
# Remove lines 33-37 (global None variables)
# Move initialization inside lifespan function
# Store in app.state instead of globals
```

**Checklist**:

- [ ] Delete global `config: Config = None` lines
- [ ] Initialize Config/SolarCalculator/ExposureCalculator in lifespan
- [ ] Store in `app.state.config`, `app.state.solar_calc`, `app.state.exposure_calc`
- [ ] Update endpoints to use `request.app.state.config` instead of global
- [ ] Test: Backend starts without errors
- [ ] Test: `/status` endpoint returns correct data

---

### [ ] C2. Fix Profile Counter Incrementing on Failures

**File**: `backend/main.py`
**Problem**: Profile counter increments even when capture fails, breaking rotation
**Simple Fix**:

```python
# Line 135: Only increment profile_counter if success == True
# Add counter before capture, only increment if successful
```

**Checklist**:

- [ ] Move `profile_counter += 1` AFTER success check
- [ ] Only increment if `success == True`
- [ ] Test: Simulate Pi offline, verify counter doesn't increment
- [ ] Test: Profile rotation stays correct after failures

---

### [ ] C3. Use Config Values for Schedule Windows

**File**: `backend/solar.py`
**Problem**: Hardcoded -30min/+60min, ignores config `offset_minutes` and `duration_minutes`
**Simple Fix**:

```python
# Lines 120-131: Read offset/duration from schedule_config parameter
# Pass schedule_config to get_schedule_window() from main.py
```

**Checklist**:

- [ ] Add `schedule_config: dict` parameter to `get_schedule_window()`
- [ ] Read `offset_minutes` from config (default -30)
- [ ] Read `duration_minutes` from config (default 60)
- [ ] Calculate: `start = sunrise + timedelta(minutes=offset)`
- [ ] Calculate: `end = start + timedelta(minutes=duration)`
- [ ] Update call sites in main.py to pass schedule_config
- [ ] Test: Change offset to -15, verify window shifts
- [ ] Test: Change duration to 30, verify window shortens

---

## HIGH PRIORITY - Do These Next

### [ ] H1. Make Config Saving Atomic

**File**: `backend/config.py`
**Problem**: Config can get corrupted if process crashes during save
**Simple Fix**:

```python
# Write to temp file first, then rename (atomic operation)
import tempfile, shutil
# temp_fd, temp_path = tempfile.mkstemp(dir=self.config_path.parent)
# write to temp_path, then shutil.move(temp_path, self.config_path)
```

**Checklist**:

- [ ] Import `tempfile` and `shutil`
- [ ] Create temp file in same directory as config.json
- [ ] Write JSON to temp file
- [ ] Use `shutil.move()` to atomically replace config.json
- [ ] Add try/except to clean up temp file on error
- [ ] Test: Verify config.json not corrupted after simulated crash

---

### [ ] H2. Add Retry Logic for Pi Captures

**File**: `backend/main.py`
**Problem**: Single network failure = lost capture forever
**Simple Fix**:

```python
# Add simple retry loop (3 attempts) with 2-second delays
# Only retry on timeout/connection errors, not HTTP errors
```

**Checklist**:

- [ ] Add `for attempt in range(3):` loop around httpx.post()
- [ ] Catch `httpx.TimeoutException` and `httpx.ConnectError`
- [ ] Sleep 2 seconds between retries
- [ ] Don't retry on HTTP 4xx/5xx errors (Pi rejection)
- [ ] Log retry attempts
- [ ] Test: Simulate network glitch, verify retries succeed

---

### [ ] H3. Move Camera Init to Lifespan

**File**: `pi/main.py`
**Problem**: Camera initialized at module load, can't test without hardware
**Simple Fix**:

```python
# Don't call initialize_camera() at module level (line 95)
# Call it inside @asynccontextmanager lifespan
```

**Checklist**:

- [ ] Remove `initialize_camera()` call from line 95
- [ ] Create `@asynccontextmanager async def lifespan(app: FastAPI):`
- [ ] Call `initialize_camera()` in lifespan startup
- [ ] Add camera cleanup in lifespan shutdown
- [ ] Update FastAPI app creation: `app = FastAPI(lifespan=lifespan)`
- [ ] Test: Import module without camera, no crash
- [ ] Test: Service starts and camera initializes

---

### [ ] H4. Remove Duplicate Time Parsing

**File**: `backend/main.py`
**Problem**: Same time parsing code in lines 183-199 and 293-306
**Simple Fix**:

```python
# Create parse_time_range(schedule_config, schedule_name) function
# Return (start_time, end_time) or None if invalid
# Use in both places
```

**Checklist**:

- [ ] Create `parse_time_range()` function (15 lines)
- [ ] Replace lines 183-199 with function call
- [ ] Replace lines 293-306 with function call
- [ ] Test: Invalid time format returns None
- [ ] Test: Valid times return correct tuple

---

### [ ] H5. Validate Bracket Parameters

**File**: `pi/main.py`
**Problem**: bracket_ev list can be wrong length, no validation
**Simple Fix**:

```python
# Add Pydantic @validator to CaptureSettings
# Check len(bracket_ev) >= bracket_count when bracket_count > 1
```

**Checklist**:

- [ ] Add `@validator("bracket_ev")` to CaptureSettings class
- [ ] Check: if bracket_count > 1, bracket_ev must exist and have enough values
- [ ] Check: EV values are floats in range -2.0 to +2.0
- [ ] Test: Send invalid bracket config, verify 400 error
- [ ] Test: Send valid bracket config, verify success

---

### [ ] H6. Fix Return Type Hint in ExposureCalculator

**File**: `backend/exposure.py`
**Problem**: `Dict[str, any]` should be `Dict[str, Any]` (capital A)
**Simple Fix**:

```python
# Line 29: Change 'any' to 'Any'
# Add 'from typing import Any' import
```

**Checklist**:

- [ ] Change `Dict[str, any]` to `Dict[str, Any]`
- [ ] Verify `from typing import Any` imported
- [ ] Test: Run type checker (no errors)

---

## MEDIUM PRIORITY - Nice to Have

### [ ] M1. Limit Solar Calculator Cache Size

**File**: `backend/solar.py`
**Problem**: Cache grows forever (1 entry per day)
**Simple Fix**:

```python
# Keep only last 7 days
# When adding new entry, remove oldest if len > 7
```

**Checklist**:

- [ ] Change `self._cache = {}` to `self._cache = OrderedDict()`
- [ ] Import `from collections import OrderedDict`
- [ ] After adding to cache, check if `len(self._cache) > 7`
- [ ] If too large: `self._cache.popitem(last=False)`
- [ ] Test: Run for 10 days, verify cache stays at 7 entries

---

### [ ] M2. Check Pi Connectivity on Backend Startup

**File**: `backend/main.py`
**Problem**: Backend starts even if Pi unreachable, fails silently later
**Simple Fix**:

```python
# In lifespan startup, ping Pi /health endpoint
# Log warning (not error) if unreachable
```

**Checklist**:

- [ ] After loading config in lifespan, get Pi URL
- [ ] Try GET /health with 5-second timeout
- [ ] If fails: log warning (don't crash)
- [ ] Test: Start backend with Pi offline, verify warning logged
- [ ] Test: Backend continues running despite unreachable Pi

---

### [ ] M3. Make Sleep Intervals Configurable

**File**: `backend/main.py`
**Problem**: 30-second sleep hardcoded in multiple places
**Simple Fix**:

```python
# Add "scheduler": {"check_interval_seconds": 30} to default config
# Read from config instead of hardcoding
```

**Checklist**:

- [ ] Add scheduler config section to default_config in config.py
- [ ] Read `check_interval = config.get("scheduler.check_interval_seconds", 30)`
- [ ] Replace hardcoded `await asyncio.sleep(30)` with variable
- [ ] Test: Set interval to 5 seconds, verify faster checking

---

### [ ] M4. Check Disk Space Before Capture

**File**: `pi/main.py`
**Problem**: Could fill disk and crash service
**Simple Fix**:

```python
# Before capture, check shutil.disk_usage()
# Raise error if < 100MB free
```

**Checklist**:

- [ ] Import `shutil`
- [ ] Check `shutil.disk_usage(output_dir).free`
- [ ] Raise HTTPException if less than 100MB (100 _ 1024 _ 1024 bytes)
- [ ] Test: Fill disk to 50MB, verify capture fails with clear error

---

### [ ] M6. Add Docker Restart Policies

**File**: `docker-compose.yml`
**Problem**: Services don't auto-restart after crashes
**Simple Fix**:

```yaml
# Add "restart: unless-stopped" to each service
```

**Checklist**:

- [ ] Add `restart: unless-stopped` to backend service
- [ ] Add `restart: unless-stopped` to frontend service (if used)
- [ ] Add `restart: unless-stopped` to processing service (if used)
- [ ] Test: Kill container, verify auto-restart

---

### [ ] M7. Add Docker Log Rotation

**File**: `docker-compose.yml`
**Problem**: Logs grow unbounded, can fill disk
**Simple Fix**:

```yaml
# Add logging section to each service
# max-size: "10m", max-file: "3"
```

**Checklist**:

- [ ] Add logging config to backend service
- [ ] Set max-size: "10m" and max-file: "3"
- [ ] Test: Verify old logs rotate out after 30MB total

---

## LOW PRIORITY - Polish

### [ ] L2. Remove Example Code from config.py

**File**: `backend/config.py`
**Problem**: `if __name__ == "__main__"` test code in production file
**Simple Fix**:

```python
# Delete lines 168-189 (example usage section)
```

**Checklist**:

- [ ] Delete example code block
- [ ] Verify config.py still imports and works

---

### [ ] L4. Add Type Hint to parse_shutter_speed

**File**: `pi/main.py`
**Problem**: Missing return type hint
**Simple Fix**:

```python
# Line 143: def parse_shutter_speed(shutter_str: str) -> int:
```

**Checklist**:

- [ ] Add `-> int` return type
- [ ] Verify no type checker errors

---

## Pre-Commit Hooks

### [ ] Setup Pre-Commit Config

**File**: `.pre-commit-config.yaml` (create new file)
**Problem**: Hook installed but no config file
**Options**:

1. **Remove hook**: `pre-commit uninstall` (simplest)
2. **Add minimal config**: Black formatter only
3. **Discuss**: What checks do you want?

**If keeping, minimal config**:

```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
        language_version: python3.11
```

**Checklist**:

- [ ] Decide: Keep or remove pre-commit?
- [ ] If keep: Create .pre-commit-config.yaml with Black only
- [ ] If remove: Run `pre-commit uninstall`
- [ ] Test: Commit works without errors

---

## Testing Strategy

### For Each Fix:

1. Make the change
2. Start backend: `docker-compose up backend`
3. Check logs for errors
4. Test the specific functionality (curl commands or manual verification)
5. Commit with descriptive message

### No New Test Infrastructure Required

- Manual testing is sufficient for these fixes
- Each checklist item has simple "Test:" steps
- Future: Add pytest when doing larger refactors

---

## Notes

- **Do fixes in order** (Critical → High → Medium → Low)
- **One PR per section** (all Critical fixes together, all High together, etc.)
- **Keep it simple** - no fancy patterns unless discussed
- **Each fix is ~30 minutes to 2 hours** of focused work
- **Total effort: ~15-20 hours** for Critical + High priority items
