# URGENT: External QA Required - Sprint 3 Dashboard Failures

**Date**: 2025-09-28
**Priority**: CRITICAL
**Status**: INTERNAL TEAM FAILING - EXTERNAL QA NEEDED

## Situation Summary

The internal development team has delivered a **non-functional dashboard** for Sprint 3. Despite multiple attempts to fix critical issues, the dashboard at http://localhost:3000 remains broken. **External QA is required immediately** to validate fixes and document remaining issues.

## Test Environment Setup

```bash
# Start services in correct order
cd /Users/nicholasmparker/Projects/skylapse

# 1. Start realtime backend
docker compose -f backend/docker-compose.yml up -d realtime-backend

# 2. Start processing API
docker compose -f processing/docker-compose.dev.yml up -d processing

# 3. Start frontend (dev mode)
docker compose -f frontend/docker-compose.yml --profile dev up frontend-dev
```

**Expected URLs:**
- Dashboard: http://localhost:3000
- Processing API: http://localhost:8081
- Realtime API (WebSocket): ws://localhost:8082

**Environment Verification:**
Open browser console at http://localhost:3000 and verify these logs from environment.ts:
- 📡 API URL: http://localhost:8081
- 🔌 WebSocket URL: ws://localhost:8082
- 📷 Capture URL: http://helios.local:8080

## Critical Issues That SHOULD Be Fixed (But May Not Be)

### 1. Visual/UI Issues
- **White-on-white text**: Text should be visible, not invisible
- **Tailwind colors**: `mountain-*` and `golden-*` colors should render properly
- **Layout broken**: Dashboard should have proper spacing and alignment

### 2. Authentication Issues
- **Auto-login**: Should show authenticated state immediately (dev mode)
- **Connection status**: Should show "Real-time" not "disconnected"
- **User context**: Should display dev user information

### 3. WebSocket/Real-time Issues
- **Connection**: Should connect to ws://localhost:8082
- **Data updates**: System status should show live data
- **Error handling**: Should gracefully handle connection failures

### 4. API Integration Issues
- **CORS errors**: Should NOT see CORS policy blocking messages
- **Data loading**: Environmental data and gallery should load
- **Error responses**: Should handle API failures gracefully

## Specific Test Cases

### Test 1: Basic Dashboard Load
1. Navigate to http://localhost:3000
2. **EXPECTED**: Dashboard loads without JavaScript errors
3. **VERIFY**: Browser console shows no critical errors
4. **VERIFY**: Text is visible (not white-on-white)

### Test 2: Real-time Connection
1. Check connection status indicator
2. **EXPECTED**: Shows "Real-time" with green indicator
3. **VERIFY**: WebSocket connects to localhost:8082
4. **VERIFY**: No connection errors in console

### Test 3: Data Display
1. Check system status panel
2. **EXPECTED**: Shows CPU/Memory usage (even if mock data)
3. **VERIFY**: Numbers display properly (not "0%" everywhere)
4. **VERIFY**: Environmental data panel shows temperature, humidity, etc.

### Test 4: API Calls
1. Open browser Network tab
2. Refresh page
3. **EXPECTED**: API calls to localhost:8081 succeed (200 status)
4. **VERIFY**: No CORS errors in console
5. **VERIFY**: Data is returned in JSON format
6. **VERIFY**: Environment config logs show correct VITE_* variables

### Test 5: Error Boundary Testing
1. Check browser console for React errors
2. **EXPECTED**: No "Cannot read properties of undefined" errors
3. **VERIFY**: No component crashes
4. **VERIFY**: Error boundaries display if errors occur

## Known Issues Fixed (Should Work Now)

✅ **JavaScript hoisting errors** - Functions declared before use
✅ **TypeScript import issues** - Proper type imports added
✅ **CORS middleware** - Added to processing API server
✅ **Tailwind config** - Custom colors defined
✅ **Authentication bypass** - Development mode enabled
✅ **Environment variables** - VITE_* variables properly configured
✅ **WebSocket URL scheme** - Proper ws:// protocol for real-time connection

## Failure Documentation Required

Please document ANY of the following that still fail:

### Visual Failures
- [ ] White or invisible text
- [ ] Broken layout/spacing
- [ ] Missing colors/styling
- [ ] Responsive design issues

### Functional Failures
- [ ] JavaScript errors in console
- [ ] Failed API calls
- [ ] WebSocket connection failures
- [ ] Missing or broken data display

### Performance Issues
- [ ] Slow loading times
- [ ] Memory leaks
- [ ] High CPU usage
- [ ] Network timeouts

## Expected Deliverable

**Detailed bug report with:**
1. **Screenshots** of any visual issues
2. **Console logs** of any JavaScript errors
3. **Network tab** showing failed API calls
4. **Step-by-step reproduction** of any broken functionality
5. **Browser compatibility** testing (Chrome, Firefox, Safari)

## Escalation Path

**If dashboard is still non-functional**: Recommend immediate team replacement. This is basic functionality that should work on first delivery.

**Timeline**: Testing needed within 24 hours to determine Sprint 3 viability.

---

**Contact**: Project Owner for escalation decisions
**Budget**: Approved for external QA due to internal team failures
