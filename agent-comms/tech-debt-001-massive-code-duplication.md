# Tech Debt Issue #1: Massive Code Duplication in Error Handling

## ⚠️ Priority: CRITICAL
**Risk Level**: Maintenance Nightmare
**Effort**: 4 hours
**Impact**: Every error handling change requires updates in 3+ places

---

## Problem Description

Nearly identical error handling middleware is repeated across all services with minor variations. This creates a maintenance nightmare where any improvement to error handling must be implemented multiple times, leading to inconsistencies and bugs.

## Specific Locations

### **Primary Duplication Sites**
1. **File**: `capture/src/api_server.py:583-608`
2. **File**: `processing/src/api_server.py:266-291`
3. **File**: `backend/src/realtime_server.py:198-223`

### **Error Middleware Duplication**
```python
# DUPLICATED in capture/src/api_server.py:583-608
@web.middleware
async def _error_middleware(self, request, handler):
    try:
        return await handler(request)
    except Exception as e:
        logger.error(f"API error: {e}\n{traceback.format_exc()}")
        return json_response({
            "error": str(e),
            "type": type(e).__name__,
            "timestamp": datetime.now().isoformat(),
        }, status=500)

# DUPLICATED in processing/src/api_server.py:266-291
@web.middleware
async def error_middleware(request, handler):  # Different name!
    try:
        return await handler(request)
    except Exception as e:
        logger.error(f"Processing error: {e}\n{traceback.format_exc()}")  # Different message!
        return json_response({
            "error": str(e),
            "type": type(e).__name__,
            "timestamp": datetime.now().isoformat(),
            "service": "processing"  # Additional field!
        }, status=500)

# DUPLICATED in backend/src/realtime_server.py:198-223
async def handle_error(self, request, handler):  # Different signature!
    try:
        return await handler(request)
    except Exception as e:
        self.logger.error(f"Realtime error: {e}")  # Missing traceback!
        return web.json_response({
            "error": str(e),
            "type": type(e).__name__,
            "timestamp": datetime.now().isoformat(),
            # Missing status field!
        }, status=500)
```

### **JSON Response Helper Duplication**
```python
# capture/src/api_server.py:100-114
def json_response(data: Dict[str, Any], status: int = 200) -> web.Response:
    """Create JSON response."""
    return web.Response(
        text=json.dumps(data, indent=2),
        content_type='application/json',
        status=status
    )

# processing/src/api_server.py:88-102
def create_json_response(data: Dict[str, Any], status: int = 200) -> web.Response:  # Different name!
    """Create JSON response."""
    return web.Response(
        text=json.dumps(data, indent=None),  # Different formatting!
        content_type='application/json',
        status=status,
        headers={'Cache-Control': 'no-cache'}  # Additional header!
    )
```

### **Health Check Duplication**
```python
# Each service implements nearly identical health checks
# capture/src/api_server.py:450-465
# processing/src/api_server.py:380-395
# backend/src/realtime_server.py:145-160
```

## Root Cause Analysis

### **1. Copy-Paste Development**
- Initial service created error handling
- Subsequent services copied and modified slightly
- No refactoring to shared library

### **2. Missing Common Library**
- No shared utilities between services
- Each service exists in isolation
- No cross-service standards established

### **3. Inconsistent Naming**
- `_error_middleware` vs `error_middleware` vs `handle_error`
- `json_response` vs `create_json_response`
- Different parameter signatures

### **4. Feature Drift**
- Each copy evolved independently
- Processing service added `service` field
- Backend service removed traceback logging
- Different error message formats

## Impact Analysis

### **Maintenance Cost: HIGH**
- **Bug Fixes**: Must be applied in 3+ places
- **Security Updates**: Risk of missing one implementation
- **Feature Additions**: 3x development time
- **Testing**: Must test identical logic multiple times

### **Consistency Issues: HIGH**
- Different error message formats across services
- Inconsistent logging levels and formats
- Different response structures for clients
- Varying timeout and retry behaviors

### **Code Quality: LOW**
- ~200 lines of duplicated code
- 15+ similar functions across services
- No single source of truth for error handling
- Violation of DRY principle

## Proposed Solution

### **Phase 1: Create Shared Common Library**

```python
# common/middleware.py - NEW SHARED MODULE
import json
import logging
import traceback
from datetime import datetime
from typing import Any, Dict, Optional
from aiohttp import web

logger = logging.getLogger(__name__)

class SkylaspseErrorHandler:
    """Shared error handling for all Skylapse services."""

    def __init__(self, service_name: str, include_traceback: bool = True):
        self.service_name = service_name
        self.include_traceback = include_traceback

    @web.middleware
    async def error_middleware(self, request: web.Request, handler):
        """Standard error handling middleware."""
        try:
            return await handler(request)
        except web.HTTPException:
            # Let HTTP exceptions pass through
            raise
        except Exception as e:
            return await self._handle_error(e, request)

    async def _handle_error(self, error: Exception, request: web.Request) -> web.Response:
        """Handle unexpected errors with consistent formatting."""
        error_id = self._generate_error_id()

        # Log error with context
        log_message = f"API error in {self.service_name}: {error}"
        if self.include_traceback:
            log_message += f"\n{traceback.format_exc()}"

        logger.error(log_message, extra={
            'error_id': error_id,
            'service': self.service_name,
            'endpoint': str(request.url),
            'method': request.method
        })

        # Create consistent error response
        error_response = {
            "error": str(error),
            "error_type": type(error).__name__,
            "error_id": error_id,
            "service": self.service_name,
            "timestamp": datetime.now().isoformat(),
        }

        return self.json_response(error_response, status=500)

    def json_response(self, data: Dict[str, Any], status: int = 200) -> web.Response:
        """Create standardized JSON response."""
        return web.Response(
            text=json.dumps(data, indent=2, default=str),
            content_type='application/json',
            status=status,
            headers={
                'Cache-Control': 'no-cache',
                'X-Service': self.service_name
            }
        )

    @staticmethod
    def _generate_error_id() -> str:
        """Generate unique error ID for tracking."""
        import uuid
        return str(uuid.uuid4())[:8]

# common/health.py - SHARED HEALTH CHECKS
class HealthChecker:
    """Shared health check functionality."""

    def __init__(self, service_name: str):
        self.service_name = service_name
        self.start_time = datetime.now()

    async def health_check(self) -> Dict[str, Any]:
        """Standard health check response."""
        uptime = datetime.now() - self.start_time

        return {
            "status": "healthy",
            "service": self.service_name,
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": int(uptime.total_seconds()),
            "version": self._get_version()
        }

    def _get_version(self) -> str:
        """Get service version from environment or default."""
        import os
        return os.getenv(f'{self.service_name.upper()}_VERSION', '1.0.0')
```

### **Phase 2: Update Each Service**

```python
# capture/src/api_server.py - UPDATED TO USE SHARED
from common.middleware import SkylaspseErrorHandler
from common.health import HealthChecker

class CaptureAPIServer:
    def __init__(self):
        self.error_handler = SkylaspseErrorHandler('capture', include_traceback=True)
        self.health_checker = HealthChecker('capture')

        # Use shared middleware
        self.app.middlewares.append(self.error_handler.error_middleware)

    async def health(self, request: web.Request) -> web.Response:
        """Health check endpoint."""
        health_data = await self.health_checker.health_check()
        return self.error_handler.json_response(health_data)

    # Remove all duplicated error handling and JSON response methods
```

### **Phase 3: Standardize Across All Services**

Apply the same pattern to:
- `processing/src/api_server.py`
- `backend/src/realtime_server.py`

## Implementation Steps

### **Step 1: Create Common Module (1 hour)**
1. Create `common/` directory in project root
2. Implement `SkylaspseErrorHandler` class
3. Implement `HealthChecker` class
4. Add comprehensive tests

### **Step 2: Update Capture Service (1 hour)**
1. Add common module import
2. Replace error middleware with shared version
3. Remove duplicated functions
4. Test error handling still works

### **Step 3: Update Processing Service (1 hour)**
1. Same pattern as capture service
2. Ensure service-specific features are preserved
3. Update any service-specific error handling

### **Step 4: Update Backend Service (1 hour)**
1. Same pattern as other services
2. Handle any WebSocket-specific error cases
3. Comprehensive integration testing

## Dependencies

**Must Complete First**:
- None - this is foundational infrastructure

**Enables These Issues**:
- Issue #2 (CORS Duplication) - Can use same shared middleware pattern
- Issue #8 (JSON Response Duplication) - Solved by this refactoring
- Issue #14 (Health Check Duplication) - Directly addressed

## Testing Strategy

### **Unit Tests for Shared Components**
```python
# tests/common/test_error_handler.py
@pytest.mark.asyncio
async def test_error_handler_captures_exceptions():
    """Test that error handler captures and formats exceptions properly."""
    handler = SkylaspseErrorHandler('test-service')

    async def failing_handler(request):
        raise ValueError("Test error")

    request = create_mock_request()
    response = await handler.error_middleware(request, failing_handler)

    assert response.status == 500
    data = json.loads(response.text)
    assert data['error'] == 'Test error'
    assert data['service'] == 'test-service'
    assert 'error_id' in data

@pytest.mark.asyncio
async def test_error_handler_preserves_http_exceptions():
    """Test that HTTP exceptions pass through unchanged."""
    handler = SkylaspseErrorHandler('test-service')

    async def http_error_handler(request):
        raise web.HTTPNotFound()

    request = create_mock_request()

    with pytest.raises(web.HTTPNotFound):
        await handler.error_middleware(request, http_error_handler)
```

### **Integration Tests**
```python
# tests/integration/test_error_consistency.py
async def test_all_services_have_consistent_error_format():
    """Test that all services return errors in the same format."""
    services = ['capture', 'processing', 'backend']

    for service in services:
        # Trigger error in each service
        response = await trigger_error_in_service(service)

        # Verify consistent error format
        assert response.status == 500
        data = response.json()
        assert 'error' in data
        assert 'error_type' in data
        assert 'error_id' in data
        assert 'service' in data
        assert 'timestamp' in data
```

## Risk Assessment

### **Implementation Risk: LOW**
- **Minimal Breaking Changes**: Only changing implementation, not interface
- **Gradual Migration**: Can update one service at a time
- **Backward Compatible**: Error response format can remain the same

### **Rollback Plan**
1. Keep original error handling methods as `_legacy_error_handler`
2. Add feature flag to switch between old and new error handling
3. Can revert individual services if needed

```python
# Rollback strategy
class CaptureAPIServer:
    def __init__(self):
        self.use_shared_error_handler = os.getenv('USE_SHARED_ERROR_HANDLER', 'true').lower() == 'true'

        if self.use_shared_error_handler:
            self.error_handler = SkylaspseErrorHandler('capture')
            self.app.middlewares.append(self.error_handler.error_middleware)
        else:
            self.app.middlewares.append(self._legacy_error_middleware)
```

## Expected Results

### **Code Reduction**
- **Remove ~200 lines** of duplicated code
- **Consolidate to ~100 lines** in shared module
- **50% reduction** in error handling code

### **Maintenance Improvement**
- **Single location** for error handling updates
- **Consistent behavior** across all services
- **Easier testing** with shared test utilities

### **Feature Consistency**
- **Uniform error formats** for frontend consumption
- **Consistent logging** for debugging and monitoring
- **Standardized health checks** for monitoring systems

---

## Related Issues

- **Issue #2**: CORS Middleware Duplication - Same pattern applies
- **Issue #8**: JSON Response Helper Duplication - Directly solved
- **Issue #14**: Health Check Duplication - Directly addressed
- **Issue #18**: Logging Configuration - Can standardize in shared module

---

*This refactoring establishes the foundation for shared utilities across all Skylapse services and eliminates the largest source of code duplication in the system.*
