# Image Review Checklist

## What to Look For

### 1. ExposureValue Control Test

**Compare:** `capture_20250930_131830.jpg` (EV 0.0) vs `capture_20250930_131831.jpg` (EV +0.3)

✓ **Expected:** EV +0.3 image should be noticeably brighter
✓ **Look for:** ~1/3 stop brighter = subtle but visible difference
✗ **Problem if:** Images look identical (control not working)

### 2. ISO Noise Comparison

**Compare:** `capture_20250930_131828.jpg` (ISO 200) vs `capture_20250930_131833.jpg` (ISO 800)

✓ **Expected:** ISO 800 has more visible noise/grain
✓ **Look at:** Smooth areas (sky, walls, shadows)
✓ **Question:** Is ISO 800 acceptable quality for golden hour?

### 3. Overall Image Quality (All Images)

#### Sharpness

- [ ] Focus is sharp (not blurry)
- [ ] Fine details visible
- [ ] No motion blur

#### Exposure

- [ ] No blown highlights (pure white areas)
- [ ] Shadow detail visible (not pure black)
- [ ] Good contrast and tonal range

#### Color

- [ ] Colors look natural (not oversaturated)
- [ ] White balance correct
- [ ] No weird color casts

#### Artifacts

- [ ] No banding in smooth areas
- [ ] No JPEG compression artifacts
- [ ] No lens issues (vignetting, distortion)

### 4. 16MP Resolution Quality

- [ ] Image size: 4656×3496 pixels (verify in image properties)
- [ ] File size: 1.4-1.8MB (reasonable for 16MP JPEG)
- [ ] Can zoom in and see fine detail
- [ ] Quality sufficient for large prints/displays

## Decision Points

### ✅ If Images Look Good:

1. ExposureValue control is working correctly
2. ISO range (200-800) provides acceptable quality
3. Camera is properly focused and configured
4. Ready to proceed with fixes and golden hour testing

### ⚠️ If Issues Found:

**Brightness identical (EV +0.3 has no effect):**

- CRITICAL-2 confirmed: ExposureValue not actually working
- Need to validate camera controls before proceeding

**ISO 800 too noisy:**

- May need to limit max ISO to 400 or 600
- Consider HDR mode for noise reduction

**Focus issues:**

- Need to set LensPosition or AfMode
- May require manual focus adjustment

**Color/exposure problems:**

- May need to adjust white balance (AwbMode)
- Consider tuning file adjustments

## Next Actions Based on Review

Record your observations here and we'll prioritize fixes accordingly.

**ExposureValue Working?** (Y/N): **\_**

**ISO 800 Acceptable?** (Y/N): **\_**

**Overall Quality Rating (1-10):** **\_**

**Issues Found:**

- [ ]
- [ ]
- [ ]

**Priority Fixes:**

1.
2.
3.
