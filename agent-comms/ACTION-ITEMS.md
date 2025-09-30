# Action Items: Sprint 1 Week 1 → Week 2 Transition

**Date:** 2025-09-30
**Status:** READY TO PROCEED TO PI INTEGRATION
**Conditions:** Complete 2 fixes below (4-5 hours)

---

## ✓ MUST DO Before Week 2 Starts

### 1. Fix Schedule Type Duplication [CRITICAL]

**Effort:** 2 hours
**Assignee:** Backend developer
**Priority:** P0 - BLOCKING

**Steps:**

1. Create new file: `/Users/nicholasmparker/Projects/skylapse/backend/schedule_types.py`

   ```python
   from enum import Enum
   from typing import Set

   class ScheduleType(str, Enum):
       SUNRISE = "sunrise"
       DAYTIME = "daytime"
       SUNSET = "sunset"

   SOLAR_SCHEDULES: Set[ScheduleType] = {
       ScheduleType.SUNRISE,
       ScheduleType.SUNSET,
   }

   def is_solar_schedule(schedule_type: str) -> bool:
       try:
           return ScheduleType(schedule_type) in SOLAR_SCHEDULES
       except ValueError:
           return False

   def is_time_schedule(schedule_type: str) -> bool:
       try:
           return ScheduleType(schedule_type) == ScheduleType.DAYTIME
       except ValueError:
           return False
   ```

2. Update `/Users/nicholasmparker/Projects/skylapse/backend/main.py`

   - Import: `from schedule_types import is_solar_schedule, is_time_schedule`
   - Line 169: Replace `if schedule_name in ["sunrise", "sunset"]:` with `if is_solar_schedule(schedule_name):`
   - Line 174: Replace `elif schedule_name == "daytime":` with `elif is_time_schedule(schedule_name):`
   - Line 254: Replace `for schedule_name in ["sunrise", "sunset"]:` with loop + filter
   - Line 277: Same as line 169

3. Update `/Users/nicholasmparker/Projects/skylapse/backend/exposure.py`

   - Import: `from schedule_types import ScheduleType`
   - Lines 45-50: Replace string comparisons with enum values

4. Update `/Users/nicholasmparker/Projects/skylapse/backend/solar.py`

   - Import: `from schedule_types import ScheduleType`
   - Lines 120-124: Replace string comparisons with enum values

5. **Test:**
   ```bash
   cd /Users/nicholasmparker/Projects/skylapse
   docker-compose up backend
   # Check logs for errors
   # Verify scheduler still works
   ```

**Why:** Prevents typo bugs, enables extension, type-safe

---

### 2. Add Pi Health Monitoring [HIGH]

**Effort:** 2 hours
**Assignee:** Backend developer
**Priority:** P0 - BLOCKING

**Steps:**

1. Add to `/Users/nicholasmparker/Projects/skylapse/backend/main.py`:

   ```python
   class PiHealthMonitor:
       """Track Pi connectivity and alert on failures"""

       def __init__(self, failure_threshold: int = 3):
           self.consecutive_failures = 0
           self.threshold = failure_threshold
           self.is_healthy = True
           self.last_success_time = None
           self.last_error = None

       def record_success(self):
           self.consecutive_failures = 0
           self.is_healthy = True
           self.last_success_time = datetime.now(solar_calc.timezone)
           self.last_error = None

       def record_failure(self, error: str):
           self.consecutive_failures += 1
           self.last_error = error

           if self.consecutive_failures >= self.threshold:
               self.is_healthy = False
               logger.critical(
                   f"🚨 PI UNHEALTHY: {self.consecutive_failures} "
                   f"consecutive failures. Last error: {error}"
               )

       def get_status(self) -> dict:
           return {
               "healthy": self.is_healthy,
               "consecutive_failures": self.consecutive_failures,
               "last_success": self.last_success_time.isoformat()
                              if self.last_success_time else None,
               "last_error": self.last_error
           }

   # Initialize in lifespan
   health_monitor = PiHealthMonitor()
   ```

2. Update scheduler loop (line ~124):

   ```python
   if success:
       health_monitor.record_success()
       logger.info(f"✓ {schedule_name} capture successful")
   else:
       health_monitor.record_failure(f"{schedule_name} capture failed")
       logger.error(f"✗ {schedule_name} capture failed")
   ```

3. Add new endpoint:

   ```python
   @app.get("/health/pi")
   async def get_pi_health():
       """Check if Pi is responding to capture requests"""
       return health_monitor.get_status()
   ```

4. **Test:**

   ```bash
   # Start backend
   docker-compose up backend

   # Check health endpoint
   curl http://localhost:8082/health/pi

   # Simulate Pi down (stop Pi or block network)
   # Wait for 3 failures
   # Check logs for critical alert
   ```

**Why:** Know when system is broken, remote monitoring

---

### 3. Smoke Test [VALIDATION]

**Effort:** 1 hour
**Assignee:** QA or developer
**Priority:** P0 - VALIDATION

**Steps:**

1. Start backend:

   ```bash
   cd /Users/nicholasmparker/Projects/skylapse
   docker-compose up backend
   ```

2. Watch logs for 30-60 minutes:

   - Verify scheduler loop runs every 30 seconds
   - Verify no crashes
   - Verify sun times calculated correctly
   - Verify schedule window logic works

3. Test endpoints:

   ```bash
   curl http://localhost:8082/
   curl http://localhost:8082/schedules
   curl http://localhost:8082/status
   curl http://localhost:8082/health
   curl http://localhost:8082/health/pi
   ```

4. Check edge cases:
   - Start during different times of day
   - Start near sunrise/sunset boundary
   - Check behavior across midnight

**Pass Criteria:**

- ✓ No crashes for 1 hour
- ✓ All endpoints return 200
- ✓ Logs show correct schedule evaluation
- ✓ No unexpected errors

---

## ⏸️ MEDIUM PRIORITY (Defer to Week 3-4)

### 4. Centralize Camera Constraints

**Effort:** 1 hour
**When:** Sprint 1 Week 3
**Why:** After Pi integration, when we know actual hardware constraints

### 5. Config-Driven Exposure Profiles

**Effort:** 2-3 hours
**When:** Sprint 1 Week 3-4
**Why:** After tuning exposure with real captures

### 6. Configurable Scheduler Interval

**Effort:** 15 minutes
**When:** Sprint 1 Week 3
**Why:** Nice-to-have for testing

### 7. Timezone Validation

**Effort:** 30 minutes
**When:** Sprint 1 Week 3
**Why:** Fail-fast improvement

---

## 🚫 DO NOT DO (Defer to v2 or Never)

### 8. Solar Cache Eviction

**Reason:** Grows 200 bytes/day = not a real problem
**When:** Sprint 2 if memory issues appear (unlikely)

### 9. HTTP Connection Pooling

**Reason:** Premature optimization (captures every 30s)
**When:** If profiling shows it matters (unlikely)

### 10. Comprehensive Unit Tests

**Reason:** Write tests incrementally as code stabilizes
**When:** Week 2-3 after Pi integration

### 11. Request ID Tracing

**Reason:** Nice for debugging, not critical
**When:** If debugging becomes difficult

---

## Week 2 Schedule

### Day 1 (Monday)

- ✓ Fix schedule type duplication (2 hours)
- ✓ Add Pi health monitoring (2 hours)
- ✓ Smoke test scheduler (1 hour)

### Day 2 (Tuesday)

- Build minimal Pi capture service
- Test camera initialization
- Test settings application

### Day 3 (Wednesday)

- Backend → Pi communication
- End-to-end capture flow
- Error handling

### Day 4 (Thursday)

- Retry logic
- Timeout tuning
- Integration testing

### Day 5 (Friday)

- Overnight test (verify no crashes)
- Performance profiling
- Documentation

---

## Success Criteria for Week 2

By end of Sprint 1 Week 2, we should have:

**Working:**

- ✓ Backend sends capture commands to Pi
- ✓ Pi receives commands and captures images
- ✓ Images stored on backend
- ✓ Health monitoring shows Pi status
- ✓ System runs overnight without crashes

**Demo-Ready:**

- ✓ Show scheduler triggering captures
- ✓ Show different exposure settings for sunrise/daytime/sunset
- ✓ Show captured images
- ✓ Show health monitoring

---

## Communication

### Team Standups

**Daily 9am:**

- What did you complete yesterday?
- What are you working on today?
- Any blockers?

### Sprint Review

**Friday 4pm:**

- Demo working system
- Review technical debt decisions
- Plan Week 3

---

## Contacts

**Questions on:**

- Schedule type refactoring → Backend lead
- Pi health monitoring → Backend lead
- Pi integration → Hardware/Pi lead
- Testing strategy → QA lead
- Architecture decisions → Tech lead

---

## Files to Modify

### Create New:

- [ ] `/Users/nicholasmparker/Projects/skylapse/backend/schedule_types.py`

### Modify Existing:

- [ ] `/Users/nicholasmparker/Projects/skylapse/backend/main.py`
- [ ] `/Users/nicholasmparker/Projects/skylapse/backend/exposure.py`
- [ ] `/Users/nicholasmparker/Projects/skylapse/backend/solar.py`

---

## Verification Checklist

Before starting Pi integration (Week 2 Day 2):

- [ ] schedule_types.py created and tested
- [ ] All string literals replaced with enum/helpers
- [ ] PiHealthMonitor class implemented
- [ ] /health/pi endpoint working
- [ ] Smoke test passed (1 hour no crashes)
- [ ] All existing endpoints still work
- [ ] Git commit created with fixes
- [ ] Team reviewed changes

---

## Git Workflow

```bash
# Create branch for fixes
git checkout -b fix/sprint-1-tech-debt

# Make changes (items 1-2 above)

# Test
docker-compose up backend
# Run smoke test

# Commit
git add backend/schedule_types.py backend/main.py backend/exposure.py backend/solar.py
git commit -m "fix: Address Sprint 1 Week 1 technical debt

- Add ScheduleType enum to eliminate string duplication
- Add PiHealthMonitor for operational visibility
- Add /health/pi endpoint

Addresses critical DRY violation and adds health monitoring
as recommended by technical debt analysis.

See agent-comms/FINAL-TECH-DEBT-SUMMARY.md for details."

# Push and create PR
git push origin fix/sprint-1-tech-debt
gh pr create --title "Fix Sprint 1 Week 1 Technical Debt" \
  --body "Addresses 2 critical items from tech debt analysis before Week 2 Pi integration."
```

---

## Risk Mitigation

**If fixes take longer than expected:**

- Schedule type duplication: Can skip if running out of time (but don't)
- Pi health monitoring: Absolutely required for operations

**If smoke test fails:**

- Debug immediately
- Don't proceed to Pi integration until fixed
- Escalate to tech lead

**If Pi integration blocked:**

- Continue with fixes anyway
- Use mock Pi for testing
- Revisit integration when Pi available

---

## Success Indicators

**Green lights to proceed:**

- ✓ All action items 1-3 completed
- ✓ No regressions in existing functionality
- ✓ Team confident in code quality
- ✓ Documentation updated

**Red flags to stop:**

- ✗ Smoke test reveals crashes
- ✗ Fixes introduce new bugs
- ✗ Team not confident proceeding
- ✗ Architecture concerns raised

---

**Ready to proceed? Let's ship this MVP!**

**Questions?** See `/Users/nicholasmparker/Projects/skylapse/agent-comms/FINAL-TECH-DEBT-SUMMARY.md` for full analysis.
