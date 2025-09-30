# Baseline Capture Test Results

**Date:** 2025-09-30 13:18 MST
**Location:** Indoor test (not sunrise/sunset)
**Purpose:** Establish baseline before implementing continuous ramping

## Test Configuration

- **Camera:** Arducam IMX519 (16MP)
- **Resolution:** 4656×3496 pixels
- **GPU Memory:** 256MB
- **Bracket Type:** Standard (ISO + EV variations)

## Captured Images

### 1. ISO Low (Underexposed)

- **File:** capture_20250930_131828.jpg (1.8MB)
- **Settings:** ISO 200, 1/500s, EV -0.3
- **Purpose:** Test shadow detail retention

### 2. Baseline

- **File:** capture_20250930_131830.jpg (1.8MB)
- **Settings:** ISO 400, 1/500s, EV +0.0
- **Purpose:** Neutral reference exposure

### 3. EV Boost

- **File:** capture_20250930_131831.jpg (1.6MB)
- **Settings:** ISO 400, 1/500s, EV +0.3
- **Purpose:** Test ExposureValue control effectiveness

### 4. ISO High

- **File:** capture_20250930_131833.jpg (1.4MB)
- **Settings:** ISO 800, 1/500s, EV +0.0
- **Purpose:** Test noise at higher ISO

## Observations

### File Sizes

- ISO 200: 1.8MB
- ISO 400 (EV 0): 1.8MB
- ISO 400 (EV +0.3): 1.6MB
- ISO 800: 1.4MB

**Note:** File size decreases with higher ISO/brightness, likely due to JPEG compression of noise.

### Capture Performance

- ✅ All 4 captures successful
- ✅ No errors or failures
- ✅ Consistent ~2 second intervals
- ✅ Camera stays running between captures

## Next Steps

1. **Visual Review:** Compare images side-by-side to evaluate:

   - ExposureValue control effectiveness (baseline vs EV boost)
   - ISO impact on noise (ISO 200 vs 800)
   - Overall image quality

2. **Fix Identified Issues:**

   - Implement continuous ramping (eliminate flicker)
   - Add camera control validation
   - Add capture file verification

3. **Golden Hour Test:** Run bracket test during actual sunset to:
   - See flicker in current algorithm
   - Establish proper exposure curve
   - Test HDR mode effectiveness

## QA Findings Applied

- ✅ Fixed CRITICAL-5: Image directory permissions (changed to ~/skylapse-images)
- 🔲 Still TODO: Continuous exposure ramping
- 🔲 Still TODO: Camera control validation
- 🔲 Still TODO: HDR mode support
