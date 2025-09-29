# Tech Debt Issue #5: JWT Secret Hardcoded

## 🚨 Priority: CRITICAL
**Risk Level**: Security Vulnerability
**Effort**: 1 hour
**Impact**: Production security breach possible

---

## Problem Description

A hardcoded JWT secret is embedded directly in the source code, creating a critical security vulnerability. This secret is used for authentication token signing and verification across the system.

## Specific Locations

### Primary Issue Location
- **File**: `backend/src/realtime_server.py`
- **Line**: 23
- **Code Block**:
```python
JWT_SECRET = "skylapse_jwt_secret_change_in_production"
```

### Additional Instances
- **File**: `backend/src/realtime_server.py:45`
- **Usage**: `jwt.encode(payload, JWT_SECRET, algorithm="HS256")`
- **File**: `backend/src/realtime_server.py:67`
- **Usage**: `jwt.decode(token, JWT_SECRET, algorithms=["HS256"])`

## Current Problematic Patterns

```python
# backend/src/realtime_server.py:23 - CRITICAL SECURITY ISSUE
JWT_SECRET = "skylapse_jwt_secret_change_in_production"

class RealTimeServer:
    def __init__(self):
        self.jwt_secret = JWT_SECRET  # Using hardcoded secret

    async def authenticate_user(self, token: str):
        try:
            # PROBLEM: Secret is in source control
            payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            return payload
        except jwt.InvalidTokenError:
            return None
```

## Root Cause Analysis

1. **Development Convenience**: Secret was hardcoded for rapid development
2. **Missing Environment Setup**: No environment variable configuration
3. **Production Oversight**: Comment indicates awareness but no action taken
4. **Security Process Gap**: No security review catching this issue

## Security Implications

### **CRITICAL RISKS**:
1. **Token Forgery**: Anyone with source code access can forge valid JWT tokens
2. **Source Control Exposure**: Secret is permanently in git history
3. **Production Compromise**: Same secret used across all environments
4. **Privilege Escalation**: Attackers could gain admin access to camera system

### **Attack Vectors**:
- Public GitHub repository exposure
- Developer machine compromise
- Docker image inspection
- Log file analysis

## Proposed Solution

### **Immediate Fix (1 hour)**:

```python
# backend/src/realtime_server.py - SECURE VERSION
import os
from typing import Optional

def get_jwt_secret() -> str:
    """Get JWT secret from environment variables with validation."""
    secret = os.getenv('SKYLAPSE_JWT_SECRET')
    if not secret:
        raise ValueError(
            "SKYLAPSE_JWT_SECRET environment variable is required. "
            "Generate a secure secret: openssl rand -hex 32"
        )
    if len(secret) < 32:
        raise ValueError(
            "JWT secret must be at least 32 characters long for security"
        )
    return secret

class RealTimeServer:
    def __init__(self):
        self.jwt_secret = get_jwt_secret()

    async def authenticate_user(self, token: str) -> Optional[dict]:
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
            return payload
        except jwt.InvalidTokenError:
            return None
```

### **Environment Configuration**:

```bash
# .env.production
SKYLAPSE_JWT_SECRET=your_super_secure_secret_here_at_least_32_chars_long

# .env.development
SKYLAPSE_JWT_SECRET=dev_secret_for_local_development_only_32_chars

# .env.test
SKYLAPSE_JWT_SECRET=test_secret_for_automated_testing_32_chars
```

### **Docker Configuration**:

```yaml
# docker-compose.production.yml
services:
  backend:
    environment:
      - SKYLAPSE_JWT_SECRET=${SKYLAPSE_JWT_SECRET}
    # Secret should be passed via environment, not embedded
```

## Implementation Steps

### **Phase 1: Immediate Security Fix (30 minutes)**
1. Create `get_jwt_secret()` function with validation
2. Replace hardcoded secret with environment variable call
3. Test locally with environment variable set

### **Phase 2: Environment Setup (20 minutes)**
1. Add environment variable to all deployment configurations
2. Generate secure production secret: `openssl rand -hex 32`
3. Update Docker compose files to use environment variable

### **Phase 3: Verification (10 minutes)**
1. Verify JWT authentication still works
2. Test with invalid/missing environment variable
3. Confirm error messages are helpful for developers

## Dependencies

**Must Complete Before**:
- None - this is blocking critical security

**Can Be Done In Parallel**:
- Issue #3 (Configuration Management) - will improve this further
- Issue #42 (Environment Variable Validation) - adds schema validation

## Testing Strategy

### **Security Testing**:
```python
# tests/test_jwt_security.py
def test_jwt_secret_from_environment():
    """Test JWT secret is loaded from environment variable."""
    with patch.dict(os.environ, {'SKYLAPSE_JWT_SECRET': 'test_secret_32_characters_long_here'}):
        server = RealTimeServer()
        assert server.jwt_secret == 'test_secret_32_characters_long_here'

def test_jwt_secret_missing_raises_error():
    """Test that missing JWT secret raises clear error."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="SKYLAPSE_JWT_SECRET environment variable is required"):
            RealTimeServer()

def test_jwt_secret_too_short_raises_error():
    """Test that short JWT secret raises security error."""
    with patch.dict(os.environ, {'SKYLAPSE_JWT_SECRET': 'short'}):
        with pytest.raises(ValueError, match="JWT secret must be at least 32 characters"):
            RealTimeServer()
```

### **Integration Testing**:
- Test JWT token generation and validation with environment secret
- Verify authentication flow works end-to-end
- Test error handling when secret is invalid

## Risk Assessment

### **Fix Risks: LOW**
- **Minimal Code Changes**: Only changing secret source, not logic
- **Backward Compatible**: JWT functionality remains identical
- **Environment Only**: All changes are in configuration, not algorithms

### **Rollback Plan**
```python
# Emergency rollback if needed (DO NOT USE IN PRODUCTION)
def get_jwt_secret() -> str:
    secret = os.getenv('SKYLAPSE_JWT_SECRET')
    if not secret:
        # TEMPORARY FALLBACK - REMOVE IMMEDIATELY
        logger.critical("Using hardcoded JWT secret - SECURITY RISK!")
        return "skylapse_jwt_secret_change_in_production"
    return secret
```

### **Monitoring**
- Add logging when JWT secret is loaded from environment
- Monitor authentication failures after deployment
- Alert on any JWT-related errors

## Long-term Improvements

### **Future Enhancements** (Post-Fix):
1. **Secret Rotation**: Implement JWT secret rotation mechanism
2. **Key Management**: Use AWS Secrets Manager or HashiCorp Vault
3. **Multi-Key Support**: Support multiple valid keys for zero-downtime rotation
4. **Audit Logging**: Log all JWT operations for security monitoring

### **Security Hardening**:
1. **Token Expiry**: Ensure reasonable JWT expiration times
2. **Scope Limitation**: Implement granular permissions in JWT claims
3. **Rate Limiting**: Add rate limiting for authentication endpoints
4. **Intrusion Detection**: Monitor for suspicious JWT usage patterns

---

## Related Issues

- **Issue #3**: Configuration Management - Will provide unified config framework
- **Issue #42**: Environment Variable Validation - Adds schema validation
- **Issue #39**: Input Validation - Improves overall API security

---

## 🧪 **MANDATORY: Playwright Testing After Implementation**

**CRITICAL REQUIREMENT**: After completing this fix, you MUST use Playwright to verify the implementation is working correctly before marking as complete.

### **Required Playwright Tests**:
```javascript
// Test JWT authentication flow
test('JWT authentication works with environment secret', async ({ page }) => {
    // Navigate to dashboard
    await page.goto('http://localhost:3000/dashboard')

    // Should show authentication or connect successfully
    await expect(page.locator('[data-testid="connection-status"]')).toContainText('Connected')

    // Check real-time server health
    const response = await page.request.get('http://helios.local:8082/health')
    expect(response.ok()).toBeTruthy()
})

test('JWT secret validation prevents startup with invalid secret', async ({ page }) => {
    // This would be tested in deployment environment
    // Verify service fails to start with short/missing JWT secret
})
```

### **Verification Checklist**:
- [ ] Backend service starts successfully with proper JWT_SECRET environment variable
- [ ] Dashboard connects to real-time server without authentication errors
- [ ] JWT token generation works via `/auth/token` endpoint
- [ ] Real-time WebSocket connections authenticate successfully
- [ ] No JWT secret values appear in logs or error messages

**DO NOT MARK THIS ISSUE COMPLETE** until all Playwright tests pass and manual verification is confirmed.

---

*This issue represents a **critical security vulnerability** that should be fixed immediately before any production deployment.*
