# Skylapse System Architecture

## Overview

Skylapse captures professional-quality mountain timelapses through a two-service architecture that separates hardware-optimized capture from compute-intensive processing.

### Core Design Decision

**Native Pi Capture + Docker Processing** provides the optimal balance of performance and maintainability:

```
┌─────────────────────┐    Network     ┌─────────────────────┐
│   Capture Service   │ ──────────────► │ Processing Service  │
│  (Raspberry Pi)     │    rsync/ssh   │    (Docker)         │
│      Native         │                │                     │
└─────────────────────┘                └─────────────────────┘
```

**Why This Works:**
- **Performance**: Native deployment = <50ms capture vs ~100ms Docker
- **Simplicity**: Clear separation of concerns
- **Maintainability**: Independent development and deployment
- **Scalability**: Processing can scale without affecting capture

---

## Service Details

### Capture Service (Raspberry Pi Native)
**Purpose**: Take the highest quality photos possible

**Key Components:**
- **Camera Controller**: Direct libcamera integration, <2s autofocus
- **Adaptive Scheduler**: Astronomical timing + weather awareness
- **Environmental Sensors**: Light, temperature, weather API integration
- **Storage Manager**: 48-hour local buffer with automatic cleanup

**Performance:**
- <50ms capture latency (vs ~100ms with Docker)
- ~50MB memory footprint (vs ~150MB with Docker)
- ~12W power consumption (vs ~14W with Docker)
- 50MB/s sustained write performance

**Deployment**: systemd service for reliability and auto-restart

### Processing Service (Docker)
**Purpose**: Transform raw captures into exceptional timelapses

**Key Components:**
- **Image Enhancement**: HDR processing, focus stacking, noise reduction
- **Timelapse Assembly**: Sequence building, stabilization, deflickering
- **Output Generation**: Multiple formats (4K HDR, 1080p, raw frames)
- **Archive Management**: Long-term storage with automated cleanup

**Processing Pipeline:**
```
Raw Images ──► Enhancement ──► Stacking ──► Assembly ──► Encoding ──► Archive
     │              │             │           │           │          │
     ▼              ▼             ▼           ▼           ▼          ▼
  Metadata    Noise Reduction  HDR Merge  Stabilization  H.265   Cloud Backup
              Color Correction Focus Stack  Deflicker    Multiple   S3-Compatible
              Lens Correction              Smoothing     Formats
```

**Deployment**: Docker Compose with persistent volumes for easy scaling

---

## Data Flow

### Image Processing Pipeline
```
Environmental ──► Adaptive ──► Camera ──► Raw Images ──► Local Buffer
Sensors           Control      Interface                    (48hr)
    │                │           │                           │
    ▼                ▼           ▼                           ▼
Weather APIs ── Setting ── Hardware Access ── Network Transfer
               Optimization    (libcamera)         │
                                                   ▼
Cloud Storage ◄── Final ◄── Processing ◄── Enhancement ◄── Image Queue
               Timelapses    Assembly      Pipeline
```

### Storage Strategy
- **Capture Buffer**: 100GB SSD, 48-hour retention
- **Processing Working**: 500GB for active jobs
- **Long-term Archive**: 2TB+ with automated cleanup
- **Cloud Backup**: S3-compatible for final timelapses

---

## Camera Architecture

### Abstraction Layer
**Problem**: Support different cameras without code changes
**Solution**: Factory pattern with capability discovery

```python
# Simple usage - works with any supported camera
camera = await CameraFactory.auto_detect_camera()
if camera.supports_capability(CameraCapability.HDR_BRACKETING):
    result = await camera.capture_hdr_sequence(settings)
```

**Supported Cameras:**
- Arducam IMX519 16MP (primary)
- Pi Camera v3/v2 (alternative)
- USB cameras (development)
- Mock camera (testing)

### Adaptive Control System
**Problem**: Optimize settings for changing mountain conditions
**Solution**: Environmental sensing + learning system

**Environmental Inputs:**
- Weather APIs (cloud cover, visibility, wind)
- Astronomical calculations (sun position, golden hour timing)
- Real-time sensors (ambient light, temperature)
- Image quality feedback (focus score, exposure analysis)

**Optimization Strategies:**
- **Golden Hour**: Extended intervals, HDR bracketing, warm WB preservation
- **Blue Hour**: Cool WB enhancement, longer exposures, noise reduction
- **Overcast**: Shadow lifting, contrast boost, atmospheric haze compensation
- **Stormy**: Highlight protection, dramatic cloud capture, vibration damping

### Technical Configuration
**Problem**: Each camera has unique characteristics requiring specific tuning
**Solution**: YAML-based configuration system

**Configuration Categories:**
1. **Essential**: Bayer patterns, color matrices, focus calibration
2. **Quality**: Lens corrections, noise characteristics, processing pipelines
3. **Advanced**: Thermal modeling, custom enhancement profiles

---

## Communication Architecture

### Inter-Service Communication
- **Images**: rsync over SSH (reliable, resumable, compressed)
- **Control**: REST API with JSON (configuration, status, commands)
- **Monitoring**: WebSocket (real-time updates, live preview)
- **Health**: HTTP endpoints (service status, performance metrics)

### External Integrations
- **Weather**: OpenWeatherMap API (15-minute refresh cycle)
- **Time**: NTP + astronomical libraries (precise scheduling)
- **Storage**: S3-compatible APIs (automated backup)

---

## Quality & Reliability

### Error Handling Strategy
1. **Hardware Failures**: Automatic restart, fallback modes, alert notifications
2. **Network Issues**: Queue transfers, retry with exponential backoff
3. **Storage Full**: Emergency cleanup, oldest-first deletion
4. **Service Crashes**: systemd auto-restart, Docker health checks

### Monitoring & Observability
- **Metrics**: Prometheus-compatible (capture rates, processing times, error counts)
- **Logging**: Structured JSON logs with correlation IDs
- **Health Checks**: Service endpoints with detailed status
- **Alerting**: Critical failures, performance degradation, maintenance needs

### Performance Monitoring
```python
# Key metrics tracked
capture_latency_ms          # Target: <50ms
focus_acquisition_time_s    # Target: <2s
processing_queue_depth      # Target: <10 jobs
storage_utilization_pct     # Target: <80%
image_quality_score         # Target: >0.9
system_uptime_pct          # Target: >99.5%
```

---

## Development & Deployment

### Development Workflow
1. **Local Development**: Direct SSH to Pi for camera development
2. **Processing Development**: Docker Compose for consistent environment
3. **Integration Testing**: Full system test with mock data
4. **Hardware Testing**: Controlled lighting setup with real camera

### Deployment Strategy
- **Capture**: Native systemd service deployment
- **Processing**: Docker Compose with volume persistence
- **Configuration**: Git-managed configs with validation
- **Updates**: Rolling deployment with health checks

### Scalability Considerations
- **Multi-Camera**: Factory pattern supports multiple camera instances
- **Processing Scale**: Docker Compose can scale processing workers
- **Geographic Distribution**: rsync supports remote processing servers
- **Cloud Integration**: S3 APIs enable cloud processing offload

---

## Success Metrics

### Technical Performance
- ✅ <50ms capture latency (native deployment)
- ✅ <2s autofocus acquisition (direct hardware access)
- ✅ 99.5% uptime target (robust error handling)
- ✅ Professional image quality (technical configuration system)

### Operational Excellence
- ✅ Unattended operation (adaptive control system)
- ✅ Remote monitoring (web interface + APIs)
- ✅ Easy maintenance (clear architecture + documentation)
- ✅ Future flexibility (abstraction layers + configuration)

This architecture delivers exceptional mountain timelapses through focused components, clean interfaces, and performance-optimized deployment choices.
