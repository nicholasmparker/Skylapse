# Archived Documentation

This directory contains historical documentation from earlier phases of the Skylapse project. These docs are preserved for reference but do not reflect the current system implementation (as of October 2025).

## Current Documentation

For up-to-date documentation, see the project root:

- `README.md` - Project overview and quick start
- `ARCHITECTURE.md` - Current system architecture
- `DEPLOYMENT_AND_DOCKER.md` - Development and deployment workflows
- `HARDWARE.md` - Raspberry Pi and camera setup

## Archive Organization

### Design Documents (`/docs/archive/`)

Historical design proposals and architecture explorations:

- `SIMPLE_ARCHITECTURE.md` - Original v2 design (pre-database, pre-worker)
- `LESSONS_LEARNED.md` - Why we rewrote from v1
- `EXPOSURE_STRATEGY.md` - Original exposure research
- `EXPOSURE_TESTING_PLAN.md` - Early testing methodology
- `TIMELAPSE_AB_TESTING_PLAN.md` - Original profile testing approach
- `CENTRALIZED_CONFIG_DESIGN.md` - Future feature proposal
- `SPRINT_DEMOS.md` - Demo planning docs

### Sprint Reports (`/docs/archive/sprint-reports/`)

Point-in-time status reports and QA summaries:

- `CRITICAL_FIXES_COMPLETE.md` - Sprint 1 Week 1 status
- `TECH_DEBT_FIXES.md` - Sprint 1 checklist
- `QA_SUMMARY.md` - Sprint 1 QA report
- `QA_VALIDATION_REPORT.md` - Sprint 4 validation

### Agent Communications (`/docs/archive/agent-comms/`)

Communication between AI agents during early development:

- Sprint 1 planning and tech debt analysis
- Historical context for AI-assisted development

### Test Data (`/docs/archive/test-captures/`)

Baseline test results and checklists from Sept 30, 2025:

- Baseline test captures (JSON metadata)
- Review checklists

## What Changed Since These Docs?

**Major additions to current system:**

- SQLite database for session and capture metadata tracking
- Redis Queue (RQ) for background timelapse generation
- Worker service executing timelapse jobs
- Automated image download from Pi during captures
- Schedule-end detection triggering automatic timelapse generation
- 3 production profiles (A, D, G) out of 6 total profiles
- Docker volume persistence for database

**Deprecated concepts:**

- Processing service (replaced by RQ worker)
- Profile deployment mode (deferred to future)
- Multi-camera coordination (deferred to future)

## When to Reference Archived Docs

These docs are useful when:

- Understanding the evolution of design decisions
- Reviewing why certain approaches were chosen
- Looking up historical test results
- Researching features that were considered but not implemented

For all current implementation details, consult the main documentation in the project root.

---

**Last Updated:** October 1, 2025
