# Exposure Testing & Optimization Plan

**Goal**: Find the PERFECT exposure settings for sunrise/sunset at different times of day

**Approach**: Multi-strategy testing system with visual comparison tools

---

## Strategy 1: Bracketing Burst Test

**What**: Take multiple shots with different settings at the same moment
**When**: Every 5 minutes during sunrise/sunset
**Purpose**: Compare settings side-by-side to see what works best

### Implementation

```python
# New endpoint: /test/bracket
POST /api/test/bracket
{
  "test_name": "sunrise_golden_hour",
  "base_iso": 400,
  "base_shutter": "1/500",
  "variations": [
    {"iso_offset": -1, "ev_offset": 0},      # ISO 200
    {"iso_offset": 0, "ev_offset": -0.3},    # Base, slight underexpose
    {"iso_offset": 0, "ev_offset": 0},       # Base
    {"iso_offset": 0, "ev_offset": +0.3},    # Base, slight overexpose
    {"iso_offset": +1, "ev_offset": 0},      # ISO 800
  ]
}
```

**Result**: 5 images captured within 5 seconds, all metadata logged

---

## Strategy 2: Settings Matrix Test

**What**: Test every combination of ISO/shutter/EV systematically
**When**: Once at sunrise, once at sunset, once at noon
**Purpose**: Build empirical data on what settings work best when

### Test Matrix

```python
test_matrix = {
    "iso_values": [100, 200, 400, 800, 1600],
    "shutter_speeds": ["1/1000", "1/500", "1/250", "1/125", "1/60"],
    "ev_values": [-0.7, -0.3, 0.0, +0.3, +0.7],
    "hdr_modes": [0, 1]  # Off, SingleExposure
}

# Total: 5 * 5 * 5 * 2 = 250 combinations
# At 2 seconds per shot = ~8 minutes total
```

**Run this 3x per day**:

- 6:00 AM (pre-dawn)
- 6:45 AM (golden hour)
- 12:00 PM (noon baseline)

---

## Strategy 3: Time-Lapse A/B Test

**What**: Run two different exposure algorithms simultaneously
**When**: Full sunrise capture (60 min)
**Purpose**: See which algorithm produces better final timelapse

### Setup

```python
# Algorithm A: Our current simple zones
# Algorithm B: Continuous ramping curve
# Algorithm C: Auto-exposure (for comparison)

# Alternate captures:
# Frame 1: Algorithm A
# Frame 2: Algorithm B
# Frame 3: Algorithm C
# Repeat for 60 minutes
```

**Result**: 3 separate timelapses from same session to compare

---

## Strategy 4: Live Preview Dashboard

**What**: Web interface showing live camera feed with setting adjustments
**When**: Real-time during sunrise/sunset
**Purpose**: Immediately see impact of settings changes

### Features Needed

```
┌─────────────────────────────────────────┐
│  Exposure Test Dashboard                │
├─────────────────────────────────────────┤
│                                         │
│  [Live Preview Image - 1280x720]       │
│  Last updated: 2 seconds ago            │
│                                         │
├─────────────────────────────────────────┤
│  Current Settings:                      │
│    ISO: [==400====] 100-1600            │
│    Shutter: [==1/500==] 1/1000-1/15     │
│    EV: [===0.0====] -2.0 to +2.0        │
│    HDR: [Off] [Single] [Multi] [Night] │
│                                         │
│  [Capture Test Shot]  [Apply & Monitor]│
├─────────────────────────────────────────┤
│  Sun Info:                              │
│    Current: 6:42 AM                     │
│    Sunrise: 6:52 AM (in 10 min)        │
│    Time from sun: -10 minutes          │
│                                         │
│  Recommended Settings:                  │
│    ISO: 400  Shutter: 1/250  EV: +0.7  │
│    (Click to apply)                     │
└─────────────────────────────────────────┘
```

---

## Strategy 5: Histogram Analysis

**What**: Capture histogram data with each image
**When**: Every test shot
**Purpose**: Objectively measure exposure quality

### Metrics to Track

```python
image_quality_metrics = {
    "histogram": {
        "shadows": 0-51,      # Count of pixels in shadow range
        "midtones": 52-204,   # Count in midtone range
        "highlights": 205-255 # Count in highlight range
    },
    "clipping": {
        "blacks_clipped": 0,     # Pure black pixels (lost shadow)
        "whites_clipped": 0      # Pure white pixels (blown highlights)
    },
    "distribution": {
        "mean_luminance": 128,   # Average brightness
        "std_dev": 45,           # Contrast measure
        "dynamic_range": 200     # Brightest - darkest pixel
    }
}
```

**Good Exposure Indicators**:

- Blacks clipped < 2%
- Whites clipped < 1% (except sun itself)
- Mean luminance: 100-140 (slightly bright)
- Good spread across histogram (not bunched up)

---

## Implementation Plan

### Phase 1: Add Test Endpoints (1-2 hours)

**Backend: `backend/test_endpoints.py`**

```python
from fastapi import APIRouter
from typing import List, Optional
from datetime import datetime

router = APIRouter(prefix="/api/test", tags=["testing"])

@router.post("/capture-test")
async def capture_test_shot(
    iso: int,
    shutter_speed: str,
    exposure_value: float,
    hdr_mode: int = 0,
    test_name: Optional[str] = None
):
    """
    Capture a single test shot with specific settings.

    Returns image path and quality metrics.
    """
    # Call Pi with exact settings
    # Save with metadata: timestamp, settings, sun position
    # Calculate histogram
    # Return results
    pass

@router.post("/bracket")
async def capture_bracket(
    base_iso: int,
    base_shutter: str,
    variations: List[dict],
    test_name: str
):
    """
    Capture bracketed sequence for comparison.

    Takes 3-7 shots with different settings.
    """
    results = []
    for variation in variations:
        # Calculate modified settings
        # Capture shot
        # Store with variation label
        results.append(shot_info)

    return {"test_id": test_id, "shots": results}

@router.post("/matrix-test")
async def run_matrix_test():
    """
    Run full settings matrix test.

    WARNING: Takes ~8 minutes, captures 250 images.
    """
    pass

@router.get("/test-results/{test_id}")
async def get_test_results(test_id: str):
    """
    Retrieve test results with comparison gallery.
    """
    pass
```

### Phase 2: Simple Web UI (2-3 hours)

**Frontend: `frontend/src/pages/ExposureTest.tsx`**

Key components:

1. **Live Preview** - Show latest capture from Pi
2. **Settings Sliders** - Adjust ISO/shutter/EV in real-time
3. **Quick Capture** - Button to test current settings
4. **Results Gallery** - Grid of recent test shots
5. **Comparison View** - Side-by-side shot comparison
6. **Sun Clock** - Visual indicator of sunrise/sunset timing

### Phase 3: Comparison Tools (2-3 hours)

**Features**:

- **2-up, 4-up, 9-up** comparison grids
- **Slider overlay** - Swipe between two images
- **Histogram overlay** - Show histogram on each image
- **Metadata display** - Settings printed on each image
- **Rating system** - Star/favorite the best shots
- **Export notes** - Document which settings worked best

---

## Test Protocols

### Protocol A: Daily Sunrise Test (30 days)

**Goal**: Build empirical dataset of what works

**Schedule**:

- 30 minutes before sunrise
- Run bracketing burst every 5 minutes
- Total: 12 bursts × 5 shots = 60 test images per morning
- Review results same day

**Data Collection**:

```python
test_log = {
    "date": "2025-10-01",
    "sunrise_time": "6:52 AM",
    "weather": "Clear",
    "temperature": "65°F",
    "tests": [
        {
            "time": "6:22 AM",
            "minutes_from_sunrise": -30,
            "shots": [
                {
                    "iso": 800,
                    "shutter": "1/125",
                    "ev": 0.0,
                    "histogram": {...},
                    "rating": 4,  # Manual rating 1-5
                    "notes": "Good shadow detail, slight noise"
                },
                # ... 4 more variations
            ]
        },
        # ... 11 more test points
    ]
}
```

### Protocol B: Golden Hour Deep Dive

**Goal**: Perfect the golden hour settings (most important)

**Setup**:

- Focus on 15 minutes before to 15 minutes after sunrise
- Test every minute (30 total tests)
- 3 variations per test (90 images)
- Find the exact ISO/shutter/EV curve

**Variations to test**:

1. Conservative (underexpose): ISO 200, 1/500, EV +0.3
2. Balanced: ISO 400, 1/500, EV +0.5
3. Aggressive (bright): ISO 400, 1/250, EV +0.7

### Protocol C: Algorithm Validation

**Goal**: Verify our ramping algorithm produces good results

**Setup**:

- Run our algorithm for full 60-minute sunrise
- Capture every 30 seconds (120 frames)
- Review final timelapse for:
  - Flicker
  - Blown highlights
  - Lost shadow detail
  - Smooth exposure transitions

**Pass criteria**:

- ✓ No visible flicker
- ✓ <1% blown highlights (except sun)
- ✓ Shadow detail visible throughout
- ✓ Smooth brightness curve

---

## Tools We Need to Build

### 1. **Test Capture Script** (Quick implementation)

```python
# scripts/test-capture.py
"""
Quick CLI tool for manual testing from laptop.
"""

import requests
import sys

PI_URL = "http://helios.local:8080/capture"

def capture_test(iso, shutter, ev, name):
    response = requests.post(PI_URL, json={
        "iso": iso,
        "shutter_speed": shutter,
        "exposure_compensation": ev
    })
    print(f"Captured: {name}")
    print(f"  Settings: ISO {iso}, {shutter}, EV {ev:+.1f}")
    print(f"  Result: {response.json()}")

if __name__ == "__main__":
    # Quick bracket test
    base_iso = int(sys.argv[1]) if len(sys.argv) > 1 else 400

    tests = [
        (base_iso // 2, "1/500", -0.3, "underexposed"),
        (base_iso, "1/500", 0.0, "baseline"),
        (base_iso, "1/500", +0.3, "boosted"),
        (base_iso * 2, "1/500", 0.0, "high_iso"),
    ]

    for iso, shutter, ev, name in tests:
        capture_test(iso, shutter, ev, name)
```

**Usage**:

```bash
# From laptop, captures 4 test shots
python3 scripts/test-capture.py 400
```

### 2. **Image Comparison Webpage** (Simple first version)

```html
<!-- frontend/public/compare.html -->
<!doctype html>
<html>
  <head>
    <title>Exposure Comparison</title>
    <style>
      .grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 10px;
      }
      .shot {
        border: 2px solid #ccc;
        padding: 10px;
      }
      .shot.selected {
        border-color: #00ff00;
      }
      .shot img {
        width: 100%;
        cursor: pointer;
      }
      .metadata {
        font-family: monospace;
        font-size: 12px;
      }
    </style>
  </head>
  <body>
    <h1>Test Shot Comparison</h1>
    <div id="grid" class="grid"></div>

    <script>
      // Load test results from backend
      // Display in grid
      // Click to select/compare
      // Show histograms
    </script>
  </body>
</html>
```

### 3. **Histogram Viewer**

```python
# backend/utils/histogram.py
"""
Calculate and visualize image histograms.
"""
from PIL import Image
import numpy as np

def calculate_histogram(image_path):
    img = Image.open(image_path).convert('L')  # Grayscale
    histogram = np.histogram(np.array(img), bins=256, range=(0, 255))[0]

    return {
        "bins": histogram.tolist(),
        "mean": float(np.mean(np.array(img))),
        "std": float(np.std(np.array(img))),
        "min": int(np.min(np.array(img))),
        "max": int(np.max(np.array(img))),
        "clipped_blacks": int(histogram[0]),  # Pure black pixels
        "clipped_whites": int(histogram[255]),  # Pure white pixels
    }
```

---

## Expected Outcomes

### Week 1: Baseline Data

- 7 days × 60 test images = 420 test shots
- Identify best settings for each time window
- Document what definitely doesn't work

### Week 2: Algorithm Refinement

- Implement findings into exposure calculator
- Run validation captures
- Compare against auto-exposure baseline

### Week 3: Fine-Tuning

- Adjust ramping curves based on real data
- Test edge cases (cloudy, very bright, etc.)
- Optimize for different weather conditions

### Week 4: Production Ready

- Final algorithm locked in
- Documentation complete
- Confidence in image quality

---

## Success Metrics

**We know we're ready when**:

1. ✅ 10 consecutive sunrise timelapses with no flicker
2. ✅ Preserved highlight detail in 95%+ of frames
3. ✅ Shadow detail visible throughout golden hour
4. ✅ Smooth exposure curve (no jumps)
5. ✅ Someone says "WOW" when watching the timelapse

---

## Next Actions

**Immediate** (This session):

1. Create test capture endpoint on Pi
2. Build simple bracket capture script
3. Test bracketing on Pi with current sunrise/sunset position

**Tomorrow**: 4. Capture first bracket set during sunrise 5. Review images and document findings 6. Start building comparison web UI

**This Week**: 7. Daily sunrise tests with bracketing 8. Build histogram analysis tools 9. Implement first round of algorithm improvements

---

**Remember**: We're not guessing. We're measuring, comparing, and iterating based on real data.
