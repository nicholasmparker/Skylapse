# Image Stacking Research & Implementation Plan

**Date:** October 4, 2025
**Status:** Research complete, awaiting verification of camera settings fix before implementation

## Current State

- Config has `stack_images: true` and `stack_count: 5` for sunrise/sunset schedules
- Feature is **NOT implemented** - backend doesn't send stacking parameters to Pi
- Config added Oct 2nd but never connected to capture logic

## Research Findings

### ✅ Why Image Stacking Would Work

1. **Picamera2 Support**

   - Picamera2 fully supports burst capture mode
   - Can rapidly capture multiple frames in sequence
   - Hardware-accelerated on Pi

2. **Noise Reduction Benefits**

   - Averaging N images improves signal-to-noise ratio by √N
   - 5 images = 2.2x SNR improvement (√5 = 2.24)
   - Most beneficial in low-light conditions (sunrise/sunset)

3. **Enhanced Shadow Detail**

   - Multiple exposures reveal details lost in single shots
   - Particularly valuable during golden hour transitions
   - Reduces banding in gradients (sky transitions)

4. **Proven Technique**
   - Same principle as astrophotography stacking
   - Used successfully in landscape timelapse workflows
   - Well-established noise reduction method

### ⚠️ Implementation Challenges

1. **Timing Impact**

   - **Current:** 2-second intervals = 1 capture every 2 seconds
   - **With stacking:** 5 captures + processing ≈ 3-5 seconds per frame
   - **Solution:** Increase interval to 4 seconds OR accept fewer timelapse frames

2. **Processing Requirements**

   - Full-resolution stacking: 5 × (4656×3496 @ 16MP) images
   - **Options:**
     - Process on Pi (adds ~1-2 sec latency, uses CPU/GPU)
     - Send all 5 to backend (5× network traffic, ~25MB per stack)
     - Use Pi GPU acceleration with numpy (recommended)

3. **Motion Blur Consideration**
   - **Risk:** Moving elements (clouds, birds) blur when averaged
   - **Mitigating factors:**
     - Static mountain landscapes = no blur issues
     - Short burst duration (~0.5-1 sec) minimizes cloud movement
     - Your use case is ideal (static landscape timelapses)

### 💡 Ideal Use Case Match

**Why this works perfectly for Skylapse:**

- ✅ Static mountain/landscape subjects (no motion blur)
- ✅ Low-light sunrise/sunset captures (maximum noise reduction benefit)
- ✅ Already using 2-sec intervals (can accommodate 3-4 sec for stacking)
- ✅ Quality over quantity (prefer cleaner images vs. more frames)

## Proposed Implementation

### Phase 1: Pi Capture Logic

**File:** `pi/main.py`

1. **Add stacking parameters to CaptureSettings:**

   ```python
   stack_images: bool = False
   stack_count: int = 1  # Number of images to stack (1 = no stacking)
   ```

2. **Implement burst capture + stacking:**

   ```python
   def capture_stacked_image(camera, settings):
       """Capture multiple images and stack them for noise reduction."""
       import numpy as np

       # Capture burst of images
       frames = []
       for i in range(settings.stack_count):
           frame = camera.capture_array()
           frames.append(frame)

       # Stack using mean averaging (reduces noise)
       stacked = np.mean(frames, axis=0).astype(np.uint8)

       return stacked
   ```

3. **Integrate into capture endpoint:**
   - Check if `stack_images=True` and `stack_count > 1`
   - Use burst capture instead of single shot
   - Process and save stacked result
   - Log stacking info (e.g., "📸 Stacked 5 images")

### Phase 2: Backend Integration

**File:** `backend/exposure.py` (Profile settings)

1. **Pass stacking parameters from config:**

   ```python
   # In _apply_profile_settings():
   settings["stack_images"] = base_settings.get("stack_images", False)
   settings["stack_count"] = base_settings.get("stack_count", 1)
   ```

2. **Update schedule handling:**
   - Read `stack_images` and `stack_count` from schedule config
   - Include in base_settings passed to profile application
   - Forward to Pi capture request

### Phase 3: Interval Adjustment

**File:** `backend/config.json`

- Increase sunrise/sunset intervals from 2→4 seconds to accommodate stacking
- Maintains smooth timelapse while allowing processing time
- Alternative: Keep 2 sec interval but accept ~50% fewer frames during processing

## Performance Estimates

### Timing Breakdown (5-image stack):

- Burst capture: ~0.5-1.0 sec (hardware limited)
- Numpy averaging: ~0.3-0.5 sec (Pi 4 CPU)
- JPEG encoding: ~0.5-1.0 sec (existing)
- **Total:** ~1.5-2.5 seconds

### Recommended Interval:

- **Current:** 2 seconds
- **Recommended with stacking:** 4 seconds
- **Rationale:** Provides buffer for processing variance

## Testing Plan

### Before Implementation:

1. ✅ Verify camera settings fix works (focus, sharpness, etc.)
2. ✅ Capture sunrise with current settings
3. ✅ Confirm profiles A, D, G behave distinctly

### After Implementation:

1. Test burst capture speed (measure actual timing)
2. Compare stacked vs. non-stacked images (noise, detail)
3. Verify timelapse smoothness with 4-sec intervals
4. Monitor Pi CPU/memory usage during stacking

## Next Steps

1. **Wait for verification** - Confirm Oct 4th camera settings fix works correctly
2. **Review sunrise captures** - Check that focus and enhancement settings are applied
3. **Implement stacking** - Add burst capture + numpy averaging to Pi
4. **Test and tune** - Adjust intervals based on actual performance
5. **Deploy** - Roll out to production after validation

## Alternative: Remove Stacking Config

If we decide **NOT** to implement:

- Remove `stack_images` and `stack_count` from `config.json`
- Update config validator to remove unused fields
- Document decision to avoid future confusion

## Recommendation

**IMPLEMENT IT** - The benefits outweigh the complexity:

- Straightforward implementation (~2-3 hours work)
- Significant quality improvement for sunrise/sunset
- Minimal performance impact with 4-sec intervals
- Aligns perfectly with static landscape use case

---

**Author:** Claude
**Next Review:** After Oct 5th sunrise capture verification
