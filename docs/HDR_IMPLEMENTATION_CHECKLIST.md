# HDR Exposure Stacking - Implementation & QA Checklist

**Feature:** Automated exposure bracketing and HDR merge for professional golden hour timelapses
**Branch:** `feature/image-stacking`
**Target:** Production deployment for next sunrise capture

---

## Phase 1: Foundation & Core Components

### 1.1 Refactor HDR Merge Script

- [ ] **IMPL:** Convert `scripts/hdr-merge.py` into importable module
  - [ ] Move core functions to `backend/hdr_processing.py`
  - [ ] Keep CLI wrapper in `scripts/hdr-merge.py` for manual use
  - [ ] Add error handling for invalid/corrupted images
  - [ ] Add logging with structured output

- [ ] **QA:** Test HDR merge module
  - [ ] Unit test: `merge_hdr_mertens()` with valid 3-image set
  - [ ] Unit test: Error handling for missing images
  - [ ] Unit test: Error handling for mismatched resolutions
  - [ ] Manual test: Merge actual sunset brackets, verify quality
  - [ ] Performance test: Measure merge time on worker hardware

**Acceptance Criteria:**
- ✅ Module can be imported: `from backend.hdr_processing import merge_hdr_mertens`
- ✅ Merges 3 brackets in <2 seconds
- ✅ Produces visually superior HDR compared to single exposure

---

### 1.2 Database Schema Updates

- [ ] **IMPL:** Add HDR tracking columns to captures table
  ```sql
  ALTER TABLE captures ADD COLUMN is_bracket BOOLEAN DEFAULT FALSE;
  ALTER TABLE captures ADD COLUMN bracket_index INTEGER;  -- 0, 1, 2 for under/normal/over
  ALTER TABLE captures ADD COLUMN is_hdr_result BOOLEAN DEFAULT FALSE;
  ALTER TABLE captures ADD COLUMN hdr_result_id INTEGER REFERENCES captures(id);
  ALTER TABLE captures ADD COLUMN source_bracket_ids TEXT;  -- JSON: [id1, id2, id3]
  ALTER TABLE captures ADD COLUMN bracket_ev_offset REAL;  -- -2.0, 0.0, +2.0
  ```

- [ ] **IMPL:** Create database migration script
  - [ ] `backend/migrations/add_hdr_columns.sql`
  - [ ] Apply to local dev database
  - [ ] Apply to dagon production database

- [ ] **QA:** Verify schema changes
  - [ ] Test insert bracket capture with new columns
  - [ ] Test insert HDR result with source_bracket_ids
  - [ ] Test foreign key constraint (hdr_result_id references captures)
  - [ ] Query test: Find all brackets for a session
  - [ ] Query test: Find HDR result for a bracket set

**Acceptance Criteria:**
- ✅ All new columns exist in captures table
- ✅ Can record brackets with EV offsets
- ✅ Can link brackets to merged HDR result
- ✅ Queries retrieve correct relationships

---

### 1.3 Pi Bracket Capture Endpoint

- [ ] **IMPL:** Add `/capture-bracket` endpoint to `pi/main.py`
  - [ ] Accept `bracket_exposures` list (e.g., [-2.0, 0.0, +2.0])
  - [ ] Capture N images with EV offsets
  - [ ] Name files with bracket index: `capture_YYYYMMDD_HHMMSS_bracket0.jpg`
  - [ ] Return list of filenames and metadata
  - [ ] Add logging for each bracket capture

- [ ] **IMPL:** Update `CaptureSettings` model
  - [ ] Add `bracket_exposures: Optional[List[float]]` field
  - [ ] Validation: EVs must be in ascending order

- [ ] **QA:** Test Pi bracket endpoint
  - [ ] API test: POST `/capture-bracket` with 3 EVs
  - [ ] Verify 3 separate images captured
  - [ ] Verify filenames include bracket index
  - [ ] Verify EXIF data shows different exposure compensation
  - [ ] Verify images are visually different (brightness levels)
  - [ ] Test error: Invalid EV values (too extreme)
  - [ ] Test error: Empty bracket_exposures list

**Acceptance Criteria:**
- ✅ Endpoint captures N brackets in sequence
- ✅ Files named with bracket index
- ✅ Each image has correct EV offset applied
- ✅ Total capture time: <3 seconds for 3 brackets

**Test Command:**
```bash
curl -X POST http://helios.local:8080/capture-bracket \
  -H "Content-Type: application/json" \
  -d '{
    "bracket_exposures": [-2.0, 0.0, 2.0],
    "iso": 100,
    "shutter_speed": "1/500",
    "profile": "d"
  }'
```

---

## Phase 2: Backend Orchestration

### 2.1 HDR Configuration Schema

- [ ] **IMPL:** Add HDR settings to `backend/config.json`
  - [ ] Add `hdr_enabled: bool` to profile schema
  - [ ] Add `bracket_exposures: [float]` to profile schema
  - [ ] Add `bracket_count: int` (derived from exposures length)
  - [ ] Update sunrise/sunset profiles with HDR settings

- [ ] **IMPL:** Update config validator
  - [ ] Validate `hdr_enabled` is boolean
  - [ ] Validate `bracket_exposures` is list of floats
  - [ ] Validate bracket_exposures length matches bracket_count
  - [ ] Validate EVs are in ascending order

- [ ] **QA:** Test config validation
  - [ ] Valid config: HDR enabled with 3 brackets
  - [ ] Invalid config: hdr_enabled=true but no bracket_exposures
  - [ ] Invalid config: bracket_exposures not ascending
  - [ ] Reload config test: Changes applied without restart

**Acceptance Criteria:**
- ✅ Profiles can enable/disable HDR independently
- ✅ Custom bracket ranges per profile (-1.5/+1.5 vs -2/+2)
- ✅ Config validation catches errors before deployment

**Example Config:**
```json
{
  "d": {
    "name": "Golden Hour HDR",
    "hdr_enabled": true,
    "bracket_exposures": [-2.0, 0.0, 2.0],
    "bracket_count": 3,
    ...
  }
}
```

---

### 2.2 Backend Bracket Orchestration

- [ ] **IMPL:** Modify `backend/main.py` capture logic
  - [ ] Detect if profile has `hdr_enabled=true`
  - [ ] If HDR: Call Pi `/capture-bracket` instead of `/capture`
  - [ ] Download all bracket images
  - [ ] Record each bracket in database with `is_bracket=true`
  - [ ] Store bracket metadata (EV offset, bracket_index)

- [ ] **IMPL:** Add `capture_with_hdr()` function
  - [ ] Build bracket request with profile settings
  - [ ] Send to Pi and await response
  - [ ] Download each bracket image
  - [ ] Save to `/data/captures/` directory
  - [ ] Return list of capture IDs

- [ ] **QA:** Test backend orchestration
  - [ ] Mock test: HDR profile triggers bracket capture
  - [ ] Mock test: Non-HDR profile uses single capture
  - [ ] Integration test: End-to-end bracket capture and download
  - [ ] Verify all 3 brackets saved to disk
  - [ ] Verify database records created correctly
  - [ ] Test error: Pi fails to capture (handle gracefully)
  - [ ] Test error: Network timeout during download

**Acceptance Criteria:**
- ✅ HDR profiles automatically capture brackets
- ✅ All brackets downloaded and recorded
- ✅ Graceful error handling if Pi capture fails
- ✅ Non-HDR profiles unaffected (backward compatible)

---

### 2.3 HDR Job Queue

- [ ] **IMPL:** Add HDR merge job type to `backend/tasks.py`
  - [ ] Define `HDRMergeJob` schema
  - [ ] Add to job queue after bracket capture completes
  - [ ] Include: bracket_ids, session_id, profile

- [ ] **IMPL:** Queue management
  - [ ] Add job to Redis queue after downloading brackets
  - [ ] Set priority (HDR merge high priority)
  - [ ] Add timeout (fail if merge takes >30 seconds)

- [ ] **QA:** Test job queueing
  - [ ] Unit test: Create HDR job with bracket IDs
  - [ ] Integration test: Job appears in queue after capture
  - [ ] Test error: Duplicate job prevention
  - [ ] Test error: Invalid bracket IDs

**Acceptance Criteria:**
- ✅ HDR jobs queued immediately after bracket download
- ✅ Jobs include all necessary metadata
- ✅ Queue monitoring shows pending HDR jobs

---

## Phase 3: Worker Processing

### 3.1 HDR Merge Worker Task

- [ ] **IMPL:** Add `process_hdr_merge()` task handler
  - [ ] Retrieve bracket capture records from database
  - [ ] Load bracket images from disk
  - [ ] Call `hdr_processing.merge_hdr_mertens()`
  - [ ] Save merged HDR image
  - [ ] Record HDR result in database
  - [ ] Update brackets to reference HDR result
  - [ ] Clean up bracket images (optional)

- [ ] **IMPL:** Error handling and retries
  - [ ] Retry on transient errors (disk full, etc.)
  - [ ] Mark job as failed after 3 retries
  - [ ] Log detailed error information
  - [ ] Alert on repeated failures

- [ ] **QA:** Test worker processing
  - [ ] Unit test: Merge task with 3 valid brackets
  - [ ] Unit test: Error handling for corrupted bracket
  - [ ] Integration test: Full queue → process → result
  - [ ] Performance test: Measure processing time
  - [ ] Load test: Queue 10 HDR jobs, verify all process
  - [ ] Test error: Missing bracket file
  - [ ] Test error: OpenCV merge failure

**Acceptance Criteria:**
- ✅ Worker processes HDR jobs from queue
- ✅ Merged images saved with correct naming
- ✅ Database updated with HDR results
- ✅ Processing completes in <5 seconds per job
- ✅ Failed jobs logged with detailed errors

---

### 3.2 Bracket Cleanup

- [ ] **IMPL:** Add cleanup task after successful merge
  - [ ] Delete individual bracket images from disk
  - [ ] Keep only merged HDR result
  - [ ] Update database to mark brackets as deleted
  - [ ] Log disk space reclaimed

- [ ] **IMPL:** Configuration option
  - [ ] Add `cleanup_brackets: bool` to config
  - [ ] Default: `true` (save disk space)
  - [ ] Option to keep brackets for debugging

- [ ] **QA:** Test cleanup
  - [ ] Verify brackets deleted after merge
  - [ ] Verify HDR result remains
  - [ ] Verify database integrity (references still valid)
  - [ ] Test with `cleanup_brackets=false` (keep brackets)

**Acceptance Criteria:**
- ✅ Brackets deleted after successful merge
- ✅ Disk space savings: ~66% (keep 1 instead of 3 images)
- ✅ Option to disable cleanup for debugging

---

## Phase 4: Timelapse Integration

### 4.1 Timelapse Generation with HDR

- [ ] **IMPL:** Update `get_session_images()` query
  - [ ] Prioritize HDR results over individual captures
  - [ ] For captures with `hdr_result_id`: use HDR image
  - [ ] For captures without: use original image
  - [ ] Ensure correct chronological order

- [ ] **IMPL:** Modify timelapse generation logic
  - [ ] Query returns mixed list (HDR + regular captures)
  - [ ] FFmpeg processes all images in sequence
  - [ ] Log which images are HDR vs regular

- [ ] **QA:** Test timelapse generation
  - [ ] Unit test: Query returns HDR images correctly
  - [ ] Integration test: Generate timelapse with mixed images
  - [ ] Verify HDR images appear in correct sequence
  - [ ] Verify smooth playback (no jumps or glitches)
  - [ ] Visual test: HDR portions have superior quality
  - [ ] Test edge case: Session with all HDR
  - [ ] Test edge case: Session with no HDR
  - [ ] Test edge case: Session with partial HDR (some failed merges)

**Acceptance Criteria:**
- ✅ Timelapse uses HDR images where available
- ✅ Smooth playback, correct chronological order
- ✅ Visual improvement obvious in HDR sections
- ✅ Graceful fallback if HDR merge fails

---

### 4.2 Dashboard Updates

- [ ] **IMPL:** Show HDR status in dashboard
  - [ ] Badge on capture thumbnails: "HDR" or "Bracket"
  - [ ] Metadata modal shows bracket info
  - [ ] Link to view source brackets

- [ ] **IMPL:** HDR processing status
  - [ ] Show "Processing HDR..." for queued jobs
  - [ ] Show "HDR Ready" when merge completes
  - [ ] Show error if merge failed

- [ ] **QA:** Test dashboard display
  - [ ] Verify HDR badge appears on merged images
  - [ ] Verify bracket badge on individual brackets
  - [ ] Click through to metadata, verify details
  - [ ] Test status updates (pending → processing → complete)

**Acceptance Criteria:**
- ✅ Easy to identify HDR images in dashboard
- ✅ Clear status for processing state
- ✅ Access to source brackets for debugging

---

## Phase 5: Integration Testing

### 5.1 End-to-End Workflow

- [ ] **TEST:** Complete HDR capture flow
  1. [ ] Enable HDR on profile D
  2. [ ] Trigger scheduled capture
  3. [ ] Verify Pi captures 3 brackets
  4. [ ] Verify backend downloads all brackets
  5. [ ] Verify worker merges HDR
  6. [ ] Verify HDR result recorded in database
  7. [ ] Verify timelapse uses HDR image
  8. [ ] Verify brackets cleaned up

- [ ] **TEST:** Mixed session (HDR + regular captures)
  1. [ ] Schedule with 2 profiles: one HDR, one regular
  2. [ ] Verify both capture correctly
  3. [ ] Verify timelapse includes both types
  4. [ ] Verify visual quality difference

- [ ] **TEST:** Error recovery
  1. [ ] Simulate Pi failure during bracket capture
  2. [ ] Verify graceful error handling
  3. [ ] Verify system recovers for next capture
  4. [ ] Simulate worker crash during merge
  5. [ ] Verify job retries and completes

**Acceptance Criteria:**
- ✅ Complete flow works end-to-end
- ✅ No data loss or corruption
- ✅ Errors handled gracefully
- ✅ System self-recovers from failures

---

### 5.2 Performance Validation

- [ ] **TEST:** Timing under load
  - [ ] Measure: Pi bracket capture time (target: <3s)
  - [ ] Measure: Backend download time (target: <2s)
  - [ ] Measure: Worker merge time (target: <2s)
  - [ ] Measure: Total latency (capture → HDR ready, target: <10s)

- [ ] **TEST:** Queue processing capacity
  - [ ] Queue 20 HDR jobs simultaneously
  - [ ] Verify all process without queue buildup
  - [ ] Monitor worker CPU/memory usage

- [ ] **TEST:** Disk space usage
  - [ ] Measure space used per HDR capture
  - [ ] Verify cleanup reclaims space
  - [ ] Project disk usage for 24-hour capture session

**Acceptance Criteria:**
- ✅ Capture timing meets targets
- ✅ Worker keeps up with capture rate
- ✅ Disk usage sustainable for production

---

### 5.3 Quality Validation

- [ ] **TEST:** Visual quality comparison
  - [ ] Capture same scene: 3 individual + 1 HDR merge
  - [ ] Side-by-side comparison in image viewer
  - [ ] Verify HDR shows superior dynamic range
  - [ ] Verify no artifacts (halos, ghosting)

- [ ] **TEST:** Sunrise/sunset test captures
  - [ ] Enable HDR on profile D
  - [ ] Capture during actual sunrise
  - [ ] Generate timelapse
  - [ ] Compare to previous non-HDR sunrise timelapse
  - [ ] **Success metric: "Holy shit, that looks professional!"**

**Acceptance Criteria:**
- ✅ HDR images visibly better than single exposure
- ✅ No visible artifacts or quality degradation
- ✅ Sunrise timelapse has full tonal range (sky + landscape)

---

## Phase 6: Production Deployment

### 6.1 Pre-Deployment Checklist

- [ ] **VERIFY:** All tests passing
- [ ] **VERIFY:** Database migrations applied to production
- [ ] **VERIFY:** Config updated with HDR profiles
- [ ] **VERIFY:** Worker has OpenCV dependencies
- [ ] **VERIFY:** Sufficient disk space for HDR captures

- [ ] **DEPLOY:** Pi code
  - [ ] Deploy updated `pi/main.py` to helios
  - [ ] Restart Pi service
  - [ ] Verify `/capture-bracket` endpoint available

- [ ] **DEPLOY:** Backend/Worker code
  - [ ] Build new Docker images with HDR code
  - [ ] Deploy to dagon
  - [ ] Restart backend and worker services
  - [ ] Verify HDR processing available

---

### 6.2 Production Monitoring

- [ ] **MONITOR:** First production run
  - [ ] Watch sunrise capture in real-time
  - [ ] Monitor worker queue (no buildup)
  - [ ] Check logs for errors
  - [ ] Verify HDR images generated

- [ ] **MONITOR:** Metrics
  - [ ] Capture success rate (target: >95%)
  - [ ] HDR merge success rate (target: >98%)
  - [ ] Average processing time
  - [ ] Disk usage trend

- [ ] **MONITOR:** Quality checks
  - [ ] Review first HDR timelapse
  - [ ] Check for artifacts or issues
  - [ ] Compare to non-HDR timelapse

**Acceptance Criteria:**
- ✅ Production deployment successful
- ✅ No errors or crashes
- ✅ HDR captures generating correctly
- ✅ Quality meets expectations

---

### 6.3 Tuning and Optimization

- [ ] **TUNE:** Bracket EV ranges
  - [ ] Test different ranges: ±1.5, ±2.0, ±2.5
  - [ ] Evaluate which produces best results
  - [ ] Update config with optimal values

- [ ] **TUNE:** Capture intervals
  - [ ] Test 3s, 4s, 5s intervals
  - [ ] Balance smoothness vs HDR processing time
  - [ ] Update schedule intervals

- [ ] **TUNE:** Merge algorithm parameters
  - [ ] Experiment with Mertens contrast/saturation/exposure weights
  - [ ] Test alternative algorithms (Debevec, etc.)
  - [ ] Select best for landscape timelapses

**Acceptance Criteria:**
- ✅ Optimal settings determined through testing
- ✅ Configuration updated with tuned values
- ✅ Maximum visual quality achieved

---

## Success Criteria (Overall)

### Technical Success:
- ✅ All implementation tasks complete
- ✅ All QA tests passing
- ✅ Production deployment stable
- ✅ Performance targets met

### Quality Success:
- ✅ HDR images demonstrate clear dynamic range improvement
- ✅ No visible artifacts or quality degradation
- ✅ Sunrise/sunset timelapses look professional

### User Success:
- ✅ Nick reaction: "Holy shit, that looks professional!"
- ✅ Timelapses worthy of sharing/showcasing
- ✅ Feature becomes permanent part of Skylapse workflow

---

## Risk Management

### High Risk Items:
1. **Worker processing can't keep up** → Monitor queue depth, add capacity if needed
2. **Disk space fills up** → Aggressive cleanup, compress older captures
3. **Motion blur from clouds** → Test with alignment, add deghosting if needed

### Mitigation Strategies:
- Start with single HDR-enabled profile (limit scope)
- Monitor first production runs closely
- Quick rollback plan: disable `hdr_enabled` in config

---

## Next Steps

1. **Review this checklist** with Nick
2. **Start Phase 1:** Refactor HDR merge script
3. **Iterate through phases** with testing at each step
4. **Deploy to production** for next sunrise capture
5. **Celebrate** when we see those professional timelapses! 🎉

---

**Last Updated:** October 9, 2025
**Branch:** `feature/image-stacking`
**Tracking:** Use todo list to track progress through checklist
