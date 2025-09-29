# Task 5 Remediation Script: Remove Legacy Middleware from Capture Service

This document provides the exact code changes needed to fix the middleware consistency issues identified in the QA assessment.

## File: `/capture/src/api_server.py`

### 1. Remove Legacy Error Middleware (Lines 258-271)

**REMOVE THIS BLOCK:**
```python
@web.middleware
async def _error_middleware(self, request, handler):
    """Error handling middleware."""
    try:
        return await handler(request)
    except Exception as e:
        logger.error(f"API error: {e}\n{traceback.format_exc()}")
        return json_response(
            {
                "error": str(e),
                "type": type(e).__name__,
                "timestamp": datetime.now().isoformat(),
            },
            status=500,
        )
```

### 2. Remove Legacy CORS Middleware (Lines 600-624)

**REMOVE THIS BLOCK:**
```python
@web.middleware
async def _cors_middleware(self, request, handler):
    """CORS middleware to allow cross-origin requests from frontend."""
    try:
        # Handle preflight OPTIONS requests
        if request.method == "OPTIONS":
            response = web.Response()
        else:
            response = await handler(request)

        # Add CORS headers
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = (
            "Content-Type, Authorization, X-Requested-With"
        )
        response.headers["Access-Control-Max-Age"] = "86400"  # 24 hours

        return response

    except Exception as e:
        logger.error(f"CORS middleware error: {e}")
        # Even on error, return response with CORS headers
        error_response = web.Response(status=500, text=str(e))
        error_response.headers["Access-Control-Allow-Origin"] = "*"
        return error_response
```

### 3. Remove Manual Error Handling in Route Handlers

**In `_manual_capture` method (around lines 397-400), REMOVE:**
```python
except json.JSONDecodeError:
    return json_response({"error": "Invalid JSON in request body"}, status=400)
except Exception as e:
    return json_response({"error": str(e)}, status=500)
```

**In `_test_capture` method (around lines 410-411), REMOVE:**
```python
except Exception as e:
    return json_response({"error": str(e)}, status=500)
```

**In `_run_baseline` method (around lines 428-431), REMOVE:**
```python
except json.JSONDecodeError:
    return json_response({"error": "Invalid JSON in request body"}, status=400)
except Exception as e:
    return json_response({"error": str(e)}, status=500)
```

**Continue this pattern for ALL route handlers that have manual error handling.**

### 4. Remove Duplicate json_response Function

**REMOVE the local json_response function (lines 116-130):**
```python
def json_response(data: Any, status: int = 200, **kwargs) -> web.Response:
    """Create JSON response using Skylapse JSON encoder."""
    if web is None:
        raise RuntimeError("aiohttp not available")

    # Convert data to JSON-serializable format
    serializable_data = to_dict(data)

    # Create JSON response
    return web.json_response(
        serializable_data,
        status=status,
        dumps=lambda obj: json.dumps(obj, cls=SkylapsJSONEncoder),
        **kwargs,
    )
```

**USE the shared json_response from middleware.error_handler instead.**

## Verification Commands

After making these changes, run these commands to verify the fixes:

```bash
# 1. Test error response consistency
curl -s -i "http://helios.local:8080/nonexistent-endpoint" | grep -A 10 "HTTP"

# 2. Test JSON error handling
curl -s -i -X POST "http://helios.local:8080/capture/manual" \
  -H "Content-Type: application/json" -d "invalid-json" | grep -A 20 "HTTP"

# 3. Test security headers
curl -s -i "http://helios.local:8080/health" | grep -E "X-(Content-Type-Options|Frame-Options|XSS-Protection)"

# 4. Run Playwright tests
cd frontend && npx playwright test shared-middleware-validation.spec.ts
```

## Expected Results After Fix

### Error Response Format
```json
{
  "error": {
    "code": "NOT_FOUND_ERROR",
    "message": "Resource not found",
    "details": {},
    "timestamp": "2025-09-29T16:21:50.329964",
    "service": "capture"
  }
}
```

### Security Headers
```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
```

### HTTP Status Codes
- 404 for nonexistent endpoints (not 500)
- 400 for invalid JSON (not 500)
- Consistent across all services

## Testing Checklist

After implementing fixes:

- [ ] All Playwright tests pass (10/10)
- [ ] Error responses use standardized format
- [ ] Security headers present on all responses
- [ ] CORS headers consistent across services
- [ ] No duplicate middleware code remains
- [ ] HTTP status codes are appropriate and consistent

## Risk Mitigation

To ensure these changes don't break existing functionality:

1. **Test all capture service endpoints** after changes
2. **Verify camera operations still work**
3. **Check frontend integration remains functional**
4. **Monitor logs for any new errors**

## Notes

- The shared middleware (`common/middleware/`) is correctly implemented
- The issue is only in the capture service's incomplete migration
- Other services (processing, backend) are correctly using shared middleware
- This fix will achieve 100% middleware consistency across all services
