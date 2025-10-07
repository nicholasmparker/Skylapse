# Next Session: Exposure Smoothing & Debug Overlay

## What Just Deployed

**Branch merged**: `feature/exposure-smoothing-debug` → `main`
**Commit**: `1595069`

### Database Schema Extended

The `captures` table now stores ALL camera settings (not just basic exposure):

**New columns added**:
- `profile` - Which profile captured this (a-g)
- `hdr_mode`, `bracket_count`, `bracket_ev` - HDR/bracketing settings
- `ae_metering_mode` - Metering mode (spot/center/matrix)
- `af_mode`, `lens_position` - Focus settings
- `sharpness`, `contrast`, `saturation` - Enhancement settings

**Migration**: Safe for existing Dagon database
- Uses `ALTER TABLE` with NULL checks
- Won't break existing data
- Logs each migration step on first startup

## Testing on Dagon

After GitHub Actions deploys:

```bash
# Check migration ran successfully
docker-compose logs backend | grep "Adding column"

# Should see:
# INFO - Adding column 'profile' to captures table
# INFO - Adding column 'hdr_mode' to captures table
# ... (10 new columns)

# Verify new columns exist
docker-compose exec backend sqlite3 /data/db/skylapse.db "PRAGMA table_info(captures);"
```

**Expected**: Backend starts normally, captures work as before, new columns populate with data.

## What's Coming Next

### Goal: Fix Timelapse Flicker + Debug Overlay

**Problem**: Rapid ISO/exposure changes cause brightness flickering in timelapses

**Solution**: Two-part implementation

### Part 1: Exposure Smoothing (Removes Flicker)

Add temporal smoothing to exposure calculator:

**Config** (`config.json`):
```json
"schedules": {
  "sunrise": {
    "smoothing": {
      "enabled": true,
      "window_frames": 8,
      "max_change_per_frame": 0.12,
      "iso_weight": 0.7,
      "shutter_weight": 0.3
    }
  }
}
```

**Algorithm**: Exponential Moving Average (EMA)
- Stores last N frames per session
- Limits max change per frame (prevents jumps)
- Weighted smoothing (prioritize ISO or shutter)
- Persists across backend restarts (database)

**Result**: Smooth transitions, no flickering

### Part 2: Debug Overlay (Tuning Tool)

Overlay ALL camera settings on timelapse video:

**Config** (`config.json`):
```json
"schedules": {
  "sunrise": {
    "video_debug": {
      "enabled": true,
      "font_size": 16,
      "position": "bottom-left",
      "background": true
    }
  }
}
```

**Overlay shows** (bottom-left of video):
```
Profile: D (Warm Dramatic)
Frame: 324/1200
ISO: 200 → 250 (smoothed ↑12%)
Shutter: 1/500s
EV: +0.3
WB: 5200K (warm curve)
Focus: 2.45mm (manual)
Lux: 1250
Sharpness: 1.0  Contrast: 1.15  Sat: 1.05
Time: 06:42:15
```

**Use cases**:
- See exactly what smoothing is doing
- Tune smoothing parameters (window size, max change)
- Verify profile settings are applied
- Debug exposure issues
- A/B test profiles

## Implementation Plan (Next Session)

### Task 1: Add Config Structure
- [ ] Update `backend/config.json` with smoothing/debug defaults
- [ ] Update `config.json.example` with examples
- [ ] Update `config_validator.py` to validate new settings

### Task 2: Implement Smoothing
- [ ] Create `ExposureHistory` class (stores per-session)
- [ ] Implement EMA algorithm in `exposure.py`
- [ ] Add smoothing to `calculate_settings()`
- [ ] Load/save history to database
- [ ] Test: Capture sequence shows smooth transitions

### Task 3: Implement Debug Overlay
- [ ] Add `build_debug_overlay()` in `tasks.py`
- [ ] Query capture metadata from database
- [ ] Generate ffmpeg drawtext filter chain
- [ ] Position overlay bottom-left
- [ ] Test: Timelapse shows all settings

### Task 4: Testing
- [ ] Test smoothing with sunrise schedule
- [ ] Verify debug overlay readable in 4K
- [ ] Test disabled smoothing (no changes)
- [ ] Test disabled debug (production mode)
- [ ] Verify no performance impact

**Estimated time**: 2-3 hours

## Quick Reference

**Current commits**:
```
1595069 - feat(database): Store all camera settings (DEPLOYED)
901875f - docs: Add config example and deployment guide
27c5232 - fix(tech-debt): Address blockers from QA
dad0f49 - feat(tech-debt): Data-driven profiles
23fe81c - refactor(tech-debt): Remove sys.path hacks
```

**Feature branch**: Can delete `feature/exposure-smoothing-debug` (merged)

**Next branch**: Create `feature/smoothing-implementation` when ready

## Notes

- Database changes are **non-breaking** (all new columns nullable)
- Smoothing algorithm is **stateful** (persists in database)
- Debug overlay is **per-schedule** (can run in production)
- Config changes are **hot-reloadable** (restart backend, no rebuild)

---

**When ready**: Ping me and I'll implement smoothing + debug overlay!
