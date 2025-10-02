# Profile Execution Implementation

## Overview

The Pi capture service now supports **three capture modes** for maximum flexibility:

1. **Explicit Settings** (backward compatible) - Backend sends exact settings
2. **Deployed Profile** - Pi calculates settings autonomously from deployed profile
3. **Override Mode** - Profile execution with test overrides

## Implementation Status

### Completed Components

#### 1. Profile Executor (`profile_executor.py`)

- Loads and stores deployed profiles
- Calculates settings from profile + lux
- Interpolates adaptive WB from lux tables
- Handles schedule-specific overrides

#### 2. Profile Deployment Endpoints (`main.py`)

- `POST /profile/deploy` - Deploy profile snapshot
- `GET /profile/current` - Get deployed profile info
- `DELETE /profile/current` - Clear profile (revert to live mode)
- `/status` endpoint reports operational mode

#### 3. Enhanced Capture Endpoint (`main.py`)

- **New fields in CaptureSettings:**

  - `use_deployed_profile: bool` - Enable profile execution
  - `schedule_type: str` - Schedule name (sunrise/daytime/sunset)
  - `override: dict` - Override settings for testing

- **Mode selection logic:**
  ```python
  if settings.use_deployed_profile:
      # MODE 2/3: Calculate from profile
      profile_settings = profile_executor.calculate_settings(
          schedule_type, lux, override
      )
  else:
      # MODE 1: Use explicit settings (backward compatible)
  ```

## Usage Examples

### Mode 1: Explicit Settings (Current - Backward Compatible)

```python
POST /capture
{
    "iso": 400,
    "shutter_speed": "1/1000",
    "exposure_compensation": 0.7,
    "profile": "a"
}
```

**Behavior:** Pi uses exact settings provided by Backend. No profile needed.

### Mode 2: Deployed Profile Execution

```python
POST /capture
{
    "use_deployed_profile": true,
    "schedule_type": "sunset",
    "profile": "a"
}
```

**Behavior:**

1. Pi meters scene → gets lux value
2. Calls `profile_executor.calculate_settings("sunset", lux)`
3. Profile returns settings based on schedule + lux
4. Pi executes capture with calculated settings

### Mode 3: Override Mode (Testing)

```python
POST /capture
{
    "use_deployed_profile": true,
    "schedule_type": "sunset",
    "override": {
        "exposure_compensation": 0.9
    },
    "profile": "a"
}
```

**Behavior:**

1. Calculate base settings from profile
2. Apply override dict to final settings
3. Useful for testing profile tweaks without redeployment

## Error Handling

### No Profile Deployed

```python
POST /capture {"use_deployed_profile": true, ...}
→ 400 Bad Request
   "No profile deployed - cannot use profile execution mode"
```

### Missing Schedule Type

```python
# schedule_type defaults to "daytime" if omitted
POST /capture {"use_deployed_profile": true}
→ Uses "daytime" schedule
```

### ISO=0 Auto Mode

```python
# ISO=0 still works with explicit settings
POST /capture {"iso": 0, "shutter_speed": "1/500", ...}
→ Camera uses auto-exposure
```

## Logging

The implementation includes detailed logging:

```
# Profile mode
🎯 Profile execution mode: schedule_type=sunset
📸 Profile-calculated settings: ISO 400, shutter 1/1000, EV+0.7, lux=850

# Explicit mode
📸 Explicit settings mode: ISO 400, shutter 1/1000, EV+0.7

# Profile executor
🎯 Profile execution: profile-abc123 for sunset, lux=850, EV+0.7
🧪 Override applied: {'exposure_compensation': 0.9}
```

## Testing Strategy

### 1. Backward Compatibility Test

```bash
# Verify Mode 1 still works without any profile
curl -X POST http://helios.local:8080/capture \
  -H "Content-Type: application/json" \
  -d '{"iso": 400, "shutter_speed": "1/1000", "exposure_compensation": 0.7}'
```

**Expected:** Capture succeeds with explicit settings

### 2. Profile Deployment Test

```bash
# Deploy a profile
curl -X POST http://helios.local:8080/profile/deploy \
  -H "Content-Type: application/json" \
  -d @test_profile.json

# Check status
curl http://helios.local:8080/status
```

**Expected:** operational_mode = "deployed_profile"

### 3. Profile Execution Test

```bash
# Capture using deployed profile
curl -X POST http://helios.local:8080/capture \
  -H "Content-Type: application/json" \
  -d '{"use_deployed_profile": true, "schedule_type": "sunset"}'
```

**Expected:** Pi calculates settings and captures

### 4. Override Test

```bash
# Test with override
curl -X POST http://helios.local:8080/capture \
  -H "Content-Type: application/json" \
  -d '{
    "use_deployed_profile": true,
    "schedule_type": "sunset",
    "override": {"exposure_compensation": 0.9}
  }'
```

**Expected:** Base settings from profile + override applied

### 5. Error Handling Test

```bash
# Clear profile
curl -X DELETE http://helios.local:8080/profile/current

# Try to use profile mode
curl -X POST http://helios.local:8080/capture \
  -d '{"use_deployed_profile": true}'
```

**Expected:** 400 error - "No profile deployed"

## Integration Notes

### Backend Integration

When Backend wants to use profile execution:

1. Deploy profile once: `POST /profile/deploy`
2. Schedule can now use: `use_deployed_profile=true`
3. Pi calculates settings autonomously
4. Reduces network traffic and latency

### Profile Structure

```json
{
  "profile_id": "abc123",
  "version": "1.0.0",
  "settings": {
    "base": {
      "iso": 400,
      "shutter_speed": "1/1000",
      "exposure_compensation": 0.0
    },
    "adaptive_wb": {
      "enabled": true,
      "lux_table": [
        [10000, 5500],
        [1000, 4500],
        [100, 3500]
      ]
    },
    "schedule_overrides": {
      "sunset": {
        "exposure_compensation": 0.7
      },
      "sunrise": {
        "exposure_compensation": 0.5
      }
    }
  }
}
```

## Next Steps

### For Backend Team

1. Update schedule executor to optionally use `use_deployed_profile=true`
2. Add profile deployment logic before autonomous schedules
3. Test profile execution vs live orchestration performance

### For Testing

1. Deploy test profile to Pi
2. Run all three capture modes
3. Verify settings match expected profile calculations
4. Test fallback to live mode when profile cleared

### For Documentation

1. Update API docs with new capture modes
2. Add profile deployment examples
3. Document operational mode transitions

## Files Modified

- `/Users/nicholasmparker/Projects/skylapse/pi/main.py`
  - Updated `CaptureSettings` model with profile fields
  - Enhanced `capture_photo()` with mode selection logic
  - Added detailed logging for both modes

## Files Created

- `/Users/nicholasmparker/Projects/skylapse/pi/test_profile_execution.py`
  - Test script demonstrating all three modes
  - Example payloads for each scenario

## Backward Compatibility

✓ **Fully maintained** - All existing capture requests work unchanged

- Explicit settings still function exactly as before
- ISO=0 auto mode still supported
- No breaking changes to API
- New fields are optional with safe defaults
