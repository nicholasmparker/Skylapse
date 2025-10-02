# Timelapse A/B Testing Plan

## Strategy: Round-Robin Multi-Algorithm Capture

Capture **4 different setting profiles** in rotation, saving to separate folders.
Each profile will produce its own timelapse for side-by-side comparison.

---

## Profile Definitions

### Profile A: Auto Everything (Baseline)

**Folder:** `~/skylapse-images/profile-a-auto/`
**Settings:**

- AfMode: 2 (Continuous autofocus)
- AwbMode: 0 (Auto white balance)
- ExposureMode: Auto (let camera decide ISO/shutter)
  **Purpose:** Baseline - what camera thinks is best

### Profile B: Fixed Daylight WB + Auto Exposure

**Folder:** `~/skylapse-images/profile-b-daylight-wb/`
**Settings:**

- AfMode: 2 (Continuous autofocus)
- AwbMode: 1 (Daylight white balance - consistent color)
- ExposureMode: Auto (camera decides ISO/shutter)
  **Purpose:** Test if fixed WB prevents color flicker

### Profile C: Manual Ramping (Our Algorithm)

**Folder:** `~/skylapse-images/profile-c-manual-ramp/`
**Settings:**

- AfMode: 2 (Continuous autofocus)
- AwbMode: 1 (Daylight white balance)
- Exposure: Manual ramping based on time from sunrise
  **Purpose:** Our intelligent exposure curve

### Profile D: HDR Mode

**Folder:** `~/skylapse-images/profile-d-hdr/`
**Settings:**

- AfMode: 2 (Continuous autofocus)
- AwbMode: 1 (Daylight white balance)
- HdrMode: 1 (Single exposure HDR)
- Exposure: Manual ramping
  **Purpose:** Test if HDR improves dynamic range during golden hour

---

## Capture Schedule

**Interval:** 30 seconds
**Rotation:** A → B → C → D → A → B → C → D...

**Example Timeline:**

```
00:00 - Profile A capture → folder A
00:30 - Profile B capture → folder B
01:00 - Profile C capture → folder C
01:30 - Profile D capture → folder D
02:00 - Profile A capture → folder A
02:30 - Profile B capture → folder B
... (repeat for 60 minutes)
```

**Result:** Each profile gets 15 frames over 60 minutes (1 frame every 2 minutes)

---

## Implementation

### Backend Changes Needed:

1. **Add profile rotation logic** to scheduler
2. **Track current profile** (A/B/C/D counter)
3. **Calculate settings per profile** (different logic for each)
4. **Send profile name** to Pi in capture request
5. **Pi saves to correct folder** based on profile

### Pi Changes Needed:

1. **Accept profile parameter** in capture request
2. **Create folder structure** (~skylapse-images/profile-X/)
3. **Save to correct folder** based on profile name

---

## After Sunrise Test

### Create 4 Separate Timelapses:

```bash
# Profile A - Auto Everything
ffmpeg -framerate 30 -pattern_type glob -i 'profile-a-auto/*.jpg' \
  -c:v libx264 -pix_fmt yuv420p timelapse-a-auto.mp4

# Profile B - Daylight WB
ffmpeg -framerate 30 -pattern_type glob -i 'profile-b-daylight-wb/*.jpg' \
  -c:v libx264 -pix_fmt yuv420p timelapse-b-daylight-wb.mp4

# Profile C - Manual Ramping
ffmpeg -framerate 30 -pattern_type glob -i 'profile-c-manual-ramp/*.jpg' \
  -c:v libx264 -pix_fmt yuv420p timelapse-c-manual-ramp.mp4

# Profile D - HDR
ffmpeg -framerate 30 -pattern_type glob -i 'profile-d-hdr/*.jpg' \
  -c:v libx264 -pix_fmt yuv420p timelapse-d-hdr.mp4
```

### Compare:

- Which has best color consistency?
- Which has smoothest exposure transitions?
- Which has best dynamic range (detail in highlights + shadows)?
- Which looks most cinematic?

---

## Pros/Cons

### ✅ Advantages:

- **Scientifically compare** different approaches
- **Same lighting conditions** for all profiles (captured simultaneously)
- **Prove which works best** with real data
- **No guessing** - see actual results

### ⚠️ Considerations:

- Each profile gets **1/4 the frames** (15 instead of 60)
- Need **4x storage space**
- Slightly **more complex** to implement
- May want to adjust interval (60s instead of 30s to get more frames per profile)

---

## Alternative: 2 Profiles Instead of 4

If 4 is too many, start with just 2:

### Profile A: Auto WB + Auto Exposure (Safe)

### Profile B: Daylight WB + Manual Ramping (Quality)

**Schedule:** Alternate every 30s
**Result:** Each gets 30 frames over 60 minutes

---

## Recommendation

**Start with 2 profiles** for first test:

1. **Auto** (baseline - what camera wants)
2. **Manual** (our algorithm - what we think is best)

If both look good but can't decide, add more profiles.
If one is clearly better, use that going forward.

**Next Steps:**

1. Implement profile rotation in backend
2. Update Pi to accept profile parameter
3. Test during sunset today
4. Review results and pick winner
