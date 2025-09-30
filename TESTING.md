# Skylapse Testing Standards

**Rule**: All tests follow these standards. No exceptions. No variations.

---

## Test Organization

### Directory Structure

```
skylapse/
├── backend/
│   ├── test_integration.py      # Backend integration tests
│   └── test_unit_*.py            # Backend unit tests (if needed)
├── pi/
│   ├── test_integration.py      # Pi/capture service tests
│   └── test_unit_*.py            # Pi unit tests (if needed)
├── frontend/
│   └── tests/                    # Frontend tests (Playwright)
│       ├── system.spec.ts        # System-level tests
│       └── *.spec.ts             # Feature tests
└── TESTING.md                    # This file
```

### Naming Convention

- **Integration tests**: `test_integration.py` (one per service)
- **Unit tests**: `test_unit_<module>.py` (e.g., `test_unit_config.py`)
- **Frontend tests**: `*.spec.ts` (Playwright convention)

---

## How to Run Tests

### Backend Tests

```bash
# Location: /backend/test_integration.py
# Run with pytest (requires dependencies installed)

# Local Python:
cd backend
python3 -m pytest test_integration.py -v

# Docker (when pytest added to requirements.txt):
docker-compose run --rm backend python3 -m pytest test_integration.py -v
```

### Pi/Capture Tests

```bash
# Location: /pi/test_integration.py
# Run on Pi or with MOCK_CAMERA=true locally

# On Pi:
cd ~/skylapse-capture
python3 -m pytest test_integration.py -v

# Locally with mock:
cd pi
MOCK_CAMERA=true python3 -m pytest test_integration.py -v
```

### Frontend Tests (Playwright)

```bash
# Location: /frontend/tests/*.spec.ts
# ALWAYS run against Docker services

# Start services first:
docker-compose up frontend-dev

# Run tests:
cd frontend
npm run test           # Run all tests
npm run test:headed    # Run with browser visible
npm run test:ui        # Interactive UI mode
```

---

## Test Types

### 1. Integration Tests

**Purpose**: Verify components work together correctly
**Location**: `test_integration.py` in each service directory
**Coverage**:

- Config loading/saving
- API endpoints
- Service initialization
- Cross-component interactions

**Example**:

```python
def test_config_loads_and_saves():
    """Test config creates, modifies, and persists correctly"""
    config = Config("test_config.json")
    config.set("location.name", "Test")
    assert config.get("location.name") == "Test"
```

### 2. Unit Tests

**Purpose**: Test individual functions/classes in isolation
**Location**: `test_unit_<module>.py` in service directory
**Use sparingly**: Only when integration tests aren't sufficient

### 3. E2E Tests (Frontend)

**Purpose**: Test user workflows end-to-end
**Location**: `frontend/tests/*.spec.ts`
**Must**: Always run against Docker containers (not mock data)

---

## Test Requirements

### All Tests Must:

1. **Be runnable locally** - No CI/CD-only tests
2. **Use pytest** (Python) or **Playwright** (TypeScript)
3. **Clean up after themselves** - No leftover files/state
4. **Run independently** - No test depends on another test
5. **Have clear names** - `test_config_atomic_save_prevents_corruption` not `test1`

### Python Tests Must:

1. Use `pytest` framework (no unittest, no nose)
2. Follow naming: `test_<feature>_<behavior>()`
3. Use `tmp_path` fixture for file operations
4. Import from service directory (no cross-service imports)

### Frontend Tests Must:

1. Use Playwright framework
2. Start with services running: `docker-compose up frontend-dev`
3. Test against `http://localhost:3000`
4. Clean up test data (if any created)

---

## Adding Dependencies

### Backend/Pi Python Dependencies

**File**: `requirements.txt` in service directory

To add pytest:

```txt
# requirements.txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
astral==3.2
httpx==0.25.2

# Testing (optional - only if running tests in Docker)
pytest==8.4.2
pytest-asyncio==0.24.0
```

### Frontend Dependencies

**File**: `frontend/package.json`

Playwright already included:

```json
"devDependencies": {
  "@playwright/test": "^1.48.2"
}
```

---

## Running Full Test Suite

```bash
# 1. Backend integration tests (when pytest added)
docker-compose run --rm backend python3 -m pytest test_integration.py -v

# 2. Pi/capture tests (on Pi or locally with mock)
MOCK_CAMERA=true python3 -m pytest pi/test_integration.py -v

# 3. Frontend E2E tests (against Docker)
docker-compose up frontend-dev &
cd frontend && npm run test
```

---

## Test Coverage Guidelines

### What to Test:

✅ Core functionality (config, exposure, solar calculations)
✅ API endpoints (status, health, capture)
✅ Error handling (invalid inputs, missing files)
✅ User workflows (camera preview, schedule management)

### What NOT to Test:

❌ Third-party libraries (picamera2, astral, fastapi)
❌ Language features (Python dict, TypeScript arrays)
❌ Trivial getters/setters

### Coverage Target:

- **Critical code**: 80%+ (config, exposure, scheduler)
- **API endpoints**: 100% (all endpoints have at least smoke test)
- **Frontend features**: 100% (all user-visible features tested)

---

## Test Data

### Fixtures Location:

```
tests/
├── fixtures/
│   ├── test_config.json       # Sample config for tests
│   ├── test_image.jpg         # Sample image for processing
│   └── mock_responses.json    # Mock API responses
```

### Creating Test Data:

```python
# Good: Use pytest fixtures
@pytest.fixture
def sample_config():
    return {"location": {"latitude": 39.0, "longitude": -105.0}}

# Bad: Hardcode in tests
def test_something():
    config = {"location": {"latitude": 39.0, ...}}  # Don't do this
```

---

## CI/CD Integration (Future)

When ready to add CI/CD:

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: docker-compose run --rm backend python3 -m pytest test_integration.py -v

  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: docker-compose up -d frontend-dev
      - run: cd frontend && npm ci && npm run test
```

---

## Examples

### Good Test Structure

```python
# backend/test_integration.py

class TestConfig:
    """Test configuration management"""

    def test_config_atomic_save_prevents_corruption(self, tmp_path):
        """Test atomic save prevents corruption if process crashes"""
        config_file = tmp_path / "config.json"
        config = Config(str(config_file))

        # Modify and save
        config.set("location.name", "Test")

        # Verify file exists and is valid JSON
        assert config_file.exists()
        assert config.get("location.name") == "Test"

    def test_config_handles_disk_full_gracefully(self, tmp_path):
        """Test config save fails gracefully when disk is full"""
        # Test implementation...
        pass
```

### Bad Test Structure

```python
# DON'T DO THIS

def test1():  # Bad name
    c = Config()  # No cleanup
    c.set("foo", "bar")  # No assertion

def test2():  # Depends on test1
    c = Config()
    assert c.get("foo") == "bar"  # Will fail if test1 didn't run
```

---

## Questions?

- **"Should I write a test for X?"** → If it's core functionality or user-facing, yes
- **"Where does this test go?"** → Integration test in service directory
- **"What framework?"** → pytest (Python) or Playwright (TypeScript)
- **"How do I run it?"** → See "How to Run Tests" section above

---

## Summary

**One way to organize tests. One way to run them. No variations.**

1. Integration tests in `test_integration.py` per service
2. Run with `pytest` (Python) or `npm run test` (TypeScript)
3. Frontend tests MUST use Docker services
4. All tests clean up after themselves
5. Follow examples in this document

If you're about to do something different, re-read this document first.
