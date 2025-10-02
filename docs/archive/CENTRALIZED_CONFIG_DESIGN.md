# Centralized Configuration Design

## Current State (Problems)

**Split configuration:**

- Pi has hardcoded camera settings logic
- Backend calculates exposure but doesn't control everything
- Profile definitions exist in backend but some behavior is Pi-side
- No single source of truth for "what settings produce what output"

**Issues:**

- Hard to iterate on profiles without deploying to Pi
- Can't A/B test settings without code changes
- Settings are code, not data
- Can't adjust profiles based on learned results

## Proposed Design: Backend as Brain, Pi as Dumb Executor

### Architecture

```
┌─────────────────────────────────────────────────────┐
│ Backend/Brain (Docker)                               │
│                                                       │
│  ┌──────────────────────────────────────────────┐  │
│  │ Profile Database (JSON/SQLite)                │  │
│  │ - Profile definitions (A, B, C, D, E, F...)   │  │
│  │ - WB curves and lux mappings                  │  │
│  │ - Exposure compensation rules                 │  │
│  │ - Historical performance data                 │  │
│  └──────────────────────────────────────────────┘  │
│                                                       │
│  ┌──────────────────────────────────────────────┐  │
│  │ Exposure Engine                               │  │
│  │ - Reads metering from Pi                      │  │
│  │ - Applies profile rules                       │  │
│  │ - Outputs complete camera settings            │  │
│  └──────────────────────────────────────────────┘  │
│                                                       │
│  ┌──────────────────────────────────────────────┐  │
│  │ Learning/Analytics                            │  │
│  │ - Tracks which settings produce best results  │  │
│  │ - Suggests profile improvements              │  │
│  │ - A/B testing framework                       │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
                        ↓ Complete settings packet
┌─────────────────────────────────────────────────────┐
│ Pi Capture Service                                   │
│                                                       │
│  ┌──────────────────────────────────────────────┐  │
│  │ Camera Interface                              │  │
│  │ - Receives: {iso, shutter, wb_temp, ev...}   │  │
│  │ - Applies settings to camera                  │  │
│  │ - Captures image                              │  │
│  │ - Returns: success/failure + metadata         │  │
│  └──────────────────────────────────────────────┘  │
│                                                       │
│  NO LOGIC - Just execution                           │
└─────────────────────────────────────────────────────┘
```

### Profile Definition Format

```json
{
  "profiles": {
    "b_daylight": {
      "name": "Daylight WB - Natural Colors",
      "awb_mode": 1,
      "wb_temp": null,
      "exposure_compensation": 0.0,
      "hdr_mode": 0,
      "bracket_count": 1,
      "metering_mode": "scene",
      "notes": "Best performer for natural colors"
    },
    "e_adaptive": {
      "name": "EXPERIMENTAL - Adaptive Lux+Time WB",
      "awb_mode": 6,
      "wb_calculation": {
        "type": "adaptive_ramp",
        "base_curve": [
          { "minutes_from_sunset": -30, "wb_temp": 5500 },
          { "minutes_from_sunset": 0, "wb_temp": 4750 },
          { "minutes_from_sunset": 30, "wb_temp": 4000 }
        ],
        "lux_adjustments": [
          {
            "lux_above": 10000,
            "adjustment": +500,
            "reason": "preserve warm tones"
          },
          {
            "lux_below": 3000,
            "adjustment": -200,
            "reason": "enhance low light"
          },
          {
            "lux_below": 1000,
            "adjustment": -500,
            "reason": "rich night colors"
          }
        ]
      },
      "exposure_compensation": 0.0,
      "hdr_mode": 0,
      "bracket_count": 1
    }
  }
}
```

### Benefits

1. **Rapid Iteration**: Change profile settings in JSON, no code deploy
2. **A/B Testing**: Easy to test multiple profile variants
3. **Learning**: Track performance metrics per profile
4. **Portability**: Same config works on different Pi hardware
5. **UI Control**: Eventually expose profile editor in frontend
6. **Version Control**: Profile definitions are data, can track changes

### Migration Path

**Phase 1: Extract current profiles to JSON** (keep existing code working)

- Move profile definitions from exposure.py to profiles.json
- Backend reads JSON and applies settings (same logic)
- Pi unchanged

**Phase 2: Simplify Pi to pure executor**

- Remove profile logic from Pi
- Pi just accepts complete settings and applies them
- All intelligence in backend

**Phase 3: Add learning layer**

- Track capture results (success/failure, quality metrics)
- Build recommendation engine for profile improvements

## Open Questions

1. **Where to store profiles?**

   - JSON file in backend (simple, version controlled)
   - SQLite (queryable, can track history)
   - Both? (JSON is source, SQLite is runtime)

2. **How to handle camera-specific capabilities?**

   - ArduCam supports custom WB, but USB webcam might not
   - Need capability detection + fallback rules

3. **Real-time tuning during sunset?**

   - Should profiles be adjustable mid-capture?
   - Or only between schedule runs?

4. **Profile versioning?**
   - If we improve Profile E, do we version it? (E_v2)
   - Or track changes in git history?
