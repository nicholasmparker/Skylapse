# Tech Debt Issue #2: Duplicated CORS Middleware Implementation

## ⚠️ Priority: CRITICAL
**Risk Level**: Security Vulnerability
**Effort**: 2 hours
**Impact**: Security inconsistencies, maintenance burden

---

## Problem Description

CORS (Cross-Origin Resource Sharing) logic is duplicated across multiple services with slight variations, creating security inconsistencies and maintenance overhead. Different implementations may have different security policies, creating potential vulnerabilities.

## Specific Locations

### **Primary Duplication Sites**
- **File**: `capture/src/api_server.py:583-608`
- **File**: `backend/src/realtime_server.py:266-277`

### **CORS Implementation Variations**

```python
# capture/src/api_server.py:583-608 - CORS Implementation #1
@web.middleware
async def _cors_middleware(self, request, handler):
    """CORS middleware for capture service."""
    response = await handler(request)

    # Permissive CORS - SECURITY ISSUE
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    response.headers['Access-Control-Max-Age'] = '86400'

    return response

# Handle preflight requests
async def _handle_cors_preflight(self, request):
    """Handle CORS preflight requests."""
    return web.Response(
        headers={
            'Access-Control-Allow-Origin': '*',  # TOO PERMISSIVE
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            'Access-Control-Max-Age': '86400'
        }
    )

# backend/src/realtime_server.py:266-277 - CORS Implementation #2
def _setup_cors(self, app):
    """Setup CORS for realtime server."""

    @web.middleware
    async def cors_middleware(request, handler):  # Different signature!
        if request.method == 'OPTIONS':
            # Different preflight handling
            return web.Response(
                headers={
                    'Access-Control-Allow-Origin': '*',  # SAME VULNERABILITY
                    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',  # Missing PUT, DELETE
                    'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With',  # Different headers
                    'Access-Control-Max-Age': '3600'  # Different cache time
                }
            )

        response = await handler(request)
        response.headers.update({
            'Access-Control-Allow-Origin': '*',  # SECURITY ISSUE
            'Access-Control-Allow-Credentials': 'true'  # DANGEROUS with wildcard origin
        })
        return response

    app.middlewares.append(cors_middleware)
```

## Root Cause Analysis

### **1. Copy-Paste Security Policy**
- Initial CORS setup copied between services
- No security review of CORS policies
- Permissive settings for development carried to production

### **2. Inconsistent Security Requirements**
- Different services have different allowed methods
- Inconsistent header allowances
- Different cache timeout policies

### **3. Critical Security Issues**
- **Wildcard Origins**: `Access-Control-Allow-Origin: *` on all services
- **Credentials + Wildcard**: Dangerous combination in backend service
- **Overly Permissive**: All methods allowed without justification

## Security Implications

### **CRITICAL VULNERABILITIES**:

#### **1. Cross-Site Request Forgery (CSRF)**
```javascript
// Malicious site can make requests to your API
fetch('http://helios.local:8080/api/settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        rotation_degrees: 0,  // Attacker changes camera settings
        // ... other malicious settings
    })
})
```

#### **2. Data Exfiltration**
```javascript
// Malicious site can read sensitive data
fetch('http://helios.local:8080/api/status')
    .then(r => r.json())
    .then(data => {
        // Attacker extracts camera system information
        sendToAttacker(data.camera_status)
    })
```

#### **3. Credential Exposure**
- Backend service allows credentials with wildcard origin
- Cookies and authorization headers can be stolen

## Proposed Solution

### **Shared CORS Configuration**

```python
# common/cors.py - NEW SHARED CORS MODULE
from typing import List, Optional
from aiohttp import web
import os

class SecureCORSHandler:
    """Secure CORS handling for all Skylapse services."""

    def __init__(self, service_name: str):
        self.service_name = service_name
        self.allowed_origins = self._get_allowed_origins()
        self.allowed_methods = self._get_allowed_methods()
        self.allowed_headers = self._get_allowed_headers()

    def _get_allowed_origins(self) -> List[str]:
        """Get allowed origins from environment with secure defaults."""
        origins_env = os.getenv(f'SKYLAPSE_{self.service_name.upper()}_CORS_ORIGINS',
                               'http://localhost:3000,http://localhost:5173')  # Dev defaults

        origins = [origin.strip() for origin in origins_env.split(',')]

        # Security validation
        for origin in origins:
            if origin == '*':
                if os.getenv('SKYLAPSE_ENVIRONMENT', 'production') == 'production':
                    raise ValueError(f"Wildcard CORS origins not allowed in production for {self.service_name}")

        return origins

    def _get_allowed_methods(self) -> List[str]:
        """Get allowed methods based on service type."""
        method_map = {
            'capture': ['GET', 'POST', 'PUT'],  # No DELETE for camera service
            'processing': ['GET', 'POST'],      # Read-only + job submission
            'backend': ['GET', 'POST', 'OPTIONS']  # Realtime communication
        }
        return method_map.get(self.service_name, ['GET', 'POST'])

    def _get_allowed_headers(self) -> List[str]:
        """Get standard allowed headers."""
        return [
            'Content-Type',
            'Authorization',
            'X-Requested-With',
            'Accept',
            'Origin'
        ]

    @web.middleware
    async def cors_middleware(self, request: web.Request, handler):
        """Secure CORS middleware."""
        origin = request.headers.get('Origin')

        # Handle preflight requests
        if request.method == 'OPTIONS':
            return self._handle_preflight(origin)

        # Process actual request
        response = await handler(request)

        # Add CORS headers to response
        if origin and self._is_origin_allowed(origin):
            response.headers['Access-Control-Allow-Origin'] = origin  # SECURE: Specific origin
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            response.headers['Vary'] = 'Origin'  # Important for caching

        return response

    def _handle_preflight(self, origin: Optional[str]) -> web.Response:
        """Handle CORS preflight requests securely."""
        if not origin or not self._is_origin_allowed(origin):
            return web.Response(status=403, text="CORS preflight rejected")

        return web.Response(
            headers={
                'Access-Control-Allow-Origin': origin,  # SECURE: Specific origin
                'Access-Control-Allow-Methods': ', '.join(self.allowed_methods),
                'Access-Control-Allow-Headers': ', '.join(self.allowed_headers),
                'Access-Control-Max-Age': '3600',  # 1 hour cache
                'Access-Control-Allow-Credentials': 'true',
                'Vary': 'Origin'
            }
        )

    def _is_origin_allowed(self, origin: str) -> bool:
        """Check if origin is in allowed list."""
        return origin in self.allowed_origins
```

### **Environment Configuration**

```bash
# .env.production
SKYLAPSE_CAPTURE_CORS_ORIGINS=https://your-domain.com,https://app.your-domain.com
SKYLAPSE_PROCESSING_CORS_ORIGINS=https://your-domain.com
SKYLAPSE_BACKEND_CORS_ORIGINS=https://your-domain.com

# .env.development
SKYLAPSE_CAPTURE_CORS_ORIGINS=http://localhost:3000,http://localhost:5173
SKYLAPSE_PROCESSING_CORS_ORIGINS=http://localhost:3000
SKYLAPSE_BACKEND_CORS_ORIGINS=http://localhost:3000

# .env.test
SKYLAPSE_CAPTURE_CORS_ORIGINS=http://localhost:3001
```

### **Service Integration**

```python
# capture/src/api_server.py - SECURE VERSION
from common.cors import SecureCORSHandler

class CaptureAPIServer:
    def __init__(self):
        self.cors_handler = SecureCORSHandler('capture')

        # Use secure CORS middleware
        self.app.middlewares.append(self.cors_handler.cors_middleware)

        # Remove all old CORS middleware code
```

## Implementation Steps

### **Step 1: Create Secure CORS Module (45 minutes)**
1. Create `common/cors.py` with `SecureCORSHandler`
2. Add environment variable validation
3. Add comprehensive security checks

### **Step 2: Update Capture Service (30 minutes)**
1. Replace existing CORS middleware
2. Configure allowed origins for camera service
3. Test CORS with allowed and blocked origins

### **Step 3: Update Backend Service (30 minutes)**
1. Replace existing CORS implementation
2. Remove dangerous credentials + wildcard combination
3. Test WebSocket CORS functionality

### **Step 4: Security Testing (15 minutes)**
1. Verify malicious origins are blocked
2. Test preflight request handling
3. Confirm credentials work with allowed origins

## Testing Strategy

### **Security Tests**

```python
# tests/security/test_cors_security.py
async def test_cors_blocks_unauthorized_origins():
    """Test that unauthorized origins are blocked."""
    cors_handler = SecureCORSHandler('capture')

    # Mock request from malicious origin
    request = create_mock_request(
        headers={'Origin': 'https://malicious-site.com'}
    )

    response = await cors_handler._handle_preflight('https://malicious-site.com')
    assert response.status == 403

async def test_cors_allows_authorized_origins():
    """Test that authorized origins are allowed."""
    cors_handler = SecureCORSHandler('capture')

    request = create_mock_request(
        headers={'Origin': 'http://localhost:3000'}
    )

    response = await cors_handler._handle_preflight('http://localhost:3000')
    assert response.status == 200
    assert 'Access-Control-Allow-Origin' in response.headers

async def test_no_wildcard_in_production():
    """Test that wildcard origins are rejected in production."""
    with patch.dict(os.environ, {
        'SKYLAPSE_ENVIRONMENT': 'production',
        'SKYLAPSE_CAPTURE_CORS_ORIGINS': '*'
    }):
        with pytest.raises(ValueError, match="Wildcard CORS origins not allowed in production"):
            SecureCORSHandler('capture')
```

## Dependencies

**Must Complete First**:
- Issue #3 (Configuration Management) - For environment variable handling

**Enables These Issues**:
- Issue #1 (Error Handling) - Can use same middleware pattern
- Issue #42 (Environment Variables) - CORS uses same env patterns

## Risk Assessment

### **Implementation Risk: LOW**
- **Non-Breaking**: Frontend will continue to work with proper origins
- **Environment-Based**: Can configure per environment
- **Gradual Migration**: Can update one service at a time

### **Security Risk: ELIMINATED**
- **No More Wildcard Origins**: Only specific domains allowed
- **Proper Credential Handling**: Safe credential + origin combination
- **Method Restrictions**: Only necessary HTTP methods allowed

---

## Related Issues

- **Issue #1**: Error Handling - Same shared middleware pattern
- **Issue #3**: Configuration Management - Environment variables for origins
- **Issue #42**: Environment Variable Validation - CORS config validation

---

*This fix eliminates critical CORS security vulnerabilities while establishing a secure, maintainable CORS configuration system.*
