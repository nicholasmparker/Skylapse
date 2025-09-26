# Skylapse Documentation

Professional mountain timelapse system using Raspberry Pi with intelligent camera control and advanced image processing.

## Quick Start

1. **[Architecture](ARCHITECTURE.md)** - System design and component overview
2. **[Development Guide](DEVELOPMENT.md)** - Setup, testing, and deployment
3. **[Product Requirements](PRD.md)** - Features and specifications

## Architecture Documents

- **[Camera Design](CAMERA_DESIGN.md)** - Multi-camera abstraction and adaptive control
- **[Technical Reference](reference/CAMERA_SPECS.md)** - Detailed camera specifications

## System Overview

### Two-Service Architecture
```
Capture Service (Pi Native) ──► Processing Service (Docker)
    │                                │
    ▼                                ▼
• Camera control                  • Image enhancement
• Environmental sensing           • HDR processing
• Adaptive scheduling            • Timelapse assembly
• Local buffering               • Multi-format output
```

### Key Features
- **<50ms capture latency** (native Pi deployment)
- **Adaptive environmental response** (weather + astronomical awareness)
- **Multi-camera ready** (factory pattern + capability discovery)
- **Professional quality** (HDR, focus stacking, noise reduction)
- **Unattended operation** (99.5% uptime target)

### Performance
- <2s autofocus acquisition
- ~12W power consumption
- 48-hour local image buffering
- Multiple output formats (4K HDR, 1080p, raw frames)

## Development Phases

**Phase 1**: Core capture and processing
**Phase 2**: Adaptive control and camera abstraction
**Phase 3**: Learning system and multi-camera support

---

*For detailed technical information, see the specific documents above.*