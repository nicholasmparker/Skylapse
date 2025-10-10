# Exposure Stacking (HDR) - Design Document

**Goal:** Create professional, striking landscape timelapses with full dynamic range during golden hour

**Date:** October 9, 2025
**Status:** Design Phase
**Priority:** High - Maximum visual impact for sunrise/sunset captures

---

## The Vision: Professional Golden Hour Timelapses

**The Problem We're Solving:**

During sunrise and sunset, we face the photographer's eternal dilemma:
- Expose for the vibrant sky → dark, muddy foreground
- Expose for the landscape → washed out, blown sky
- Middle ground exposure → mediocre on both

**Amateur timelapse:** One or the other looks good
**Professional timelapse:** Everything looks amazing - that's HDR

**The Solution:**

Capture multiple exposures at different brightness levels (brackets) and intelligently merge them:
- **Underexposed (-2 EV):** Captures rich sky detail and color
- **Normal (0 EV):** Balanced midtones
- **Overexposed (+2 EV):** Reveals shadow detail in landscape

Result: Every frame has the full tonal range - vibrant sky AND detailed foreground.

---

## Three Types of Stacking (Clarification)

We have research on three different techniques. Each serves a different purpose:

### 1. **Exposure Stacking (HDR)** ← THIS IS WHAT WE'RE BUILDING

**Purpose:** Expand dynamic range - capture bright and dark areas in same scene
**Method:** Bracket exposures (underexposed, normal, overexposed) and merge
**Best For:** Sunrise/sunset when you have bright skies and dark landscapes
**Visual Impact:** ⭐⭐⭐⭐⭐ (Highest - this creates "wow" factor)
**Implementation:** We already have `hdr-merge.py` with Mertens fusion!

### 2. **Noise Reduction Stacking** (Documented in `image-stacking-research.md`)

**Purpose:** Reduce sensor noise by averaging multiple identical exposures
**Method:** Capture 5+ images at SAME settings, average them (√N improvement)
**Best For:** Low-light/high-ISO situations
**Visual Impact:** ⭐⭐ (Subtle - cleaner images but less dramatic)
**Implementation:** Simple numpy averaging (already researched)

### 3. **Focus Stacking**

**Purpose:** Extend depth of field - everything sharp from foreground to infinity
**Method:** Capture images at different focus distances, blend sharpest areas
**Best For:** Macro or scenes with very close foreground objects
**Visual Impact:** ⭐⭐⭐ (Nice for specific scenes)
**Implementation:** Complex alignment + depth-based blending

**Decision: Start with Exposure Stacking (HDR) for maximum impact on our sunrise/sunset timelapses.**

---

## Existing Work We're Building On

### ✅ We Already Have:

1. **HDR Merge Algorithm** (`scripts/hdr-merge.py`)
   - Mertens exposure fusion (used by professional timelapse photographers)
   - Natural-looking HDR without the "HDR look"
   - Takes 3 bracketed JPEGs → outputs merged HDR JPEG
   - Tested and working

2. **Exposure Bracketing Capability**
   - `bracket_count` exists in config (currently set to 1)
   - `exposure_compensation` working and tested
   - Pi can already capture at different exposure values

3. **Noise Reduction Research** (`agent-comms/image-stacking-research.md`)
   - Timing analysis for burst capture
   - Performance estimates for Pi processing
   - Interval adjustment recommendations
   - This applies to our HDR implementation too!

### 🎯 What We Need to Build:

1. **Automated Exposure Bracketing** - Pi captures 3 exposures automatically
2. **HDR Processing Pipeline** - Backend worker merges brackets into HDR
3. **Timelapse Integration** - Use HDR images in final timelapse video
4. **Profile Configuration** - Per-profile HDR settings (some profiles use HDR, some don't)

---

## Architecture Design

### The Complete Flow (Backend → Pi → Worker → Timelapse)

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. BACKEND: Schedule Trigger (Sunrise/Sunset)                  │
│    - Checks config: profile has hdr_enabled=true               │
│    - Calculates bracket exposures: [-2 EV, 0 EV, +2 EV]        │
│    - Sends 3 capture requests to Pi (sequential)               │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. PI: Exposure Bracket Capture                                │
│    - Capture 1: EV -2.0 (underexposed) → bracket0.jpg          │
│    - Capture 2: EV  0.0 (normal)       → bracket1.jpg          │
│    - Capture 3: EV +2.0 (overexposed)  → bracket2.jpg          │
│    - Returns all 3 filenames to backend                        │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. BACKEND: Download Brackets & Queue HDR Job                  │
│    - Downloads all 3 bracket images                            │
│    - Creates database record: hdr_stack (references 3 captures)│
│    - Queues HDR merge job for worker                           │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. WORKER: HDR Merge Processing                                │
│    - Reads 3 bracket images                                    │
│    - Calls existing hdr-merge.py (Mertens fusion)              │
│    - Saves merged HDR image                                    │
│    - Updates database with HDR result filename                 │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. TIMELAPSE GENERATION: Use HDR Images                        │
│    - Query for session images                                  │
│    - For captures with HDR result: use HDR image               │
│    - For normal captures: use original image                   │
│    - Generate timelapse video with professional quality!       │
└─────────────────────────────────────────────────────────────────┘
```

### Why This Architecture?

**Separation of Concerns:**
- **Pi:** Fast, simple capture (just take 3 photos)
- **Worker:** Heavy lifting (HDR merge with OpenCV)
- **Backend:** Orchestration and database tracking

**Scalability:**
- Worker can process HDR stacks in parallel (async queue)
- Pi isn't blocked waiting for merge to complete
- Can queue many stacks and process them as fast as hardware allows

**Flexibility:**
- Not all captures need HDR (midday doesn't benefit)
- Can enable/disable per profile
- Can use different bracket counts (3, 5, 7 exposures)

---

## Implementation Details

### Phase 1: Pi Exposure Bracketing

**File:** `pi/main.py`

**New Endpoint:** `/capture-bracket`

```python
@app.post("/capture-bracket")
async def capture_bracket(settings: CaptureSettings):
    """
    Capture exposure bracket for HDR merge.

    Takes settings with bracket_exposures list: [-2.0, 0.0, +2.0]
    Returns list of filenames.
    """
    bracket_filenames = []

    for i, ev_offset in enumerate(settings.bracket_exposures):
        # Adjust exposure compensation for this bracket
        bracket_settings = settings.copy()
        bracket_settings.exposure_compensation += ev_offset

        # Capture with adjusted EV
        result = await capture_photo(bracket_settings)

        # Rename to indicate bracket number
        base_name = result["filename"].replace(".jpg", "")
        bracket_filename = f"{base_name}_bracket{i}.jpg"
        os.rename(result["filepath"], bracket_filename)

        bracket_filenames.append(bracket_filename)

        logger.info(f"📸 Bracket {i}: EV{ev_offset:+.1f} → {bracket_filename}")

    return {
        "filenames": bracket_filenames,
        "count": len(bracket_filenames)
    }
```

**Timing Consideration:**
- 3 captures @ ~1 sec each = ~3 seconds total
- Acceptable for 4-5 second intervals (still smooth timelapse)

### Phase 2: Backend Bracket Orchestration

**File:** `backend/main.py`

**Modified capture logic:**

```python
async def capture_with_hdr(profile_settings, session_id):
    """
    Capture with HDR if profile has hdr_enabled=true.
    """
    hdr_enabled = profile_settings.get("hdr_enabled", False)

    if hdr_enabled:
        # Send bracket capture request to Pi
        bracket_exposures = profile_settings.get("bracket_exposures", [-2.0, 0.0, +2.0])

        response = await http_client.post(
            f"{PI_URL}/capture-bracket",
            json={
                **profile_settings,
                "bracket_exposures": bracket_exposures
            }
        )

        bracket_filenames = response.json()["filenames"]

        # Download all 3 bracket images
        bracket_ids = []
        for filename in bracket_filenames:
            image_data = await http_client.get(f"{PI_URL}/images/{profile}/{filename}")

            # Save to captures directory
            filepath = f"/data/captures/{filename}"
            with open(filepath, "wb") as f:
                f.write(image_data.content)

            # Record in database
            capture_id = db.record_capture(
                filename=filename,
                session_id=session_id,
                is_bracket=True,
                ...
            )
            bracket_ids.append(capture_id)

        # Queue HDR merge job
        hdr_job = {
            "type": "hdr_merge",
            "bracket_ids": bracket_ids,
            "session_id": session_id,
            "profile": profile_settings["profile"]
        }
        await queue_hdr_merge(hdr_job)

        logger.info(f"✓ HDR bracket captured: {len(bracket_ids)} exposures")

    else:
        # Normal single capture (existing logic)
        await capture_single(profile_settings, session_id)
```

### Phase 3: Worker HDR Processing

**File:** `backend/tasks.py`

**New task handler:**

```python
async def process_hdr_merge(job):
    """
    Process HDR merge job using existing hdr-merge.py script.
    """
    bracket_ids = job["bracket_ids"]
    session_id = job["session_id"]

    # Get bracket image paths from database
    bracket_paths = []
    for capture_id in bracket_ids:
        capture = db.get_capture(capture_id)
        bracket_paths.append(f"/data/captures/{capture['filename']}")

    # Sort to ensure correct order (under, normal, over)
    bracket_paths.sort()

    # Call existing HDR merge script
    output_filename = f"hdr_{session_id}_{int(time.time())}.jpg"
    output_path = f"/data/captures/{output_filename}"

    # Import and use existing merge function
    from scripts.hdr_merge import merge_hdr_mertens, load_bracket_images

    images = load_bracket_images(*bracket_paths)
    hdr_image = merge_hdr_mertens(images)

    cv2.imwrite(output_path, hdr_image)

    # Record HDR result in database
    hdr_capture_id = db.record_capture(
        filename=output_filename,
        session_id=session_id,
        is_hdr_result=True,
        source_bracket_ids=bracket_ids,
        ...
    )

    # Update bracket captures to reference HDR result
    for bracket_id in bracket_ids:
        db.update_capture(bracket_id, hdr_result_id=hdr_capture_id)

    logger.info(f"✓ HDR merged: {output_filename} from {len(bracket_ids)} brackets")

    return hdr_capture_id
```

### Phase 4: Database Schema

**New columns for `captures` table:**

```sql
ALTER TABLE captures ADD COLUMN is_bracket BOOLEAN DEFAULT FALSE;
ALTER TABLE captures ADD COLUMN is_hdr_result BOOLEAN DEFAULT FALSE;
ALTER TABLE captures ADD COLUMN hdr_result_id INTEGER REFERENCES captures(id);
ALTER TABLE captures ADD COLUMN source_bracket_ids TEXT; -- JSON array
```

**Tracking:**
- Individual bracket images marked with `is_bracket=true`
- Final HDR image marked with `is_hdr_result=true`
- Brackets reference their merged result via `hdr_result_id`
- HDR result references source brackets via `source_bracket_ids`

### Phase 5: Configuration

**File:** `backend/config.json`

**Per-profile HDR settings:**

```json
{
  "profiles": {
    "a": {
      "name": "Full Auto",
      "hdr_enabled": false,
      ...
    },
    "d": {
      "name": "Golden Hour HDR",
      "hdr_enabled": true,
      "bracket_exposures": [-2.0, 0.0, +2.0],
      "bracket_count": 3,
      ...
    },
    "g": {
      "name": "Adaptive with HDR",
      "hdr_enabled": true,
      "bracket_exposures": [-1.5, 0.0, +1.5],
      "bracket_count": 3,
      ...
    }
  },
  "schedules": {
    "sunrise": {
      "interval_seconds": 4,  // Increased for bracket capture time
      ...
    }
  }
}
```

**Key decisions:**
- Not all profiles use HDR (midday doesn't need it)
- Customizable bracket range per profile (±1.5 EV vs ±2.0 EV)
- Intervals adjusted to accommodate bracket capture

---

## Performance & Timing

### Capture Timing (3-bracket HDR):

| Step | Time | Notes |
|------|------|-------|
| Bracket 1 capture | ~0.8s | Underexposed |
| Bracket 2 capture | ~0.8s | Normal |
| Bracket 3 capture | ~0.8s | Overexposed |
| **Total capture** | **~2.5s** | Sequential on Pi |

### Processing Timing (HDR Merge):

| Step | Time | Notes |
|------|------|-------|
| Load 3 images | ~0.3s | Read JPEGs from disk |
| Mertens fusion | ~0.5s | OpenCV on worker |
| JPEG encode | ~0.4s | Write result |
| **Total merge** | **~1.2s** | Async on worker |

### Timelapse Interval:

**Recommendation:**
- **Current intervals:** 2 seconds (too tight for HDR)
- **With HDR:** 4-5 seconds
  - Captures 3 brackets in ~2.5s
  - Leaves buffer for processing variance
  - Still creates smooth timelapse (720 frames/hour @ 4s → 30 sec @ 24fps)

**Quality vs Speed:**
- Slightly fewer frames per timelapse
- Vastly superior image quality
- Professional-grade dynamic range
- **Worth the tradeoff** for sunrise/sunset

---

## Quality Improvements Expected

### Before HDR (Current):

**Sunrise capture at EV 0.0:**
- Sky: Vibrant but some blown highlights
- Mountains: Visible but shadow detail lost
- Overall: Good but compromised

### After HDR (Mertens Fusion):

**3-bracket merge (-2, 0, +2 EV):**
- Sky: Full gradient from bright to dark, no blown highlights
- Mountains: Shadow detail revealed, texture visible
- Foreground: Rich detail even in dark areas
- Overall: **Professional magazine quality**

**Visual impact: Amateur → Pro**

---

## Testing & Validation Plan

### Phase 1: Proof of Concept (Manual)

1. **Manual bracket capture:**
   - Trigger 3 manual captures at different EVs
   - Use existing `hdr-merge.py` script
   - Verify quality improvement

2. **Benchmark timing:**
   - Measure actual Pi capture time for 3 brackets
   - Measure worker merge time
   - Confirm 4-second intervals are sufficient

### Phase 2: Integration Testing

1. **End-to-end workflow:**
   - Enable HDR on one profile
   - Trigger scheduled capture
   - Verify brackets captured, merged, recorded

2. **Database verification:**
   - Confirm bracket images tracked correctly
   - Verify HDR result linked to sources
   - Check timelapse query returns HDR images

### Phase 3: Production Validation

1. **Sunrise/sunset comparison:**
   - Run two profiles side-by-side (HDR vs non-HDR)
   - Generate timelapses from both
   - **Visual comparison: Does HDR deliver the "wow"?**

2. **Performance monitoring:**
   - Worker queue depth (is processing keeping up?)
   - Disk usage (3× more images during bracket periods)
   - Network bandwidth (3× download traffic)

---

## Risk Mitigation

### Risk 1: Processing Can't Keep Up

**Symptom:** Worker queue grows faster than it processes
**Mitigation:**
- Monitor queue depth
- Adjust capture interval if needed
- Add second worker if necessary
- HDR only enabled on sunrise/sunset (limited duration)

### Risk 2: Disk Space

**Impact:** 3× storage during HDR periods
**Mitigation:**
- Delete individual brackets after HDR merge completes
- Keep only merged HDR result
- Cleanup job runs after each session

### Risk 3: Motion Blur (Clouds)

**Impact:** Moving clouds blur when merged
**Mitigation:**
- Test with actual sunrise footage
- Mertens fusion handles some motion better than averaging
- Bracket capture is fast (~2.5s) - minimal cloud movement
- If needed: add alignment step or motion rejection

---

## Success Criteria

**We'll know this is working when:**

1. ✅ Sunrise timelapses have vibrant sky AND detailed landscape
2. ✅ No blown highlights in bright areas
3. ✅ No crushed shadows in dark areas
4. ✅ Smooth timelapse playback (no jitter from varying intervals)
5. ✅ Processing keeps up with capture (queue doesn't grow)
6. ✅ **User reaction: "Holy shit, that looks professional!"**

---

## Implementation Phases (Recommended Order)

### Phase 1: Foundation (Week 1)
- [ ] Refactor `hdr-merge.py` into importable module
- [ ] Add database schema for bracket tracking
- [ ] Implement `/capture-bracket` endpoint on Pi
- [ ] Manual testing: capture brackets, merge manually

### Phase 2: Backend Integration (Week 2)
- [ ] Add HDR configuration to profiles
- [ ] Implement bracket orchestration in backend
- [ ] Queue HDR merge jobs
- [ ] Worker processes HDR merge tasks

### Phase 3: Timelapse Integration (Week 3)
- [ ] Update timelapse generation to use HDR results
- [ ] Add cleanup job (delete brackets after merge)
- [ ] Dashboard shows HDR vs non-HDR captures
- [ ] End-to-end testing

### Phase 4: Production (Week 4)
- [ ] Enable HDR on sunrise/sunset profiles
- [ ] Monitor first production run
- [ ] Tune intervals and bracket EVs
- [ ] Generate first professional-grade timelapse
- [ ] 🎉 **Ship it!**

---

## Future Enhancements (Post-MVP)

### 1. Adaptive Bracketing

**Idea:** Adjust bracket range based on scene analysis
- Wide dynamic range scene: use ±2.5 EV
- Moderate scene: use ±1.5 EV
- Low contrast scene: skip HDR entirely

### 2. Deghosting

**Idea:** Handle moving elements (birds, branches)
- Detect motion between brackets
- Mask out moving areas
- Prevents ghost artifacts

### 3. Multi-Algorithm Support

**Options beyond Mertens:**
- Debevec + Reinhard tone mapping (more "HDR look")
- Mantiuk tone mapping (local contrast)
- Custom exposure fusion weights

### 4. Real-time Preview

**UI Feature:**
- Dashboard shows bracket captures + preview merge
- User can tune EV range before full processing
- A/B comparison slider (HDR vs single exposure)

---

## Conclusion

**Exposure stacking (HDR) is the highest-impact feature for creating professional landscape timelapses.**

We have the foundation (Mertens algorithm, bracketing capability, processing infrastructure). Now we connect the pieces to automate the workflow.

**The result:** Timelapses that rival professional photographers' work, with full tonal range from shadow to highlight during the most dramatic golden hour moments.

**Let's build this.** 🚀

---

**Next:** Review this design document together, refine any details, then start Phase 1 implementation.
