# Exposure Strategy for Highest Quality Sunrise/Sunset Timelapses

**Camera**: Arducam IMX519 (16MP, HDR capable)
**Pi**: helios.local (username: nicholasmparker)
**Priority**: PICTURE QUALITY ABOVE ALL ELSE

---

## The Challenge: "Holy Grail" Timelapses

Sunrise and sunset present the hardest exposure challenge in timelapse photography:

- Light changes by 10+ stops over 60 minutes
- Too dark → noisy, underexposed images
- Too bright → blown highlights, lost detail
- Inconsistent exposure → **flicker** (the enemy of timelapses)

**"Holy Grail" timelapses** = Smooth, flicker-free day-to-night or night-to-day transitions

---

## Research Findings: Manual vs Auto Exposure

### ❌ Auto Exposure Problems

1. **Flicker**: Camera makes different decisions frame-to-frame → visible flicker
2. **Over-compensation**: Adjusts too much in wrong direction
3. **Metering changes**: Different parts of scene affect exposure differently
4. **No consistency**: Each frame is independent

### ✅ Manual Exposure with Ramping

1. **Smooth transitions**: Gradual 1/3-stop changes
2. **Predictable**: We control the exposure curve
3. **No flicker**: Consistent decision-making
4. **Professional results**: Industry standard for sunrise/sunset timelapses

---

## Your Camera Capabilities (IMX519)

```python
Available Controls:
  AnalogueGain: (1.0, 16.0, 1.0)     # ISO 100-1600
  ExposureTime: (1, 66666, 20000)    # 1μs to 66ms (max ~1/15s)
  ExposureValue: (-8.0, 8.0, 0.0)    # EV compensation ±8 stops
  HdrMode: (0, 4, 0)                 # HDR capability!
  Brightness: (-1.0, 1.0, 0.0)       # Additional compensation
```

**Key Insight**: Your camera HAS `ExposureValue` control! This is huge for quality.

---

## Recommended Strategy: Adaptive Manual Exposure

### Approach: "Smart Manual"

Instead of full auto or pure manual, we'll use **calculated manual exposure with gradual ramping**:

1. **Before capture**: Calculate optimal settings based on sun position
2. **During capture**: Set fixed exposure per frame (no auto flicker)
3. **Between frames**: Gradually adjust settings (smooth ramping)

---

## Implementation: Three-Phase Exposure Curve

### Phase 1: Before Sunrise/After Sunset (Dark)

**Goal**: Maximum light gathering without too much noise

```python
# 30 minutes before sunrise
ISO: 800-1600  # High gain for low light
Shutter: 1/30s to 1/15s  # Slower shutter (within limits)
EV: +1.0 to +1.5  # Boost exposure
```

**Why**:

- Need maximum sensitivity in low light
- Longer shutter OK (no motion blur in slow-changing scenes)
- EV compensation helps without increasing noise
- Darker images in timelapse look intentional

### Phase 2: Golden Hour (15min before/after sun)

**Goal**: Capture rich colors without blowing highlights

```python
# -15min to +15min from sunrise
ISO: 200-400  # Medium gain
Shutter: 1/250s to 1/500s  # Fast enough to freeze detail
EV: +0.3 to +0.7  # Slight boost for vibrant colors
```

**Why**:

- This is the MONEY SHOT - don't blow it
- Fast shutter preserves cloud detail
- Moderate ISO keeps noise minimal
- EV compensation brings out golden tones

### Phase 3: Full Daylight

**Goal**: Maximum image quality

```python
# Full daylight
ISO: 100  # Minimum noise
Shutter: 1/500s to 1/1000s  # Crisp, sharp
EV: 0.0  # Neutral, trust the exposure
```

**Why**:

- Plenty of light available
- Lowest ISO = best image quality
- Fast shutter = sharpest details

---

## The Critical Detail: RAMPING RATE

**Research consensus**: Change by **1/3 stop maximum** per frame

For 30-second intervals:

- ✅ 1/3 stop per frame = smooth
- ❌ 1 full stop per frame = visible jump
- ❌ 2+ stops = obvious flicker

### How to Ramp

**Option A: ISO ramping** (preferred)

- ISO 100 → 200 → 400 → 800 → 1600
- Each doubling = 1 stop
- Increments: 100, 125, 160, 200, 250, 320, 400, 500, 640, 800, 1000, 1250, 1600
- Change every 3-5 frames for 1/3 stop steps

**Option B: Shutter ramping**

- 1/1000 → 1/500 → 1/250 → 1/125
- Each halving = 1 stop
- Use with ISO changes for fine control

**Option C: EV ramping** (YOUR ADVANTAGE!)

- Your camera has ExposureValue control
- Can make micro-adjustments: EV 0.0 → 0.3 → 0.7 → 1.0
- Smoother than ISO/shutter steps alone

---

## Proposed Algorithm: Time-Based Exposure Curve

```python
def calculate_optimal_settings(schedule_type, minutes_from_sun_event):
    """
    Calculate exposure based on position relative to sunrise/sunset.

    Returns settings that ramp smoothly over time.
    """

    if schedule_type == "sunrise":
        if minutes_from_sun_event < -20:
            # Deep pre-dawn
            return {
                "iso": 1600,
                "shutter_speed": "1/30",
                "exposure_value": +1.5,
                "hdr_mode": 0  # Off (too dark)
            }
        elif -20 <= minutes_from_sun_event < -10:
            # Pre-dawn twilight
            # RAMP: ISO 1600→800, EV +1.5→+1.0
            progress = (minutes_from_sun_event + 20) / 10  # 0.0 to 1.0
            iso = int(1600 - (800 * progress))  # 1600→800
            ev = 1.5 - (0.5 * progress)  # 1.5→1.0
            return {
                "iso": iso,
                "shutter_speed": "1/60",
                "exposure_value": ev,
                "hdr_mode": 0
            }
        elif -10 <= minutes_from_sun_event < 0:
            # Approaching sunrise - GOLDEN HOUR PREP
            # RAMP: ISO 800→400, EV +1.0→+0.7
            progress = (minutes_from_sun_event + 10) / 10
            iso = int(800 - (400 * progress))  # 800→400
            ev = 1.0 - (0.3 * progress)  # 1.0→0.7
            return {
                "iso": iso,
                "shutter_speed": "1/250",
                "exposure_value": ev,
                "hdr_mode": 1  # SingleExposure HDR for dynamic range
            }
        elif 0 <= minutes_from_sun_event < 10:
            # GOLDEN HOUR - PRIME TIME
            # RAMP: ISO 400→200, EV +0.7→+0.3
            progress = minutes_from_sun_event / 10
            iso = int(400 - (200 * progress))  # 400→200
            ev = 0.7 - (0.4 * progress)  # 0.7→0.3
            return {
                "iso": iso,
                "shutter_speed": "1/500",
                "exposure_value": ev,
                "hdr_mode": 1  # HDR for rich colors
            }
        else:  # > 10 minutes after
            # Full daylight
            return {
                "iso": 100,
                "shutter_speed": "1/1000",
                "exposure_value": 0.0,
                "hdr_mode": 0
            }

    # Similar curves for sunset (reversed)
```

---

## HDR Mode: Your Secret Weapon

Your camera has **HdrMode: (0, 4, 0)** with 5 modes:

```
0 = Off
1 = SingleExposure  # Process single frame for HDR look
2 = MultiExposure   # Bracket multiple frames (need to test)
3 = Night           # Optimized for low light
4 = ?               # Unknown, need to test
```

### When to Use HDR

**SingleExposure (Mode 1)**: During golden hour

- Preserves highlights in bright sky
- Brings up shadow detail
- No extra frames needed
- **Best for timelapses** (consistent frame rate)

**MultiExposure (Mode 2)**: FOR TESTING

- Takes multiple bracketed exposures
- Merges into single HDR image
- **Problem**: Might slow down capture rate
- **Test required**: Does it fit in 30-second interval?

---

## What We Need to Build

### 1. Enhanced Exposure Calculator

**Current**: Simple 3-zone system (before/during/after)
**Needed**: Continuous ramping curve based on minutes from sun event

```python
class ExposureCalculator:
    def calculate_settings(self, schedule_type, current_time):
        # Calculate minutes from sunrise/sunset
        sun_time = self.solar_calc.get_sunrise(current_time)
        minutes_offset = (current_time - sun_time).total_seconds() / 60

        # Use continuous curve, not discrete zones
        settings = self._calculate_ramped_exposure(
            schedule_type,
            minutes_offset
        )

        return settings
```

### 2. Test Suite for Exposure Ramps

**Critical**: We must test on real hardware during actual sunrise/sunset

Test checklist:

- [ ] Capture full sunrise sequence (60 min)
- [ ] Review for flicker
- [ ] Check highlight preservation (sky)
- [ ] Check shadow detail (foreground)
- [ ] Verify smooth transitions
- [ ] Test HDR mode 1 vs 0
- [ ] Measure capture timing (30s interval maintained?)

### 3. Post-Processing Considerations

Even with perfect in-camera exposure:

- **LRTimelapse** or similar may still be needed for final smoothing
- **Deflickering** algorithms can fix minor inconsistencies
- **Color grading** brings out the best in raw captures

---

## Action Items (Priority Order)

### IMMEDIATE (This Session)

1. **Update exposure.py** with continuous ramping algorithm
2. **Add HDR mode support** to Pi capture
3. **Document camera specs** in codebase
4. **Update Pi credentials** in deployment docs

### NEXT SESSION (Field Testing)

5. **Deploy to Pi** and test during actual sunrise
6. **Capture test sequence** with current algorithm
7. **Analyze results**: flicker, exposure consistency, quality
8. **Iterate on algorithm** based on real-world results

### FUTURE (Optimization)

9. **Implement post-processing pipeline** (deflicker, color grade)
10. **Add image stacking** for noise reduction (5-frame average)
11. **Experiment with HDR MultiExposure** mode
12. **Build exposure preview tool** (simulate before capture)

---

## Key Principles (Never Forget)

1. **Smooth > Perfect**: Gradual changes matter more than perfect exposure
2. **Test in Field**: No amount of theory beats real sunrise data
3. **Iterate Fast**: Capture, review, adjust, repeat
4. **Document Everything**: Log all settings with each capture
5. **Quality Over Features**: One perfect timelapse > ten mediocre ones

---

## Expected Results

With this approach:

- ✅ Smooth exposure transitions (no flicker)
- ✅ Preserved highlights (sky detail)
- ✅ Acceptable shadow detail (foreground)
- ✅ Vibrant golden hour colors
- ✅ Professional-quality output
- ✅ Minimal post-processing needed

---

## Pi Configuration

**Hardware**: Raspberry Pi with Arducam IMX519
**Network**: helios.local
**User**: nicholasmparker
**Camera**: 16MP, HDR-capable, up to 1/15s exposure

---

## Next Steps

**Before ANY other features, we must**:

1. Implement the ramping algorithm
2. Test during real sunrise
3. Validate image quality
4. Iterate until perfect

**Everything else waits until photos are beautiful.**

---

**The goal**: When someone watches our timelapse, they say "WOW, that's stunning" - not "that's flickery" or "that's washed out".
