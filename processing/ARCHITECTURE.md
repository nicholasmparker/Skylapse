# Processing Service Architecture

## CRITICAL: API Server Policy

**THERE SHALL BE ONLY ONE API SERVER IMPLEMENTATION**

### Current Architecture
- **Single API Server**: `src/api_server.py` (ProcessingAPIServer class)
- **Single Service Entry**: `src/processing_service.py`
- **Docker Entry Point**: `python -m src.processing_service`

### BANNED PATTERNS

❌ **NEVER create duplicate API servers**
❌ **NEVER create "simple" or "lite" versions**
❌ **NEVER create multiple service entry points**

### Required API Endpoints

The ProcessingAPIServer MUST provide these endpoints:

```
GET  /api/gallery/sequences       - List timelapse sequences
GET  /api/gallery/sequences/{id}  - Get sequence details
DELETE /api/gallery/sequences/{id} - Delete sequence
POST /api/gallery/generate        - Generate timelapse
GET  /api/gallery/jobs            - Get generation jobs
GET  /api/analytics               - System analytics
```

### Code Review Checklist

Before merging ANY changes to the processing service:

- [ ] Only ONE API server class exists
- [ ] Only ONE processing service entry point exists
- [ ] All required gallery endpoints are present
- [ ] Docker uses the correct entry point
- [ ] No "simple", "lite", or "minimal" variants exist

### Historical Context

In Sprint 3, a catastrophic duplication occurred:
- Someone created `SimpleProcessingAPIServer` alongside `ProcessingAPIServer`
- This caused 405 Method Not Allowed errors for gallery endpoints
- The simple server was missing critical API contracts
- This violated DRY principles and caused production failures

**NEVER AGAIN.**

## Emergency Contact

If you're considering creating a "simplified" API server, **STOP** and:
1. Extend the existing ProcessingAPIServer instead
2. Use feature flags for optional functionality
3. Discuss architectural changes in design review

This document serves as a permanent architectural safeguard.