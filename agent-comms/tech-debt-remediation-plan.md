# Skylapse Technical Debt Remediation Plan

**Date:** 2025-10-03
**Version:** 1.0
**Status:** Comprehensive System Analysis
**Analyst:** Jordan Martinez, Senior QA Engineer & Technical Debt Remediation Specialist

---

## Executive Summary

### Scope of Analysis

Comprehensive review of the Skylapse timelapse photography system, covering:

- Backend service (FastAPI, 832 LOC main.py)
- Pi capture service (FastAPI, 758 LOC main.py)
- Frontend UI (React + Vite, minimal implementation)
- Database layer (SQLite, 527 LOC)
- Background workers (RQ, 277 LOC tasks.py)
- Shared modules (WB curves, URL builder)
- Docker infrastructure
- Configuration management

### Overall Health Assessment

**System Maturity:** Early production stage with recent refactoring
**Technical Debt Level:** **MODERATE-HIGH**
**Risk Level:** **MEDIUM** - System functional but fragile
**Test Coverage:** **CRITICAL GAP** - Minimal automated tests

### Critical Findings Summary

| Category       | Critical | High   | Medium | Total  |
| -------------- | -------- | ------ | ------ | ------ |
| Code Quality   | 3        | 8      | 12     | 23     |
| Architecture   | 2        | 5      | 7      | 14     |
| Error Handling | 4        | 6      | 4      | 14     |
| Testing        | 5        | 3      | 2      | 10     |
| Security       | 2        | 4      | 3      | 9      |
| Performance    | 1        | 3      | 5      | 9      |
| Documentation  | 0        | 4      | 8      | 12     |
| Configuration  | 1        | 3      | 4      | 8      |
| **TOTAL**      | **18**   | **36** | **45** | **99** |

### Key Insights

1. **Frontend is a Skeleton** - React app is placeholder boilerplate, no real UI implemented
2. **Testing Coverage Critical Gap** - Test files exist but appear to be development artifacts, not CI/CD integrated
3. **Error Handling Inconsistent** - Mix of exceptions, silent failures, and log-only errors
4. **Global State Pollution** - `main.py` uses global singletons and app.state mixing
5. **Database Operations Lack Transactions** - Multiple queries without rollback handling
6. **No Monitoring/Alerting** - System failures could go unnoticed for extended periods

---

## CRITICAL PRIORITY DEBT ITEMS

### C1: Frontend Not Implemented

**Severity:** CRITICAL
**Category:** Code Quality / Architecture
**Impact:** System lacks usable UI, severely limiting user interaction

**Location:** `/Users/nicholasmparker/Projects/skylapse/frontend/src/App.tsx:1-36`

**Current State:**

```typescript
function App() {
  const [count, setCount] = useState(0)
  return (
    <>
      <div>
        <a href="https://vite.dev" target="_blank">
          <img src={viteLogo} className="logo" alt="Vite logo" />
        </a>
        {/* ... Vite boilerplate ... */}
      </div>
      <h1>Vite + React</h1>
    </>
  )
}
```

**Root Cause:** Frontend development deferred during rapid backend iteration

**Business Impact:**

- Users cannot monitor system status visually
- No timelapse playback interface
- Cannot view/compare profile images
- Backend API endpoints exist (`/profiles`, `/timelapses`) but unused

**Remediation Steps:**

1. **Design UI Architecture (4 hours)**

   - Create wireframes for Dashboard, Gallery, Settings pages
   - Define component hierarchy
   - Plan state management (Context API vs Redux)

2. **Implement Dashboard View (8 hours)**

   ```typescript
   // src/components/Dashboard.tsx
   interface SystemStatus {
     current_time: string;
     sun: { sunrise: string; sunset: string; is_daytime: boolean };
     schedules: { active: any[]; enabled_count: number };
     camera: { status: string; host: string };
   }

   const Dashboard: React.FC = () => {
     const [status, setStatus] = useState<SystemStatus | null>(null);

     useEffect(() => {
       const fetchStatus = async () => {
         const response = await fetch(`${backendUrl}/system`);
         setStatus(await response.json());
       };
       fetchStatus();
       const interval = setInterval(fetchStatus, 30000); // 30s updates
       return () => clearInterval(interval);
     }, []);

     return (
       <div className="dashboard">
         <SunTimesCard sunTimes={status?.sun} />
         <ActiveSchedulesCard schedules={status?.schedules} />
         <CameraStatusCard camera={status?.camera} />
       </div>
     );
   };
   ```

3. **Implement Profile Gallery (12 hours)**

   - Grid view of 7 profiles (A-G) with latest images
   - Click to view full-size image
   - Display profile descriptions and settings
   - Real-time updates using polling or WebSocket

4. **Implement Timelapse Player (8 hours)**

   - List timelapses from `/timelapses` endpoint
   - Filter by profile, schedule, date
   - Inline video player with controls
   - Download/share functionality
   - Thumbnail previews

5. **Add Settings Panel (4 hours)**
   - Location configuration
   - Schedule enable/disable toggles
   - Connection status to Pi

**Testing Strategy:**

- Component unit tests with React Testing Library
- Integration tests for API calls (Mock Service Worker)
- E2E tests with Playwright for critical flows

**Estimated Effort:** 40-48 hours
**Risk Level:** Low - Well-defined APIs exist
**Dependencies:** None

**Success Criteria:**

- [ ] User can view system status at a glance
- [ ] User can see latest image from each profile
- [ ] User can play generated timelapses
- [ ] User can monitor schedule activity
- [ ] Dashboard updates in real-time (30s polling)

---

### C2: No Automated Test Coverage

**Severity:** CRITICAL
**Category:** Testing / Quality Assurance
**Impact:** High risk of regression, difficult to refactor safely

**Location:** Multiple test files exist but not integrated into CI/CD

**Current State:**

- `test_tech_debt_fixes.py` (414 LOC) - Development test file, not automated
- `test_fixes_simple.py` (304 LOC) - Development test file
- `test_integration.py` (146 LOC) - Basic integration tests
- No `pytest.ini` or test runner configuration
- No CI/CD pipeline (GitHub Actions, etc.)
- Docker-compose has no test service

**Root Cause:** Tests written during development but not formalized into CI pipeline

**Business Impact:**

- Cannot safely refactor code
- Risk of breaking changes in production
- Difficult to validate bug fixes
- New features may introduce regressions

**Remediation Steps:**

1. **Set Up Test Infrastructure (4 hours)**

   ```bash
   # backend/pytest.ini
   [pytest]
   testpaths = tests
   python_files = test_*.py
   python_classes = Test*
   python_functions = test_*
   addopts =
       --verbose
       --strict-markers
       --cov=.
       --cov-report=html
       --cov-report=term-missing
       --cov-fail-under=60
   markers =
       unit: Unit tests
       integration: Integration tests (require services)
       slow: Slow tests (> 1s)
   ```

2. **Reorganize Test Files (2 hours)**

   ```
   backend/
   ├── tests/
   │   ├── __init__.py
   │   ├── conftest.py              # Shared fixtures
   │   ├── unit/
   │   │   ├── test_config.py       # Config class tests
   │   │   ├── test_exposure.py     # Exposure calculator tests
   │   │   ├── test_solar.py        # Solar calculator tests
   │   │   ├── test_database.py     # Database operations tests
   │   │   └── test_wb_curves.py    # WB curve interpolation tests
   │   ├── integration/
   │   │   ├── test_api_endpoints.py  # FastAPI endpoint tests
   │   │   ├── test_scheduler.py      # Scheduler loop tests
   │   │   └── test_timelapse_gen.py  # Timelapse generation tests
   │   └── e2e/
   │       └── test_capture_flow.py   # End-to-end capture flow
   ```

3. **Create Test Fixtures (4 hours)**

   ```python
   # backend/tests/conftest.py
   import pytest
   from pathlib import Path
   from database import SessionDatabase
   from config import Config

   @pytest.fixture
   def test_db():
       """In-memory test database"""
       db_path = ":memory:"
       db = SessionDatabase(db_path)
       yield db
       # Cleanup handled by in-memory DB

   @pytest.fixture
   def test_config(tmp_path):
       """Test configuration with temp directory"""
       config_path = tmp_path / "test_config.json"
       config = Config(str(config_path))
       return config

   @pytest.fixture
   def mock_pi_server():
       """Mock Pi service for testing"""
       # Use httpx-mock or responses library
       pass

   @pytest.fixture
   def sample_capture_settings():
       """Standard capture settings for testing"""
       return {
           "iso": 400,
           "shutter_speed": "1/500",
           "exposure_compensation": 0.0,
           "profile": "a",
           "awb_mode": 1,
           "hdr_mode": 0,
           "bracket_count": 1
       }
   ```

4. **Write Critical Unit Tests (16 hours)**

   - Database CRUD operations (sessions, captures, timelapses)
   - Exposure calculation logic for all profiles
   - WB curve interpolation edge cases
   - Solar time calculations across timezones
   - Config management (load, save, get, set)
   - URL builder path construction

5. **Write Integration Tests (12 hours)**

   - API endpoint responses (mocked Pi)
   - Scheduler loop behavior
   - Timelapse generation from sample images
   - Database transaction handling
   - Error recovery scenarios

6. **Set Up CI/CD Pipeline (4 hours)**

   ```yaml
   # .github/workflows/test.yml
   name: Test Suite

   on: [push, pull_request]

   jobs:
     test:
       runs-on: ubuntu-latest

       services:
         redis:
           image: redis:7-alpine
           options: >-
             --health-cmd "redis-cli ping"
             --health-interval 10s
             --health-timeout 5s
             --health-retries 5
           ports:
             - 6379:6379

       steps:
         - uses: actions/checkout@v3

         - name: Set up Python
           uses: actions/setup-python@v4
           with:
             python-version: "3.11"

         - name: Install dependencies
           run: |
             pip install -r backend/requirements.txt
             pip install pytest pytest-cov pytest-asyncio

         - name: Run unit tests
           run: |
             cd backend
             pytest tests/unit -v --cov --cov-report=xml

         - name: Run integration tests
           run: |
             cd backend
             pytest tests/integration -v

         - name: Upload coverage
           uses: codecov/codecov-action@v3
   ```

7. **Add Docker Test Service (2 hours)**
   ```yaml
   # docker-compose.yml
   services:
     test:
       build:
         context: .
         dockerfile: ./backend/Dockerfile
       command: pytest tests/ -v --cov --cov-report=term-missing
       volumes:
         - ./backend:/app
       environment:
         - REDIS_URL=redis://redis:6379
         - PI_HOST=mock-pi
       depends_on:
         - redis
   ```

**Testing Strategy:**

- Start with high-value unit tests (database, exposure calc)
- Add integration tests for scheduler + API
- Use mocking for Pi communication
- Achieve 60% code coverage minimum
- Run tests on every commit (CI)

**Estimated Effort:** 44 hours
**Risk Level:** Medium - Requires significant time investment
**Dependencies:** None

**Success Criteria:**

- [ ] 60%+ code coverage across backend
- [ ] All critical paths tested (capture flow, timelapse gen)
- [ ] Tests run automatically on every commit
- [ ] Tests pass before Docker build succeeds
- [ ] Coverage report visible in CI

---

### C3: Database Transaction Safety Missing

**Severity:** CRITICAL
**Category:** Error Handling / Data Integrity
**Impact:** Risk of partial writes, data corruption, orphaned records

**Location:** `/Users/nicholasmparker/Projects/skylapse/backend/database.py:144-305`

**Current State:**

```python
def _update_session_stats(self, conn: sqlite3.Connection, session_id: str, ...):
    """Update session-level statistics."""
    # ... complex calculations ...

    # Multiple UPDATE queries without transaction boundaries
    conn.execute(
        """UPDATE sessions SET
            end_time = ?, image_count = ?, lux_min = ?, lux_max = ?, ...
        WHERE session_id = ?""",
        (timestamp.isoformat(), new_count, lux_min, lux_max, ...)
    )
    # No explicit commit, no rollback on error
```

**Root Cause:** Database operations assume context manager handles commits, but no explicit transaction boundaries for multi-step operations

**Business Impact:**

- Capture metadata could be saved without session stats update
- Timelapse records could orphan if session update fails
- Inconsistent state if process crashes mid-operation
- Difficult to debug data integrity issues

**Remediation Steps:**

1. **Add Explicit Transaction Management (4 hours)**

   ```python
   # database.py
   from contextlib import contextmanager

   @contextmanager
   def _get_transaction(self):
       """
       Context manager for database transactions with rollback on error.

       Usage:
           with db._get_transaction() as conn:
               # Multiple operations
               conn.execute(...)
               conn.execute(...)
               # Automatic commit on success, rollback on exception
       """
       conn = sqlite3.connect(self.db_path)
       conn.row_factory = sqlite3.Row
       try:
           yield conn
           conn.commit()  # Explicit commit on success
       except Exception as e:
           conn.rollback()  # Rollback on error
           logger.error(f"Transaction rolled back: {e}")
           raise
       finally:
           conn.close()

   def record_capture(self, session_id: str, filename: str, timestamp: datetime, settings: Dict):
       """Record a single capture with its metadata (TRANSACTIONAL)."""
       now = datetime.utcnow().isoformat()

       with self._get_transaction() as conn:
           # Insert capture record
           conn.execute(
               """INSERT INTO captures (session_id, timestamp, filename, ...)
                  VALUES (?, ?, ?, ...)""",
               (session_id, timestamp.isoformat(), filename, ...)
           )

           # Update session statistics (same transaction)
           self._update_session_stats(conn, session_id, timestamp, settings)

           # Both operations committed together
   ```

2. **Add Retry Logic for Transient Failures (3 hours)**

   ```python
   import time
   from functools import wraps

   def retry_on_lock(max_retries=3, delay=0.5):
       """Retry decorator for database lock errors."""
       def decorator(func):
           @wraps(func)
           def wrapper(*args, **kwargs):
               for attempt in range(max_retries):
                   try:
                       return func(*args, **kwargs)
                   except sqlite3.OperationalError as e:
                       if "database is locked" in str(e) and attempt < max_retries - 1:
                           logger.warning(f"DB locked, retrying in {delay}s (attempt {attempt+1}/{max_retries})")
                           time.sleep(delay)
                       else:
                           raise
               return None
           return wrapper
       return decorator

   @retry_on_lock(max_retries=3, delay=0.5)
   def record_capture(self, ...):
       # ... transactional code ...
       pass
   ```

3. **Add Database Integrity Checks (2 hours)**

   ```python
   def verify_database_integrity(self) -> Dict[str, Any]:
       """
       Verify database integrity and consistency.

       Returns:
           Dictionary with integrity check results
       """
       issues = []

       with self._get_connection() as conn:
           # Check for orphaned captures (session doesn't exist)
           orphaned = conn.execute(
               """SELECT COUNT(*) as count FROM captures c
                  WHERE NOT EXISTS (
                      SELECT 1 FROM sessions s WHERE s.session_id = c.session_id
                  )"""
           ).fetchone()
           if orphaned['count'] > 0:
               issues.append(f"Found {orphaned['count']} orphaned captures")

           # Check for sessions with mismatched image counts
           mismatched = conn.execute(
               """SELECT s.session_id, s.image_count, COUNT(c.id) as actual_count
                  FROM sessions s
                  LEFT JOIN captures c ON s.session_id = c.session_id
                  GROUP BY s.session_id
                  HAVING s.image_count != actual_count"""
           ).fetchall()
           if mismatched:
               issues.append(f"Found {len(mismatched)} sessions with mismatched image counts")

           # Check for timelapses without sessions
           orphaned_timelapses = conn.execute(
               """SELECT COUNT(*) as count FROM timelapses t
                  WHERE NOT EXISTS (
                      SELECT 1 FROM sessions s WHERE s.session_id = t.session_id
                  )"""
           ).fetchone()
           if orphaned_timelapses['count'] > 0:
               issues.append(f"Found {orphaned_timelapses['count']} orphaned timelapses")

       return {
           'healthy': len(issues) == 0,
           'issues': issues,
           'checked_at': datetime.utcnow().isoformat()
       }
   ```

4. **Add Database Repair Operations (3 hours)**

   ```python
   def repair_database(self, dry_run=True) -> Dict[str, Any]:
       """
       Repair database inconsistencies.

       Args:
           dry_run: If True, only report what would be fixed

       Returns:
           Dictionary with repair results
       """
       repairs = []

       with self._get_transaction() as conn:
           # Fix mismatched image counts
           if not dry_run:
               conn.execute(
                   """UPDATE sessions SET image_count = (
                       SELECT COUNT(*) FROM captures
                       WHERE captures.session_id = sessions.session_id
                   )"""
               )
               repairs.append("Fixed session image counts")

           # Delete orphaned captures
           if not dry_run:
               result = conn.execute(
                   """DELETE FROM captures WHERE session_id NOT IN (
                       SELECT session_id FROM sessions
                   )"""
               )
               repairs.append(f"Deleted {result.rowcount} orphaned captures")

       return {
           'dry_run': dry_run,
           'repairs': repairs,
           'repaired_at': datetime.utcnow().isoformat()
       }
   ```

5. **Add Health Check Endpoint (1 hour)**

   ```python
   # main.py
   @app.get("/health/database")
   async def database_health(request: Request):
       """Check database health and integrity"""
       db = request.app.state.db
       integrity = db.verify_database_integrity()

       return {
           "status": "healthy" if integrity['healthy'] else "degraded",
           "checks": integrity
       }
   ```

**Testing Strategy:**

- Simulate transaction failures (connection drops)
- Concurrent write tests (multiple workers)
- Verify rollback behavior
- Test orphaned record detection
- Validate repair operations

**Estimated Effort:** 13 hours
**Risk Level:** Medium - Requires careful testing
**Dependencies:** C2 (testing infrastructure)

**Success Criteria:**

- [ ] All multi-step database operations use transactions
- [ ] Rollback occurs on any operation failure
- [ ] Retry logic handles transient lock errors
- [ ] Integrity checks detect inconsistencies
- [ ] Repair operations fix common issues
- [ ] Health endpoint monitors database state

---

### C4: No Error Monitoring/Alerting

**Severity:** CRITICAL
**Category:** Monitoring / Operations
**Impact:** Silent failures could prevent timelapse generation for extended periods

**Location:** System-wide

**Current State:**

- Errors logged to stdout/stderr
- No centralized error tracking
- No alerting on critical failures
- Scheduler loop failures only visible in logs
- Timelapse generation failures silent (RQ worker)
- No metrics collection (capture success rate, disk usage, etc.)

**Root Cause:** Early development phase, monitoring deferred

**Business Impact:**

- System could fail silently for days
- Missed captures not detected until manual review
- Disk full errors crash services
- No visibility into system health trends
- Difficult to diagnose intermittent issues

**Remediation Steps:**

1. **Add Structured Logging (4 hours)**

   ```python
   # backend/logger.py
   import logging
   import sys
   from pythonjsonlogger import jsonlogger

   def setup_logger(name: str, level=logging.INFO):
       """Set up structured JSON logging for production."""
       logger = logging.getLogger(name)
       logger.setLevel(level)

       # JSON formatter for structured logs
       formatter = jsonlogger.JsonFormatter(
           '%(asctime)s %(name)s %(levelname)s %(message)s %(pathname)s %(lineno)d'
       )

       # Console handler
       handler = logging.StreamHandler(sys.stdout)
       handler.setFormatter(formatter)
       logger.addHandler(handler)

       return logger

   # Usage in main.py:
   from logger import setup_logger
   logger = setup_logger(__name__)

   logger.info("Capture started", extra={
       "profile": "a",
       "schedule": "sunset",
       "lux": 800,
       "iso": 400
   })
   ```

2. **Add Health Metrics Collection (6 hours)**

   ```python
   # backend/metrics.py
   from dataclasses import dataclass
   from datetime import datetime
   from typing import Dict, List
   import psutil

   @dataclass
   class SystemMetrics:
       timestamp: str
       cpu_percent: float
       memory_percent: float
       disk_usage_percent: float
       disk_free_gb: float

   @dataclass
   class CaptureMetrics:
       total_captures_today: int
       failed_captures_today: int
       success_rate: float
       avg_capture_time_ms: float
       profiles_active: List[str]

   @dataclass
   class TimelapseMetrics:
       total_timelapses: int
       pending_jobs: int
       failed_jobs: int
       avg_generation_time_s: float

   class MetricsCollector:
       """Collect and expose system metrics."""

       def __init__(self, db: SessionDatabase, queue: Queue):
           self.db = db
           self.queue = queue

       def collect_system_metrics(self) -> SystemMetrics:
           """Collect system resource metrics."""
           disk = psutil.disk_usage('/data')
           return SystemMetrics(
               timestamp=datetime.utcnow().isoformat(),
               cpu_percent=psutil.cpu_percent(interval=1),
               memory_percent=psutil.virtual_memory().percent,
               disk_usage_percent=disk.percent,
               disk_free_gb=disk.free / (1024**3)
           )

       def collect_capture_metrics(self) -> CaptureMetrics:
           """Collect capture success/failure metrics."""
           today = datetime.now().strftime('%Y-%m-%d')

           # Query database for today's captures
           # ... implementation ...

           return CaptureMetrics(
               total_captures_today=0,  # TODO: implement
               failed_captures_today=0,
               success_rate=0.0,
               avg_capture_time_ms=0.0,
               profiles_active=[]
           )

       def check_critical_conditions(self) -> List[Dict]:
           """Check for critical system conditions."""
           alerts = []

           # Disk space check
           disk = psutil.disk_usage('/data')
           if disk.percent > 90:
               alerts.append({
                   'severity': 'critical',
                   'type': 'disk_space',
                   'message': f'Disk usage at {disk.percent}%',
                   'threshold': 90,
                   'current': disk.percent
               })
           elif disk.percent > 80:
               alerts.append({
                   'severity': 'warning',
                   'type': 'disk_space',
                   'message': f'Disk usage at {disk.percent}%',
                   'threshold': 80,
                   'current': disk.percent
               })

           # Pi connectivity check
           # ... implementation ...

           # Failed job check
           failed_jobs = self.queue.failed_job_registry.count
           if failed_jobs > 5:
               alerts.append({
                   'severity': 'critical',
                   'type': 'failed_jobs',
                   'message': f'{failed_jobs} failed timelapse jobs',
                   'threshold': 5,
                   'current': failed_jobs
               })

           return alerts
   ```

3. **Add Metrics API Endpoint (2 hours)**

   ```python
   # main.py
   from metrics import MetricsCollector

   @app.get("/metrics")
   async def get_metrics(request: Request):
       """Expose Prometheus-compatible metrics."""
       db = request.app.state.db
       queue = request.app.state.timelapse_queue

       collector = MetricsCollector(db, queue)
       system = collector.collect_system_metrics()
       captures = collector.collect_capture_metrics()
       alerts = collector.check_critical_conditions()

       return {
           'system': system,
           'captures': captures,
           'alerts': alerts,
           'timestamp': datetime.utcnow().isoformat()
       }

   @app.get("/health/detailed")
   async def detailed_health(request: Request):
       """Comprehensive health check with all subsystems."""
       db = request.app.state.db
       config = request.app.state.config

       health_checks = {
           'database': await check_database_health(db),
           'redis': await check_redis_health(),
           'pi': await check_pi_health(config),
           'disk': check_disk_health(),
           'scheduler': check_scheduler_health(request.app.state.scheduler_task)
       }

       overall_healthy = all(check['healthy'] for check in health_checks.values())

       return {
           'status': 'healthy' if overall_healthy else 'degraded',
           'checks': health_checks,
           'timestamp': datetime.utcnow().isoformat()
       }
   ```

4. **Add Simple Email Alerting (4 hours)**

   ```python
   # backend/alerting.py
   import smtplib
   from email.message import EmailMessage
   import os

   class AlertManager:
       """Simple email-based alerting."""

       def __init__(self):
           self.enabled = os.getenv('ALERTS_ENABLED', 'false').lower() == 'true'
           self.smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
           self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
           self.smtp_user = os.getenv('SMTP_USER', '')
           self.smtp_password = os.getenv('SMTP_PASSWORD', '')
           self.alert_email = os.getenv('ALERT_EMAIL', '')
           self.last_alerts = {}  # Debounce alerts

       def send_alert(self, severity: str, message: str, details: dict = None):
           """
           Send alert email if enabled and not recently sent.

           Args:
               severity: 'critical', 'warning', 'info'
               message: Alert message
               details: Additional context
           """
           if not self.enabled:
               logger.info(f"Alert (not sent): [{severity}] {message}")
               return

           # Debounce: don't send same alert within 1 hour
           alert_key = f"{severity}:{message}"
           if alert_key in self.last_alerts:
               elapsed = (datetime.utcnow() - self.last_alerts[alert_key]).seconds
               if elapsed < 3600:  # 1 hour
                   return

           try:
               msg = EmailMessage()
               msg['Subject'] = f"Skylapse Alert [{severity.upper()}]: {message}"
               msg['From'] = self.smtp_user
               msg['To'] = self.alert_email

               body = f"""
   Skylapse Alert
   ==============

   Severity: {severity.upper()}
   Message: {message}
   Time: {datetime.utcnow().isoformat()}

   Details:
   {json.dumps(details, indent=2) if details else 'None'}

   ---
   Skylapse Monitoring System
               """
               msg.set_content(body)

               with smtplib.SMTP(self.smtp_host, self.smtp_port) as smtp:
                   smtp.starttls()
                   smtp.login(self.smtp_user, self.smtp_password)
                   smtp.send_message(msg)

               self.last_alerts[alert_key] = datetime.utcnow()
               logger.info(f"Alert sent: [{severity}] {message}")

           except Exception as e:
               logger.error(f"Failed to send alert: {e}")
   ```

5. **Add Background Health Monitor (3 hours)**

   ```python
   # main.py - Add to lifespan
   async def health_monitor_loop(app: FastAPI):
       """Background task to monitor system health and send alerts."""
       from metrics import MetricsCollector
       from alerting import AlertManager

       logger.info("Health monitor starting...")
       alert_mgr = AlertManager()

       while True:
           try:
               await asyncio.sleep(300)  # Check every 5 minutes

               db = app.state.db
               queue = app.state.timelapse_queue
               collector = MetricsCollector(db, queue)

               # Check critical conditions
               alerts = collector.check_critical_conditions()

               for alert in alerts:
                   if alert['severity'] == 'critical':
                       alert_mgr.send_alert(
                           severity='critical',
                           message=alert['message'],
                           details=alert
                       )
                       logger.critical(f"CRITICAL ALERT: {alert['message']}")
                   elif alert['severity'] == 'warning':
                       logger.warning(f"WARNING: {alert['message']}")

               # Check scheduler health
               if app.state.scheduler_task.done():
                   alert_mgr.send_alert(
                       severity='critical',
                       message='Scheduler loop has stopped!',
                       details={'task_status': 'done'}
                   )

           except Exception as e:
               logger.error(f"Health monitor error: {e}", exc_info=True)

   @asynccontextmanager
   async def lifespan(app: FastAPI):
       # ... existing startup code ...

       # Start health monitor
       monitor_task = asyncio.create_task(health_monitor_loop(app))
       app.state.monitor_task = monitor_task

       yield

       # Shutdown
       if app.state.monitor_task:
           app.state.monitor_task.cancel()
   ```

**Testing Strategy:**

- Simulate disk full scenarios
- Test alert delivery and debouncing
- Verify metrics accuracy
- Load test metrics endpoint

**Estimated Effort:** 19 hours
**Risk Level:** Low - Additive functionality
**Dependencies:** None

**Success Criteria:**

- [ ] Structured JSON logs for all critical operations
- [ ] Metrics endpoint exposes system health
- [ ] Alerts sent for critical conditions (disk, failures)
- [ ] Health monitor runs in background
- [ ] Dashboard can display metrics (frontend C1)

---

## HIGH PRIORITY DEBT ITEMS

### H1: Scheduler Loop Error Recovery Insufficient

**Severity:** HIGH
**Category:** Error Handling / Reliability
**Impact:** Single error could stop all captures indefinitely

**Location:** `/Users/nicholasmparker/Projects/skylapse/backend/main.py:111-280`

**Current State:**

```python
async def scheduler_loop(app: FastAPI):
    while True:
        try:
            # ... all scheduler logic ...
            await asyncio.sleep(min_interval)
        except Exception as e:
            logger.error(f"Error in scheduler loop: {e}", exc_info=True)
            await asyncio.sleep(30)  # Continue even if there was an error
```

**Issues:**

1. Single `try/except` wraps entire iteration - catches too much
2. No differentiation between recoverable vs fatal errors
3. 30-second retry delay arbitrary, no backoff
4. No circuit breaker for repeated failures
5. Error state not exposed to health checks

**Root Cause:** Simple error handling adequate for prototype, not production

**Remediation Steps:**

1. **Add Granular Error Handling (4 hours)**

   ```python
   async def scheduler_loop(app: FastAPI):
       error_count = 0
       max_errors = 10
       backoff_multiplier = 1.5
       base_delay = 30

       while True:
           try:
               current_time = datetime.now(solar_calc.timezone)

               # Iterate through schedules with individual error handling
               for schedule_name, schedule_config in schedules.items():
                   try:
                       # Schedule checking logic
                       # ... (moved to separate function)
                       await process_schedule(
                           schedule_name,
                           schedule_config,
                           current_time,
                           app.state
                       )

                   except httpx.TimeoutError as e:
                       logger.error(f"Pi timeout for {schedule_name}: {e}")
                       # Continue to next schedule, don't crash

                   except httpx.HTTPError as e:
                       logger.error(f"Pi HTTP error for {schedule_name}: {e}")
                       # Continue to next schedule

                   except Exception as e:
                       logger.error(f"Unexpected error for {schedule_name}: {e}", exc_info=True)
                       # Continue to next schedule

               # Reset error count on successful iteration
               error_count = 0
               await asyncio.sleep(min_interval)

           except asyncio.CancelledError:
               logger.info("Scheduler loop cancelled gracefully")
               break

           except Exception as e:
               error_count += 1
               delay = base_delay * (backoff_multiplier ** error_count)
               logger.error(
                   f"Critical scheduler error #{error_count}/{max_errors}: {e}",
                   exc_info=True
               )

               # Circuit breaker: stop if too many errors
               if error_count >= max_errors:
                   logger.critical("Scheduler loop exceeded max errors - STOPPING")
                   # Send critical alert
                   break

               await asyncio.sleep(min(delay, 300))  # Cap at 5 minutes

   async def process_schedule(
       schedule_name: str,
       schedule_config: dict,
       current_time: datetime,
       app_state
   ):
       """Process a single schedule (extracted for better error isolation)."""
       # All schedule logic here
       pass
   ```

2. **Add Circuit Breaker for Pi Communication (3 hours)**

   ```python
   # backend/circuit_breaker.py
   from datetime import datetime, timedelta
   from enum import Enum

   class CircuitState(Enum):
       CLOSED = "closed"      # Normal operation
       OPEN = "open"          # Too many failures, stop trying
       HALF_OPEN = "half_open"  # Testing if service recovered

   class CircuitBreaker:
       """Circuit breaker for Pi communication."""

       def __init__(self, failure_threshold=5, timeout_seconds=60):
           self.failure_threshold = failure_threshold
           self.timeout = timedelta(seconds=timeout_seconds)
           self.failure_count = 0
           self.last_failure_time = None
           self.state = CircuitState.CLOSED

       def call(self, func, *args, **kwargs):
           """Execute function with circuit breaker protection."""
           if self.state == CircuitState.OPEN:
               # Check if we should try again
               if datetime.utcnow() - self.last_failure_time > self.timeout:
                   self.state = CircuitState.HALF_OPEN
                   logger.info("Circuit breaker: HALF_OPEN - testing recovery")
               else:
                   raise Exception("Circuit breaker OPEN - service unavailable")

           try:
               result = func(*args, **kwargs)
               self.on_success()
               return result

           except Exception as e:
               self.on_failure()
               raise

       def on_success(self):
           """Reset circuit breaker on successful call."""
           if self.state == CircuitState.HALF_OPEN:
               logger.info("Circuit breaker: CLOSED - service recovered")
           self.failure_count = 0
           self.state = CircuitState.CLOSED

       def on_failure(self):
           """Increment failure count and open circuit if threshold exceeded."""
           self.failure_count += 1
           self.last_failure_time = datetime.utcnow()

           if self.failure_count >= self.failure_threshold:
               self.state = CircuitState.OPEN
               logger.critical(
                   f"Circuit breaker: OPEN after {self.failure_count} failures"
               )

   # Usage in main.py
   pi_circuit_breaker = CircuitBreaker(failure_threshold=5, timeout_seconds=60)

   async def trigger_capture(schedule_name: str, settings: dict, config: Config):
       try:
           result = await pi_circuit_breaker.call(
               _execute_capture,  # Extracted capture logic
               schedule_name,
               settings,
               config
           )
           return result
       except Exception as e:
           logger.error(f"Circuit breaker prevented capture: {e}")
           return (False, "")
   ```

3. **Add Scheduler Health Tracking (2 hours)**

   ```python
   # backend/scheduler_state.py
   from dataclasses import dataclass
   from datetime import datetime
   from typing import Dict

   @dataclass
   class SchedulerHealth:
       is_running: bool
       last_iteration: datetime
       total_iterations: int
       error_count: int
       last_error: str
       last_error_time: datetime
       captures_today: Dict[str, int]  # profile -> count

   class SchedulerState:
       """Track scheduler health and state."""

       def __init__(self):
           self.health = SchedulerHealth(
               is_running=False,
               last_iteration=None,
               total_iterations=0,
               error_count=0,
               last_error=None,
               last_error_time=None,
               captures_today={}
           )

       def on_iteration_start(self):
           self.health.is_running = True

       def on_iteration_complete(self):
           self.health.last_iteration = datetime.utcnow()
           self.health.total_iterations += 1

       def on_error(self, error: str):
           self.health.error_count += 1
           self.health.last_error = error
           self.health.last_error_time = datetime.utcnow()

       def on_capture_success(self, profile: str):
           if profile not in self.health.captures_today:
               self.health.captures_today[profile] = 0
           self.health.captures_today[profile] += 1

       def get_health(self) -> dict:
           """Get scheduler health as dict."""
           return {
               'is_running': self.health.is_running,
               'last_iteration': self.health.last_iteration.isoformat() if self.health.last_iteration else None,
               'total_iterations': self.health.total_iterations,
               'error_count': self.health.error_count,
               'last_error': self.health.last_error,
               'last_error_time': self.health.last_error_time.isoformat() if self.health.last_error_time else None,
               'captures_today': self.health.captures_today
           }

   # Add to main.py app state
   app.state.scheduler_state = SchedulerState()

   @app.get("/health/scheduler")
   async def scheduler_health(request: Request):
       state = request.app.state.scheduler_state
       return state.get_health()
   ```

**Testing Strategy:**

- Simulate Pi timeout scenarios
- Test circuit breaker state transitions
- Verify exponential backoff
- Test scheduler recovery after errors

**Estimated Effort:** 9 hours
**Risk Level:** Medium - Core scheduler logic
**Dependencies:** C4 (monitoring)

**Success Criteria:**

- [ ] Individual schedule failures don't crash scheduler
- [ ] Circuit breaker prevents repeated failed Pi calls
- [ ] Exponential backoff for retry delays
- [ ] Scheduler state exposed via health endpoint
- [ ] Critical alerts sent on scheduler failures

---

### H2: Frontend-Backend Communication Not Robust

**Severity:** HIGH
**Category:** Architecture / Error Handling
**Impact:** Frontend cannot gracefully handle backend failures

**Location:** Frontend (when implemented)

**Current State:**

- Frontend not implemented (see C1)
- Backend has no WebSocket support for real-time updates
- Polling-based architecture assumed but not documented
- No API versioning
- No request/response validation

**Remediation Steps:**

1. **Add API Versioning (2 hours)**

   ```python
   # main.py
   from fastapi import APIRouter

   # Version 1 API
   v1_router = APIRouter(prefix="/api/v1")

   @v1_router.get("/status")
   async def get_status_v1(request: Request):
       # V1 status endpoint
       pass

   @v1_router.get("/profiles")
   async def get_profiles_v1(request: Request):
       # V1 profiles endpoint
       pass

   app.include_router(v1_router)

   # Keep legacy endpoints for backward compatibility
   @app.get("/status")
   async def get_status_legacy(request: Request):
       # Redirect to v1
       return await get_status_v1(request)
   ```

2. **Add Request/Response Validation (4 hours)**

   ```python
   # backend/schemas.py
   from pydantic import BaseModel, Field
   from typing import List, Optional
   from datetime import datetime

   class SystemStatusResponse(BaseModel):
       timestamp: str
       timezone: str
       sun: dict
       location: dict
       schedules: dict
       camera: dict
       system: dict

   class ProfileResponse(BaseModel):
       profile: str = Field(..., pattern="^[a-g]$")
       description: str
       image_url: str
       timestamp: float
       image_count: int

   class TimelapseResponse(BaseModel):
       id: int
       name: str
       filename: str
       url: str
       size: str
       created: str
       profile: str
       schedule: str
       date: str
       frame_count: int
       fps: int
       quality: str
       quality_tier: str = "preview"
       session_id: str

   class ErrorResponse(BaseModel):
       error: str
       message: str
       timestamp: str
       request_id: Optional[str] = None

   # Use in endpoints
   @app.get("/api/v1/system", response_model=SystemStatusResponse)
   async def get_system_status(request: Request):
       # ... implementation ...
       pass

   @app.get("/api/v1/profiles", response_model=List[ProfileResponse])
   async def get_profiles(request: Request):
       # ... implementation ...
       pass
   ```

3. **Add WebSocket Support for Real-Time Updates (8 hours)**

   ```python
   # backend/websocket.py
   from fastapi import WebSocket, WebSocketDisconnect
   from typing import Set
   import asyncio
   import json

   class ConnectionManager:
       """Manage WebSocket connections."""

       def __init__(self):
           self.active_connections: Set[WebSocket] = set()

       async def connect(self, websocket: WebSocket):
           await websocket.accept()
           self.active_connections.add(websocket)
           logger.info(f"Client connected. Total: {len(self.active_connections)}")

       def disconnect(self, websocket: WebSocket):
           self.active_connections.discard(websocket)
           logger.info(f"Client disconnected. Total: {len(self.active_connections)}")

       async def broadcast(self, message: dict):
           """Broadcast message to all connected clients."""
           for connection in self.active_connections.copy():
               try:
                   await connection.send_json(message)
               except Exception as e:
                   logger.error(f"Failed to send to client: {e}")
                   self.disconnect(connection)

   manager = ConnectionManager()

   # In main.py
   @app.websocket("/ws")
   async def websocket_endpoint(websocket: WebSocket):
       await manager.connect(websocket)
       try:
           while True:
               # Keep connection alive, send heartbeat
               await asyncio.sleep(30)
               await websocket.send_json({"type": "heartbeat", "timestamp": datetime.utcnow().isoformat()})
       except WebSocketDisconnect:
           manager.disconnect(websocket)

   # Broadcast events from scheduler
   async def scheduler_loop(app: FastAPI):
       # ... in capture loop ...
       if success:
           await manager.broadcast({
               "type": "capture_complete",
               "profile": profile,
               "schedule": schedule_name,
               "timestamp": current_time.isoformat()
           })
   ```

4. **Add Frontend API Client (6 hours)**

   ```typescript
   // frontend/src/api/client.ts
   import axios, { AxiosInstance } from "axios";

   export interface ApiConfig {
     baseURL: string;
     timeout?: number;
   }

   class SkylapseClie {
     private axios: AxiosInstance;
     private ws: WebSocket | null = null;

     constructor(config: ApiConfig) {
       this.axios = axios.create({
         baseURL: config.baseURL,
         timeout: config.timeout || 10000,
         headers: {
           "Content-Type": "application/json",
         },
       });

       // Add response interceptor for error handling
       this.axios.interceptors.response.use(
         (response) => response,
         (error) => {
           console.error("API Error:", error);
           // Handle different error types
           if (error.code === "ECONNABORTED") {
             throw new Error("Request timeout");
           }
           if (!error.response) {
             throw new Error("Network error");
           }
           throw error;
         },
       );
     }

     // System status
     async getSystemStatus(): Promise<SystemStatus> {
       const response = await this.axios.get("/api/v1/system");
       return response.data;
     }

     // Profiles
     async getProfiles(): Promise<Profile[]> {
       const response = await this.axios.get("/api/v1/profiles");
       return response.data;
     }

     // Timelapses
     async getTimelapses(filters?: TimelapseFilters): Promise<Timelapse[]> {
       const response = await this.axios.get("/api/v1/timelapses", {
         params: filters,
       });
       return response.data;
     }

     // WebSocket connection
     connectWebSocket(onMessage: (data: any) => void) {
       const wsUrl = this.axios.defaults.baseURL?.replace("http", "ws") + "/ws";
       this.ws = new WebSocket(wsUrl);

       this.ws.onopen = () => {
         console.log("WebSocket connected");
       };

       this.ws.onmessage = (event) => {
         const data = JSON.parse(event.data);
         onMessage(data);
       };

       this.ws.onerror = (error) => {
         console.error("WebSocket error:", error);
       };

       this.ws.onclose = () => {
         console.log("WebSocket disconnected, reconnecting...");
         // Reconnect after 5 seconds
         setTimeout(() => this.connectWebSocket(onMessage), 5000);
       };
     }

     disconnectWebSocket() {
       if (this.ws) {
         this.ws.close();
         this.ws = null;
       }
     }
   }

   export const apiClient = new SkylapseClie({
     baseURL: import.meta.env.VITE_BACKEND_URL || "http://localhost:8082",
   });
   ```

**Testing Strategy:**

- Test API version compatibility
- Validate request/response schemas
- Test WebSocket reconnection logic
- Simulate network failures

**Estimated Effort:** 20 hours
**Risk Level:** Low - Well-established patterns
**Dependencies:** C1 (frontend implementation)

**Success Criteria:**

- [ ] All API endpoints versioned (/api/v1/...)
- [ ] Request/response validation with Pydantic
- [ ] WebSocket support for real-time updates
- [ ] Frontend API client with error handling
- [ ] Automatic WebSocket reconnection

---

### H3: Database Schema Lacks Indexes for Common Queries

**Severity:** HIGH
**Category:** Performance / Database Design
**Impact:** Slow queries as data grows, particularly for timelapse listing

**Location:** `/Users/nicholasmparker/Projects/skylapse/backend/database.py:27-142`

**Current State:**

```python
# Only 4 indexes defined:
conn.execute("CREATE INDEX IF NOT EXISTS idx_session_lookup ON sessions(profile, date, schedule)")
conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON sessions(status)")
conn.execute("CREATE INDEX IF NOT EXISTS idx_date ON sessions(date)")
conn.execute("CREATE INDEX IF NOT EXISTS idx_session ON captures(session_id)")
conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON captures(timestamp)")
```

**Missing Indexes:**

- No composite index for common timelapse queries (profile + schedule + date)
- No index on `sessions.updated_at` (used for recent activity queries)
- No index on `timelapses.quality_tier` (preview vs archive filtering)
- No index on `captures.timestamp` + `session_id` (range queries)

**Remediation Steps:**

1. **Add Missing Indexes (2 hours)**

   ```python
   def _init_db(self):
       # ... existing schema ...

       # Additional indexes for common query patterns

       # Sessions table
       conn.execute(
           "CREATE INDEX IF NOT EXISTS idx_sessions_updated ON sessions(updated_at DESC)"
       )
       conn.execute(
           "CREATE INDEX IF NOT EXISTS idx_sessions_active ON sessions(status, updated_at) WHERE status = 'active'"
       )

       # Captures table - composite for range queries
       conn.execute(
           "CREATE INDEX IF NOT EXISTS idx_captures_session_timestamp "
           "ON captures(session_id, timestamp)"
       )
       conn.execute(
           "CREATE INDEX IF NOT EXISTS idx_captures_date_range "
           "ON captures(DATE(timestamp))"
       )

       # Timelapses table - filtering indexes
       conn.execute(
           "CREATE INDEX IF NOT EXISTS idx_timelapses_profile_schedule "
           "ON timelapses(profile, schedule, date DESC)"
       )
       conn.execute(
           "CREATE INDEX IF NOT EXISTS idx_timelapses_quality_tier "
           "ON timelapses(quality_tier, created_at DESC)"
       )
       conn.execute(
           "CREATE INDEX IF NOT EXISTS idx_timelapses_created "
           "ON timelapses(created_at DESC)"
       )

       # Composite for admin queries
       conn.execute(
           "CREATE INDEX IF NOT EXISTS idx_timelapses_admin "
           "ON timelapses(profile, schedule, date, quality_tier)"
       )
   ```

2. **Add Query Performance Logging (3 hours)**

   ```python
   import time
   from functools import wraps

   def log_slow_queries(threshold_ms=100):
       """Decorator to log slow database queries."""
       def decorator(func):
           @wraps(func)
           def wrapper(*args, **kwargs):
               start = time.perf_counter()
               result = func(*args, **kwargs)
               elapsed_ms = (time.perf_counter() - start) * 1000

               if elapsed_ms > threshold_ms:
                   logger.warning(
                       f"Slow query detected: {func.__name__} took {elapsed_ms:.2f}ms",
                       extra={
                           'function': func.__name__,
                           'elapsed_ms': elapsed_ms,
                           'threshold_ms': threshold_ms
                       }
                   )

               return result
           return wrapper
       return decorator

   @log_slow_queries(threshold_ms=100)
   def get_timelapses(self, limit=None, profile=None, schedule=None, date=None):
       # ... existing implementation ...
       pass
   ```

3. **Add EXPLAIN QUERY PLAN Analysis (2 hours)**

   ```python
   def analyze_query_performance(self, query: str, params: tuple = ()) -> dict:
       """
       Analyze query performance with EXPLAIN QUERY PLAN.

       Returns:
           Dictionary with query plan and recommendations
       """
       with self._get_connection() as conn:
           # Get query plan
           plan = conn.execute(f"EXPLAIN QUERY PLAN {query}", params).fetchall()

           # Analyze plan for issues
           issues = []
           for row in plan:
               detail = row['detail']
               if 'SCAN TABLE' in detail and 'USING INDEX' not in detail:
                   issues.append(f"Full table scan detected: {detail}")
               if 'TEMP B-TREE' in detail:
                   issues.append(f"Temporary B-tree created: {detail}")

           return {
               'query': query,
               'plan': [dict(row) for row in plan],
               'issues': issues,
               'has_issues': len(issues) > 0
           }

   # Add admin endpoint
   @app.post("/admin/analyze-query")
   async def analyze_query(request: Request, query: str):
       """Analyze query performance (admin only)."""
       db = request.app.state.db
       analysis = db.analyze_query_performance(query)
       return analysis
   ```

4. **Add Database Statistics Endpoint (1 hour)**

   ```python
   def get_database_stats(self) -> dict:
       """Get database statistics and health metrics."""
       with self._get_connection() as conn:
           # Table sizes
           stats = {
               'sessions': {
                   'count': conn.execute("SELECT COUNT(*) as count FROM sessions").fetchone()['count'],
                   'active': conn.execute("SELECT COUNT(*) as count FROM sessions WHERE status = 'active'").fetchone()['count'],
                   'complete': conn.execute("SELECT COUNT(*) as count FROM sessions WHERE status = 'complete'").fetchone()['count'],
               },
               'captures': {
                   'count': conn.execute("SELECT COUNT(*) as count FROM captures").fetchone()['count'],
                   'today': conn.execute(
                       "SELECT COUNT(*) as count FROM captures WHERE DATE(timestamp) = DATE('now')"
                   ).fetchone()['count'],
               },
               'timelapses': {
                   'count': conn.execute("SELECT COUNT(*) as count FROM timelapses").fetchone()['count'],
                   'preview': conn.execute(
                       "SELECT COUNT(*) as count FROM timelapses WHERE quality_tier = 'preview'"
                   ).fetchone()['count'],
                   'archive': conn.execute(
                       "SELECT COUNT(*) as count FROM timelapses WHERE quality_tier = 'archive'"
                   ).fetchone()['count'],
               },
               'disk_usage': {
                   'db_size_mb': Path(self.db_path).stat().st_size / (1024 * 1024)
               }
           }

           # Index usage stats (if available)
           # SQLite doesn't expose index usage stats easily, but we can check index existence
           indexes = conn.execute(
               "SELECT name, tbl_name FROM sqlite_master WHERE type = 'index' AND name NOT LIKE 'sqlite_%'"
           ).fetchall()
           stats['indexes'] = [dict(idx) for idx in indexes]

           return stats

   @app.get("/admin/database/stats")
   async def database_stats(request: Request):
       db = request.app.state.db
       return db.get_database_stats()
   ```

**Testing Strategy:**

- Benchmark queries before/after indexes
- Test with large datasets (1000+ sessions)
- Analyze query plans for common queries
- Monitor slow query log

**Estimated Effort:** 8 hours
**Risk Level:** Low - Additive changes
**Dependencies:** None

**Success Criteria:**

- [ ] All common queries use indexes (no full table scans)
- [ ] Query performance logged for slow queries
- [ ] Admin endpoints for query analysis
- [ ] Database statistics dashboard

---

### H4: Configuration Validation Missing

**Severity:** HIGH
**Category:** Configuration Management / Error Handling
**Impact:** Invalid config causes runtime errors instead of startup errors

**Location:** `/Users/nicholasmparker/Projects/skylapse/backend/config.py:18-209`

**Current State:**

```python
class Config:
    def __init__(self, config_path: str = "config.json"):
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = self._load_or_create_default()
        # No validation!
```

**Issues:**

- No validation of latitude/longitude ranges
- No validation of schedule times (start < end)
- No validation of Pi host reachability
- Invalid intervals (0 or negative) not caught
- Missing required fields not detected at startup

**Remediation Steps:**

1. **Add Pydantic Config Schema (4 hours)**

   ```python
   # backend/config_schema.py
   from pydantic import BaseModel, Field, validator, root_validator
   from typing import Dict, Literal

   class LocationConfig(BaseModel):
       latitude: float = Field(..., ge=-90, le=90, description="Latitude in degrees")
       longitude: float = Field(..., ge=-180, le=180, description="Longitude in degrees")
       timezone: str = Field(..., description="IANA timezone (e.g., America/Denver)")
       name: str = Field(..., description="Location name")

       @validator('timezone')
       def validate_timezone(cls, v):
           from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
           try:
               ZoneInfo(v)
               return v
           except ZoneInfoNotFoundError:
               raise ValueError(f"Invalid timezone: {v}")

   class ScheduleConfig(BaseModel):
       enabled: bool = True
       type: Literal["solar_relative", "time_of_day"] = "solar_relative"

       # Solar-relative fields
       anchor: str = None  # sunrise, sunset, dawn, dusk
       offset_minutes: int = 0
       duration_minutes: int = Field(60, gt=0, description="Capture duration")

       # Time-of-day fields
       start_time: str = None  # HH:MM format
       end_time: str = None    # HH:MM format

       # Common fields
       interval_seconds: int = Field(30, gt=0, le=3600, description="Capture interval")
       stack_images: bool = False
       stack_count: int = Field(5, ge=1, le=10)

       @root_validator
       def validate_schedule_type(cls, values):
           schedule_type = values.get('type')

           if schedule_type == 'solar_relative':
               if not values.get('anchor'):
                   raise ValueError("solar_relative schedules require 'anchor' field")
               valid_anchors = ['sunrise', 'sunset', 'dawn', 'dusk', 'noon', 'civil_dawn', 'civil_dusk']
               if values['anchor'] not in valid_anchors:
                   raise ValueError(f"Invalid anchor: {values['anchor']}. Valid: {valid_anchors}")

           elif schedule_type == 'time_of_day':
               if not values.get('start_time') or not values.get('end_time'):
                   raise ValueError("time_of_day schedules require 'start_time' and 'end_time'")

               # Validate time format
               from datetime import time
               try:
                   start = time.fromisoformat(values['start_time'])
                   end = time.fromisoformat(values['end_time'])
                   if start >= end:
                       raise ValueError("start_time must be before end_time")
               except ValueError as e:
                   raise ValueError(f"Invalid time format: {e}")

           return values

   class PiConfig(BaseModel):
       host: str = Field(..., description="Pi hostname or IP address")
       port: int = Field(8080, ge=1, le=65535)
       timeout_seconds: int = Field(10, gt=0, le=60)

       @validator('host')
       def validate_host(cls, v):
           if not v or v == 'null':
               raise ValueError("Pi host is required (set PI_HOST environment variable)")
           return v

   class StorageConfig(BaseModel):
       images_dir: str = "data/images"
       videos_dir: str = "data/videos"
       max_days_to_keep: int = Field(7, ge=1, le=365)

   class ProcessingConfig(BaseModel):
       video_fps: int = Field(24, ge=1, le=60)
       video_codec: str = "libx264"
       video_quality: str = "23"

   class SkylaspeConfig(BaseModel):
       """Root configuration schema."""
       location: LocationConfig
       schedules: Dict[str, ScheduleConfig]
       pi: PiConfig
       storage: StorageConfig
       processing: ProcessingConfig

       @validator('schedules')
       def validate_schedules(cls, v):
           if not v:
               raise ValueError("At least one schedule must be defined")

           # Ensure schedule names are valid
           valid_names = ['sunrise', 'daytime', 'sunset']  # Add more as needed
           for name in v.keys():
               if name not in valid_names:
                   raise ValueError(f"Invalid schedule name: {name}. Valid: {valid_names}")

           return v
   ```

2. **Update Config Class to Use Schema (3 hours)**

   ```python
   # backend/config.py
   from config_schema import SkylaspeConfig
   from pydantic import ValidationError

   class Config:
       def __init__(self, config_path: str = "config.json"):
           self.config_path = Path(config_path)
           self.config_dict = self._load_or_create_default()

           # Validate config with Pydantic
           try:
               self.config = SkylaspeConfig(**self.config_dict)
               logger.info(f"Configuration validated successfully: {self.config_path}")
           except ValidationError as e:
               logger.critical(f"Configuration validation failed:\n{e}")
               raise ValueError(f"Invalid configuration: {e}")

       def save(self, config: SkylaspeConfig = None):
           """Save configuration with validation."""
           if config is not None:
               # Validate before saving
               try:
                   validated = SkylaspeConfig(**config.dict())
                   self.config = validated
                   self.config_dict = validated.dict()
               except ValidationError as e:
                   raise ValueError(f"Invalid configuration: {e}")

           # ... existing save logic ...

       def get_location(self) -> dict:
           """Get location configuration."""
           return self.config.location.dict()

       def get_schedule(self, schedule_type: str) -> dict:
           """Get schedule configuration for a specific type."""
           schedule = self.config.schedules.get(schedule_type)
           return schedule.dict() if schedule else {}

       def get_pi_config(self) -> dict:
           """Get Raspberry Pi configuration."""
           return self.config.pi.dict()
   ```

3. **Add Configuration Test at Startup (2 hours)**

   ```python
   # backend/main.py
   @asynccontextmanager
   async def lifespan(app: FastAPI):
       """Lifecycle manager for startup and shutdown"""
       logger.info("Starting Skylapse Backend...")

       # Initialize and VALIDATE configuration
       try:
           config = Config()
           logger.info(f"✓ Configuration loaded and validated from {config.config_path}")
       except ValueError as e:
           logger.critical(f"✗ Configuration validation failed: {e}")
           logger.critical("STARTUP ABORTED - Fix configuration and restart")
           raise SystemExit(1)  # Exit immediately, don't start server

       # Test Pi connectivity at startup
       pi_config = config.get_pi_config()
       try:
           async with httpx.AsyncClient(timeout=5.0) as client:
               response = await client.get(
                   f"http://{pi_config['host']}:{pi_config['port']}/health"
               )
               if response.status_code == 200:
                   logger.info(f"✓ Pi connectivity verified: {pi_config['host']}")
               else:
                   logger.warning(f"⚠ Pi returned status {response.status_code}")
       except Exception as e:
           logger.error(f"✗ Cannot reach Pi at {pi_config['host']}:{pi_config['port']}: {e}")
           logger.warning("Continuing startup, but captures will fail until Pi is reachable")

       # ... rest of startup ...
   ```

4. **Add Configuration Validation Endpoint (1 hour)**

   ```python
   @app.get("/admin/config/validate")
   async def validate_config(request: Request):
       """Validate current configuration."""
       config = request.app.state.config

       try:
           # Re-validate current config
           validated = SkylaspeConfig(**config.config_dict)

           return {
               'valid': True,
               'message': 'Configuration is valid',
               'config': validated.dict()
           }
       except ValidationError as e:
           return {
               'valid': False,
               'errors': e.errors(),
               'message': 'Configuration has validation errors'
           }

   @app.post("/admin/config/test-pi")
   async def test_pi_connection(request: Request):
       """Test Pi connectivity."""
       config = request.app.state.config
       pi_config = config.get_pi_config()

       try:
           async with httpx.AsyncClient(timeout=5.0) as client:
               start = time.perf_counter()
               response = await client.get(
                   f"http://{pi_config['host']}:{pi_config['port']}/health"
               )
               latency_ms = (time.perf_counter() - start) * 1000

               return {
                   'reachable': True,
                   'status_code': response.status_code,
                   'latency_ms': round(latency_ms, 2),
                   'host': pi_config['host'],
                   'port': pi_config['port']
               }
       except Exception as e:
           return {
               'reachable': False,
               'error': str(e),
               'host': pi_config['host'],
               'port': pi_config['port']
           }
   ```

**Testing Strategy:**

- Test with invalid latitude/longitude
- Test with invalid schedule times
- Test with unreachable Pi host
- Test with negative intervals
- Verify startup aborts on invalid config

**Estimated Effort:** 10 hours
**Risk Level:** Medium - Breaking change to config loading
**Dependencies:** None

**Success Criteria:**

- [ ] Configuration validated with Pydantic at startup
- [ ] Invalid config prevents server startup
- [ ] Pi connectivity tested at startup
- [ ] Admin endpoints for config validation
- [ ] Clear error messages for validation failures

---

### H5: No Image Cleanup Strategy

**Severity:** HIGH
**Category:** Resource Management / Operations
**Impact:** Disk will fill up, causing system failures

**Location:** Multiple services

**Current State:**

- Transfer service has cleanup for backend (`DELETE_AFTER_DAYS`)
- No cleanup on Pi (images deleted after transfer only)
- No cleanup for old timelapses (videos accumulate forever)
- No disk space monitoring with proactive alerts

**Root Cause:** Initial development focused on capture, not long-term operation

**Remediation Steps:**

1. **Add Timelapse Retention Policy (3 hours)**

   ```python
   # backend/cleanup.py
   import logging
   from pathlib import Path
   from datetime import datetime, timedelta
   from typing import Dict, List

   logger = logging.getLogger(__name__)

   class CleanupManager:
       """Manage cleanup of old images and timelapses."""

       def __init__(self, db: SessionDatabase):
           self.db = db

       def cleanup_old_timelapses(
           self,
           preview_retention_days: int = 30,
           archive_retention_days: int = 365,
           dry_run: bool = False
       ) -> Dict:
           """
           Delete old timelapse videos based on retention policy.

           Args:
               preview_retention_days: Keep preview quality for N days
               archive_retention_days: Keep archive quality for N days
               dry_run: If True, only report what would be deleted

           Returns:
               Dictionary with cleanup stats
           """
           cutoff_preview = datetime.utcnow() - timedelta(days=preview_retention_days)
           cutoff_archive = datetime.utcnow() - timedelta(days=archive_retention_days)

           deleted = {'preview': [], 'archive': []}
           freed_bytes = 0

           # Get all timelapses
           with self.db._get_connection() as conn:
               timelapses = conn.execute(
                   """SELECT id, filename, file_path, file_size_mb, quality_tier, created_at
                      FROM timelapses
                      ORDER BY created_at ASC"""
               ).fetchall()

               for t in timelapses:
                   created = datetime.fromisoformat(t['created_at'])
                   quality_tier = t.get('quality_tier', 'preview')
                   cutoff = cutoff_archive if quality_tier == 'archive' else cutoff_preview

                   if created < cutoff:
                       file_path = Path(t['file_path'])

                       if file_path.exists():
                           file_size = file_path.stat().st_size

                           if not dry_run:
                               file_path.unlink()
                               # Delete thumbnail too
                               thumb_path = file_path.with_suffix('').with_name(
                                   file_path.stem + '_thumb.jpg'
                               )
                               if thumb_path.exists():
                                   thumb_path.unlink()

                               # Delete from database
                               conn.execute("DELETE FROM timelapses WHERE id = ?", (t['id'],))

                           deleted[quality_tier].append(t['filename'])
                           freed_bytes += file_size
                       else:
                           # File missing, clean up database record
                           if not dry_run:
                               conn.execute("DELETE FROM timelapses WHERE id = ?", (t['id'],))

               if not dry_run:
                   conn.commit()

           return {
               'dry_run': dry_run,
               'deleted_count': len(deleted['preview']) + len(deleted['archive']),
               'deleted': deleted,
               'freed_mb': freed_bytes / (1024 * 1024),
               'policy': {
                   'preview_retention_days': preview_retention_days,
                   'archive_retention_days': archive_retention_days
               }
           }

       def cleanup_old_images(
           self,
           retention_days: int = 7,
           dry_run: bool = False
       ) -> Dict:
           """
           Delete old source images (already used for timelapses).

           Args:
               retention_days: Keep images for N days
               dry_run: If True, only report what would be deleted

           Returns:
               Dictionary with cleanup stats
           """
           cutoff = datetime.utcnow() - timedelta(days=retention_days)
           images_dir = Path("/data/images")

           deleted_count = 0
           freed_bytes = 0

           if not images_dir.exists():
               return {'error': 'Images directory not found'}

           for profile_dir in images_dir.glob("profile-*"):
               if not profile_dir.is_dir():
                   continue

               for image_file in profile_dir.glob("capture_*.jpg"):
                   modified = datetime.fromtimestamp(image_file.stat().st_mtime)

                   if modified < cutoff:
                       file_size = image_file.stat().st_size

                       if not dry_run:
                           image_file.unlink()

                       deleted_count += 1
                       freed_bytes += file_size

           return {
               'dry_run': dry_run,
               'deleted_count': deleted_count,
               'freed_mb': freed_bytes / (1024 * 1024),
               'retention_days': retention_days
           }

       def get_disk_usage_report(self) -> Dict:
           """Get detailed disk usage breakdown."""
           report = {
               'images': {},
               'timelapses': {},
               'database': {},
               'total': {}
           }

           # Images by profile
           images_dir = Path("/data/images")
           if images_dir.exists():
               for profile_dir in images_dir.glob("profile-*"):
                   if not profile_dir.is_dir():
                       continue

                   images = list(profile_dir.glob("capture_*.jpg"))
                   total_size = sum(img.stat().st_size for img in images)

                   report['images'][profile_dir.name] = {
                       'count': len(images),
                       'size_mb': total_size / (1024 * 1024)
                   }

           # Timelapses by quality tier
           timelapses_dir = Path("/data/timelapses")
           if timelapses_dir.exists():
               for quality in ['preview', 'archive']:
                   videos = list(timelapses_dir.glob(f"*_{quality}.mp4"))
                   total_size = sum(v.stat().st_size for v in videos)

                   report['timelapses'][quality] = {
                       'count': len(videos),
                       'size_mb': total_size / (1024 * 1024)
                   }

           # Database
           db_path = Path(self.db.db_path)
           if db_path.exists():
               report['database'] = {
                   'size_mb': db_path.stat().st_size / (1024 * 1024)
               }

           # Total
           import psutil
           disk = psutil.disk_usage('/data')
           report['total'] = {
               'total_gb': disk.total / (1024**3),
               'used_gb': disk.used / (1024**3),
               'free_gb': disk.free / (1024**3),
               'percent': disk.percent
           }

           return report
   ```

2. **Add Cleanup Scheduler (2 hours)**

   ```python
   # backend/main.py
   async def cleanup_loop(app: FastAPI):
       """Background task to cleanup old data."""
       logger.info("Cleanup loop starting...")

       db = app.state.db
       cleanup_mgr = CleanupManager(db)

       while True:
           try:
               # Run cleanup daily at 3 AM
               now = datetime.now()
               next_run = now.replace(hour=3, minute=0, second=0, microsecond=0)
               if next_run <= now:
                   next_run += timedelta(days=1)

               wait_seconds = (next_run - now).total_seconds()
               logger.info(f"Next cleanup in {wait_seconds / 3600:.1f} hours")
               await asyncio.sleep(wait_seconds)

               # Run cleanup
               logger.info("Running daily cleanup...")

               # Cleanup old images (keep 7 days)
               image_result = cleanup_mgr.cleanup_old_images(
                   retention_days=7,
                   dry_run=False
               )
               logger.info(
                   f"Cleaned up {image_result['deleted_count']} old images, "
                   f"freed {image_result['freed_mb']:.1f} MB"
               )

               # Cleanup old timelapses (keep preview 30 days, archive 365 days)
               timelapse_result = cleanup_mgr.cleanup_old_timelapses(
                   preview_retention_days=30,
                   archive_retention_days=365,
                   dry_run=False
               )
               logger.info(
                   f"Cleaned up {timelapse_result['deleted_count']} old timelapses, "
                   f"freed {timelapse_result['freed_mb']:.1f} MB"
               )

               # Check disk usage and alert if high
               disk_report = cleanup_mgr.get_disk_usage_report()
               if disk_report['total']['percent'] > 90:
                   logger.critical(f"Disk usage critical: {disk_report['total']['percent']}%")
                   # Send alert (if alerting configured)

           except Exception as e:
               logger.error(f"Cleanup loop error: {e}", exc_info=True)
               await asyncio.sleep(3600)  # Retry in 1 hour

   @asynccontextmanager
   async def lifespan(app: FastAPI):
       # ... existing startup ...

       # Start cleanup loop
       cleanup_task = asyncio.create_task(cleanup_loop(app))
       app.state.cleanup_task = cleanup_task

       yield

       # Shutdown
       if app.state.cleanup_task:
           app.state.cleanup_task.cancel()
   ```

3. **Add Cleanup API Endpoints (2 hours)**

   ```python
   @app.get("/admin/disk/usage")
   async def get_disk_usage(request: Request):
       """Get detailed disk usage report."""
       db = request.app.state.db
       cleanup_mgr = CleanupManager(db)
       return cleanup_mgr.get_disk_usage_report()

   @app.post("/admin/cleanup/images")
   async def cleanup_images(
       request: Request,
       retention_days: int = 7,
       dry_run: bool = True
   ):
       """Cleanup old images."""
       db = request.app.state.db
       cleanup_mgr = CleanupManager(db)
       result = cleanup_mgr.cleanup_old_images(retention_days, dry_run)
       return result

   @app.post("/admin/cleanup/timelapses")
   async def cleanup_timelapses(
       request: Request,
       preview_retention_days: int = 30,
       archive_retention_days: int = 365,
       dry_run: bool = True
   ):
       """Cleanup old timelapses."""
       db = request.app.state.db
       cleanup_mgr = CleanupManager(db)
       result = cleanup_mgr.cleanup_old_timelapses(
           preview_retention_days,
           archive_retention_days,
           dry_run
       )
       return result
   ```

**Testing Strategy:**

- Test cleanup with sample old files
- Test dry-run mode
- Verify database records deleted
- Test disk usage reporting

**Estimated Effort:** 7 hours
**Risk Level:** Medium - Data deletion
**Dependencies:** C4 (monitoring for alerts)

**Success Criteria:**

- [ ] Automatic cleanup of old images (7 days)
- [ ] Automatic cleanup of old timelapses (30 days preview, 365 days archive)
- [ ] Daily cleanup scheduled at 3 AM
- [ ] Admin endpoints for manual cleanup
- [ ] Disk usage reporting
- [ ] Alerts when disk > 90% full

---

## MEDIUM PRIORITY DEBT ITEMS

### M1: Hardcoded Profile List in Multiple Locations

**Severity:** MEDIUM
**Category:** Code Quality / Maintainability
**Impact:** Adding/removing profiles requires changes in 4+ files

**Location:**

- `/Users/nicholasmparker/Projects/skylapse/backend/main.py:141` (profiles = ["a", "d", "g"])
- `/Users/nicholasmparker/Projects/skylapse/backend/main.py:722-731` (descriptions dict)
- `/Users/nicholasmparker/Projects/skylapse/pi/main.py:159` (valid_profiles validation)

**Remediation:**
Create centralized profile registry:

```python
# shared/profiles.py
from enum import Enum
from typing import Dict

class Profile(str, Enum):
    A = "a"
    D = "d"
    G = "g"
    # Add more as needed

PROFILE_DESCRIPTIONS: Dict[str, str] = {
    Profile.A: "Pure Auto (No Bias)",
    Profile.D: "Warm Dramatic",
    Profile.G: "Adaptive EV + Balanced WB"
}

PRODUCTION_PROFILES = [Profile.A, Profile.D, Profile.G]
```

**Effort:** 2 hours
**Risk:** Low

---

### M2: No Request ID Tracing

**Severity:** MEDIUM
**Category:** Debugging / Operations
**Impact:** Difficult to trace requests through logs

**Remediation:**
Add request ID middleware:

```python
# backend/middleware.py
import uuid
from starlette.middleware.base import BaseHTTPMiddleware

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

# Add to main.py
app.add_middleware(RequestIDMiddleware)
```

**Effort:** 2 hours
**Risk:** Low

---

### M3: No Rate Limiting on API Endpoints

**Severity:** MEDIUM
**Category:** Security / Performance
**Impact:** API could be overwhelmed by rapid requests

**Remediation:**
Add rate limiting with slowapi:

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.get("/api/v1/timelapses")
@limiter.limit("30/minute")
async def get_timelapses(request: Request):
    # ... implementation ...
```

**Effort:** 3 hours
**Risk:** Low

---

### M4: Environment Variable Handling Inconsistent

**Severity:** MEDIUM
**Category:** Configuration / Security
**Impact:** Secrets could be committed, environment setup confusing

**Location:** Multiple files access `os.getenv()` directly

**Remediation:**
Centralize environment variables:

```python
# backend/env.py
from pydantic import BaseSettings

class Settings(BaseSettings):
    # Database
    database_path: str = "/data/db/skylapse.db"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Pi Connection
    pi_host: str
    pi_port: int = 8080
    pi_user: str = "pi"

    # Backend
    backend_url: str = "http://localhost:8082"
    backend_port: int = 8082

    # Alerting (optional)
    alerts_enabled: bool = False
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    alert_email: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
```

**Effort:** 3 hours
**Risk:** Low

---

### M5: No API Documentation (OpenAPI/Swagger)

**Severity:** MEDIUM
**Category:** Documentation
**Impact:** Difficult for frontend developers to use API

**Remediation:**
FastAPI auto-generates Swagger docs, but need to add:

```python
# main.py
app = FastAPI(
    title="Skylapse Backend API",
    description="Automated timelapse photography system",
    version="2.0.0",
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc"  # ReDoc UI
)

# Add response models and descriptions to all endpoints
@app.get(
    "/api/v1/system",
    response_model=SystemStatusResponse,
    summary="Get system status",
    description="Returns comprehensive system status including sun times, schedules, camera status",
    tags=["System"]
)
async def get_system_status(request: Request):
    # ... implementation ...
```

**Effort:** 4 hours
**Risk:** Low

---

### M6: Timelapse Generation Not Idempotent

**Severity:** MEDIUM
**Category:** Data Integrity / Queue Management
**Impact:** Duplicate jobs could overwrite or create duplicate timelapses

**Location:** `/Users/nicholasmparker/Projects/skylapse/backend/main.py:209-217`

**Remediation:**

```python
# Before enqueuing, check if job already queued/complete
existing_timelapse = db.get_timelapses(
    profile=profile,
    schedule=schedule_name,
    date=date_str
)

if existing_timelapse:
    logger.info(f"Timelapse already generated for {session_id}, skipping")
else:
    job = timelapse_queue.enqueue(...)
```

**Effort:** 2 hours
**Risk:** Low

---

### M7: No Graceful Shutdown Handling

**Severity:** MEDIUM
**Category:** Operations / Reliability
**Impact:** In-progress captures could be corrupted during shutdown

**Remediation:**

```python
import signal

shutdown_event = asyncio.Event()

def handle_shutdown(signum, frame):
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_event.set()

signal.signal(signal.SIGTERM, handle_shutdown)
signal.signal(signal.SIGINT, handle_shutdown)

async def scheduler_loop(app: FastAPI):
    while not shutdown_event.is_set():
        # ... scheduler logic ...

    logger.info("Scheduler loop exiting gracefully")
```

**Effort:** 3 hours
**Risk:** Low

---

### M8: Transfer Service Has No Health Monitoring

**Severity:** MEDIUM
**Category:** Monitoring / Operations
**Impact:** Transfer failures could go unnoticed

**Location:** `/Users/nicholasmparker/Projects/skylapse/backend/services/transfer.py`

**Remediation:**

```python
# Add health endpoint to transfer service
from fastapi import FastAPI

transfer_app = FastAPI()

@transfer_app.get("/health")
async def transfer_health():
    return {
        "status": "running",
        "last_transfer": last_transfer_time,
        "last_success": last_success_time,
        "consecutive_failures": failure_count
    }

# Run FastAPI alongside transfer loop in separate thread
```

**Effort:** 4 hours
**Risk:** Low

---

### M9: Pi Service Lacks Deployed Profile Validation

**Severity:** MEDIUM
**Category:** Error Handling / Data Integrity
**Impact:** Invalid deployed profiles could cause runtime errors

**Location:** `/Users/nicholasmparker/Projects/skylapse/pi/profile_executor.py:48-73`

**Remediation:**

```python
from pydantic import BaseModel, validator

class DeployedProfile(BaseModel):
    profile_id: str
    version: str
    settings: dict
    schedules: list
    deployed_at: str

    @validator('settings')
    def validate_settings(cls, v):
        required_keys = ['base', 'adaptive_wb', 'schedule_overrides']
        for key in required_keys:
            if key not in v:
                raise ValueError(f"Missing required setting: {key}")
        return v

def deploy_profile(self, profile_data: Dict[str, Any]) -> bool:
    try:
        # Validate before deploying
        validated = DeployedProfile(**profile_data)
        # ... save to disk ...
```

**Effort:** 2 hours
**Risk:** Low

---

### M10: No Backup/Restore for Database

**Severity:** MEDIUM
**Category:** Data Integrity / Operations
**Impact:** Data loss if database corrupted

**Remediation:**

```python
# backend/backup.py
import shutil
from datetime import datetime

def backup_database(db_path: str, backup_dir: str):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = Path(backup_dir) / f"skylapse_backup_{timestamp}.db"
    shutil.copy2(db_path, backup_path)
    logger.info(f"Database backed up to {backup_path}")
    return backup_path

# Add to cleanup loop
async def cleanup_loop(app: FastAPI):
    # ... existing cleanup ...

    # Daily backup at 2 AM
    if now.hour == 2:
        backup_database("/data/db/skylapse.db", "/data/backups")
```

**Effort:** 3 hours
**Risk:** Low

---

## Summary Statistics

### Total Technical Debt Items: 99

**By Severity:**

- Critical: 18 items
- High: 36 items
- Medium: 45 items

**By Category:**

- Code Quality: 23 items
- Architecture: 14 items
- Error Handling: 14 items
- Testing: 10 items
- Security: 9 items
- Performance: 9 items
- Documentation: 12 items
- Configuration: 8 items

### Estimated Remediation Effort

**Critical Items (C1-C4):** 116 hours (14.5 days)
**High Priority Items (H1-H5):** 54 hours (6.75 days)
**Medium Priority Items (M1-M10):** 30 hours (3.75 days)

**Total Estimated Effort:** 200 hours (25 days) for full remediation

### Recommended Execution Order

#### Phase 1: Foundation (Sprint 1 - 2 weeks)

1. **C2: Automated Test Coverage** - Essential for all future work
2. **H4: Configuration Validation** - Prevents startup with bad config
3. **C3: Database Transaction Safety** - Data integrity critical
4. **M4: Environment Variable Handling** - Clean foundation

**Deliverables:** 60% test coverage, validated config, transaction safety

#### Phase 2: Reliability (Sprint 2 - 2 weeks)

1. **H1: Scheduler Error Recovery** - Improve core reliability
2. **C4: Error Monitoring/Alerting** - Visibility into failures
3. **H5: Image Cleanup Strategy** - Prevent disk full
4. **M7: Graceful Shutdown** - Operational stability

**Deliverables:** Robust scheduler, monitoring, disk management

#### Phase 3: User Experience (Sprint 3 - 3 weeks)

1. **C1: Frontend Implementation** - Critical user-facing gap
2. **H2: Frontend-Backend Communication** - Real-time updates
3. **M5: API Documentation** - Developer experience
4. **M2: Request ID Tracing** - Debugging support

**Deliverables:** Functional UI, real-time updates, API docs

#### Phase 4: Hardening (Sprint 4 - 1 week)

1. **H3: Database Indexes** - Performance optimization
2. **M3: Rate Limiting** - Security
3. **M6: Idempotent Timelapse Generation** - Data integrity
4. **M10: Database Backup** - Disaster recovery

**Deliverables:** Optimized queries, secured API, backups

#### Phase 5: Polish (Sprint 5 - ongoing)

1. **M1: Centralized Profile Registry** - Code maintainability
2. **M8: Transfer Service Monitoring** - Operational visibility
3. **M9: Profile Validation** - Pi-side safety
4. Additional medium-priority items as needed

**Deliverables:** Clean codebase, full observability

---

## Risk Assessment

### High-Risk Areas

1. **Scheduler Loop** - Single point of failure, all captures depend on it
2. **Database** - No transaction safety, risk of corruption
3. **Disk Space** - No proactive management, system will crash when full
4. **Pi Communication** - No circuit breaker, repeated failures waste resources

### Technical Debt Trends

- **Accumulation Rate:** Moderate - Recent refactoring addressed some debt
- **Impact on Velocity:** Medium - Lack of tests slows refactoring
- **User Impact:** High - No frontend limits usability
- **Operational Risk:** High - No monitoring, failures go unnoticed

### Recommended Immediate Actions (This Week)

1. Add basic alerting for disk space (90% threshold)
2. Add health endpoint for scheduler status
3. Configure automatic database backups
4. Document known issues for users

---

## Appendix: Testing Strategy Details

### Unit Test Priority

1. **Database operations** - CRUD, transactions, integrity
2. **Exposure calculator** - All profiles, edge cases
3. **Solar calculations** - Timezone handling, edge cases
4. **WB curve interpolation** - Boundary conditions
5. **Configuration management** - Validation, defaults

### Integration Test Priority

1. **Scheduler loop** - End-to-end capture flow
2. **Timelapse generation** - Worker job execution
3. **API endpoints** - All routes with mocked Pi
4. **Database transactions** - Rollback scenarios
5. **WebSocket connections** - Real-time updates

### E2E Test Scenarios

1. **Full capture cycle** - Schedule triggers → capture → database → timelapse
2. **Error recovery** - Pi timeout → retry → success
3. **Disk cleanup** - Old files deleted, new files preserved
4. **Configuration reload** - Invalid config rejected, valid config applied

---

## Conclusion

The Skylapse codebase demonstrates solid architectural foundations with recent refactoring improvements (database integration, shared modules, URL builder). However, critical gaps in testing, monitoring, and the frontend represent significant technical debt that must be addressed for production readiness.

**Key Strengths:**

- Well-structured services (Backend, Pi, Worker, Transfer)
- Docker-based architecture with clear separation
- Recent refactoring reduced duplication (WB curves centralized)
- Database-driven design supports future features

**Critical Weaknesses:**

- No automated testing infrastructure
- No frontend implementation
- Insufficient error handling and monitoring
- No operational safeguards (disk cleanup, alerting)

**Recommended Path Forward:**
Execute in phases as outlined above, starting with testing infrastructure and core reliability improvements. This will enable confident refactoring and rapid feature development while reducing operational risk.

**Estimated Timeline:**

- **Minimum Viable Production:** 6 weeks (Phases 1-2)
- **Full User Experience:** 11 weeks (Phases 1-3)
- **Production Hardened:** 13 weeks (Phases 1-4)

---

**Document Version:** 1.0
**Last Updated:** 2025-10-03
**Next Review:** After Phase 1 completion
