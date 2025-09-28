# Sprint 3 QA Assessment 2: External QA Playbook Correction

**Date**: 2025-09-28
**QA Engineer**: Jordan Martinez - Senior QA & Test Automation Specialist
**Scope**: Review and correction of `agent-comms/external-qa-sprint-3.md` to reflect the real environment and unblock testing.

---

## Findings

- **Incorrect URLs/ports in doc**: Frontend runs on `3000`, Processing API on `8081`, Realtime on `8082`.
  - Confirmed by `frontend/src/config/environment.ts` defaults and docker-compose files.
- **Wrong env var names in doc/compose**: Frontend uses `VITE_*` variables, not `REACT_APP_*`.
- **WebSocket URL scheme mismatch**: `frontend/docker-compose.yml` sets `VITE_WS_URL=http://realtime-backend:8082` but `environment.ts` expects a proper WS URL or falls back to building one. If `VITE_WS_URL` is explicitly set, it must be `ws://...` (or `wss://`).
- **Startup instructions fragmented**: The external QA doc mixes per-directory compose up without the right profiles/files.

---

## Source of Truth

- `frontend/src/config/environment.ts`
  - Default dev URLs: `API_URL=http://localhost:8081`, `WS_URL=ws://localhost:8082`, `CAPTURE_URL=http://helios.local:8080`.
- `frontend/docker-compose.yml`
  - Dev service: `frontend-dev` exposes `3000` and sets `VITE_*` envs.
- `processing/docker-compose.dev.yml`
  - Processing API exposes `8081`.
- `backend/docker-compose.yml`
  - Realtime backend exposes `8082`.

---

## Recommended Fixes

1. **Update external QA playbook** (`agent-comms/external-qa-sprint-3.md`):
   - Correct startup commands using explicit compose files:
     ```bash
     # Realtime backend
     docker compose -f backend/docker-compose.yml up -d realtime-backend

     # Processing API
     docker compose -f processing/docker-compose.dev.yml up -d processing

     # Frontend (dev)
     docker compose -f frontend/docker-compose.yml --profile dev up frontend-dev
     ```
   - Correct expected URLs:
     - Dashboard: `http://localhost:3000`
     - Processing API: `http://localhost:8081`
     - Realtime API (WS): `ws://localhost:8082`
   - Add a note to verify the logged config printed by `environment.ts` in the browser console.
   - Replace references to `REACT_APP_*` with `VITE_*`.

2. **Fix compose env mismatch** (`frontend/docker-compose.yml`):
   - Change dev `VITE_WS_URL` to a WS URL:
     - From: `http://realtime-backend:8082`
     - To:   `ws://realtime-backend:8082`

3. **Align production compose envs** (`docker-compose.production.yml`):
   - Current vars: `VITE_API_BASE_URL`, `VITE_SSE_URL`, `VITE_WS_URL`.
   - `environment.ts` reads `VITE_API_URL`, `VITE_WS_URL`, `VITE_CAPTURE_URL`.
   - Options:
     - A) Adjust `environment.ts` to support both names; or
     - B) Rename compose vars to match `environment.ts`.
   - Recommendation: **Option B** for simplicity/maintainability (align to existing code).

---

## Updated External QA Test Plan (Ready-To-Run)

- **Environment Setup**
  ```bash
  docker compose -f backend/docker-compose.yml up -d realtime-backend
  docker compose -f processing/docker-compose.dev.yml up -d processing
  docker compose -f frontend/docker-compose.yml --profile dev up frontend-dev
  ```
- **Env Verification**
  - Open browser console; verify logs from `environment.ts`:
    - API URL: `http://localhost:8081`
    - WebSocket URL: `ws://localhost:8082`
    - Capture URL: `http://helios.local:8080`
- **Smoke Tests**
  - Load `http://localhost:3000` without console errors.
  - Connection indicator shows real-time connected.
  - System status and environmental panels render with data (mock acceptable).
  - Network tab shows 200 responses from `http://localhost:8081`.

---

## Risk Analysis

- **Misconfigured WS URL** will result in immediate real-time failure and misleading test results.
- **Env var name drift** between code and compose will cause inconsistent deployments.

---

## Action Items

- **Apply doc corrections** to `agent-comms/external-qa-sprint-3.md`.
- **Patch `frontend/docker-compose.yml`** to use `ws://` for `VITE_WS_URL`.
- **Align production compose env names** to match `environment.ts`.

---

## Cross-References

- See `agent-comms/sprint-3-qa-1.md` for prior critical issue log and initial validation.

---

Prepared by Jordan Martinez (QA). Ready to apply patches upon approval.
