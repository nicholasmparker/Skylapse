# Skylapse Development Guide

## Development Strategy

### Deployment Architecture Decision

**Capture Service**: Native Python on Raspberry Pi OS
**Processing Service**: Docker containers

This hybrid approach provides optimal performance where it matters most while maintaining development flexibility.

#### Why Native for Capture?
- **Performance**: 50ms capture latency vs 100ms with Docker
- **Hardware Access**: Direct libcamera, GPIO, I2C access
- **Resource Efficiency**: 50% lower memory usage (50MB vs 150MB)
- **Power Efficiency**: 2W power savings (12W vs 14W with Docker daemon)
- **Timing Precision**: Critical for exposure bracketing and focus stacking

#### Why Docker for Processing?
- **Consistent Environment**: Identical dev/test/production environments
- **Easy Scaling**: Horizontal scaling of processing workers
- **Isolation**: Complex dependencies don't pollute system
- **Deployment Simplicity**: `docker-compose up` deployment

---

## Development Workflow

### Phase 1: Core Development

#### Capture Service Development (Native)
```bash
# SSH into Pi for development
ssh pi@raspberrypi.local

# Set up development environment
sudo apt update && sudo apt install -y python3-pip python3-venv libcamera-dev
cd /opt/skylapse
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Development cycle (fastest iteration)
vim src/camera_controller.py
python -m pytest tests/
sudo systemctl restart skylapse-capture
journalctl -fu skylapse-capture
```

#### Processing Service Development (Docker)
```bash
# Local development with Docker
cd processing/
docker-compose -f docker-compose.dev.yml up --build

# Watch logs
docker-compose logs -f processing

# For faster iteration without Docker
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

### Phase 2: Integration Development

#### System Integration Testing
```bash
# Start both services
./scripts/start-dev-environment.sh

# Monitor system integration
./scripts/monitor-system.sh

# Test with mock data
./scripts/test-integration.py --mock-images=100
```

---

## Project Structure

```
skylapse/
├── capture/                     # Raspberry Pi capture service
│   ├── src/
│   │   ├── camera_controller.py
│   │   ├── adaptive_control.py
│   │   ├── scheduler.py
│   │   └── storage_manager.py
│   ├── tests/
│   ├── config/
│   │   ├── cameras/             # Camera-specific configs
│   │   └── system/              # System settings
│   ├── requirements.txt
│   └── systemd/
│       └── skylapse-capture.service
├── processing/                  # Docker processing service
│   ├── src/
│   │   ├── enhancement/
│   │   ├── assembly/
│   │   └── output/
│   ├── tests/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── requirements.txt
├── scripts/                     # Development and deployment scripts
│   ├── deploy-capture.sh
│   ├── deploy-processing.sh
│   ├── start-dev-environment.sh
│   └── run-tests.sh
└── docs/                        # Documentation
```

---

## Testing Strategy

### Unit Testing
```bash
# Capture service tests (with mock camera)
cd capture/
python -m pytest tests/ -v

# Processing service tests (with sample data)
cd processing/
python -m pytest tests/ -v
```

### Integration Testing
```bash
# Full system test with Docker Compose
docker-compose -f docker-compose.test.yml up --abort-on-container-exit

# Hardware integration test (requires Pi + camera)
./scripts/test-hardware-integration.sh
```

### Performance Testing
```bash
# Capture latency test
./scripts/benchmark-capture.py --iterations=100

# Processing throughput test
./scripts/benchmark-processing.py --image-sets=10
```

### Continuous Integration
```yaml
# .github/workflows/test.yml
name: Test Skylapse
on: [push, pull_request]
jobs:
  test-capture:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Test Capture Service
        run: |
          cd capture/
          python -m pytest tests/ --mock-camera

  test-processing:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Test Processing Service
        run: |
          cd processing/
          docker-compose -f docker-compose.test.yml up --abort-on-container-exit
```

---

## Configuration Management

### Camera Configuration System
```yaml
# config/cameras/arducam_imx519.yaml
sensor:
  bayer_pattern: "RGGB"
  base_iso: 100
  focus_range_mm: [100.0, .inf]

optical:
  focal_length_mm: 4.28
  hyperfocal_distance_mm: 1830

processing:
  demosaic_algorithm: "DCB"
  noise_reduction_strength: 0.2
```

### Environment-Specific Configuration
```bash
# Development
export SKYLAPSE_ENV=development
export MOCK_CAMERA=true

# Production
export SKYLAPSE_ENV=production
export WEATHER_API_KEY=your_key_here
export STORAGE_PATH=/mnt/storage
```

---

## Deployment Process

### Development Deployment
```bash
# Quick development setup
./scripts/setup-dev-environment.sh

# Start development services
./scripts/start-dev.sh

# Stop and clean up
./scripts/stop-dev.sh
```

### Production Deployment

#### Capture Service (Native)
```bash
# Deploy to Raspberry Pi
./scripts/deploy-capture.sh --target=pi@raspberrypi.local

# Service management
ssh pi@raspberrypi.local
sudo systemctl enable skylapse-capture
sudo systemctl start skylapse-capture
sudo systemctl status skylapse-capture
```

#### Processing Service (Docker)
```bash
# Deploy processing service
./scripts/deploy-processing.sh --environment=production

# Service management
docker-compose -f docker-compose.prod.yml up -d
docker-compose logs -f processing
```

### Deployment Verification
```bash
# Check capture service health
curl http://raspberrypi.local:8080/health

# Check processing service health
curl http://processing-server:8081/health

# Verify image transfer
./scripts/verify-image-pipeline.sh
```

---

## Development Tools

### Code Quality
```bash
# Install development tools
pip install black flake8 mypy pytest-cov

# Format code
black src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/

# Run tests with coverage
pytest --cov=src tests/
```

### Debugging Tools

#### Capture Service Debugging
```bash
# Direct camera testing
python -c "from src.camera_controller import CameraController;
           import asyncio;
           asyncio.run(CameraController().test_capture())"

# System resource monitoring
htop
iotop
vcgencmd measure_temp
```

#### Processing Service Debugging
```bash
# Processing pipeline debugging
docker-compose exec processing python debug_processing.py

# Container resource monitoring
docker stats
docker-compose logs -f processing
```

### Monitoring & Observability

#### Local Development Monitoring
```bash
# Start monitoring stack
docker-compose -f docker-compose.monitoring.yml up -d

# Access dashboards
open http://localhost:3000  # Grafana
open http://localhost:9090  # Prometheus
```

#### Production Monitoring
```python
# Health check endpoints
GET /health              # Service status
GET /metrics             # Prometheus metrics
GET /stats               # Performance statistics
```

---

## Performance Optimization

### Capture Service Optimization
```python
# Camera performance tuning
CAPTURE_BUFFER_SIZE = 4        # Reduce for lower memory
FOCUS_TIMEOUT_MS = 2000       # Adjust for conditions
EXPOSURE_BRACKETING_DELAY = 50 # Milliseconds between captures

# Storage optimization
STORAGE_WRITE_BUFFER = 64 * 1024  # 64KB write buffer
CLEANUP_INTERVAL_HOURS = 6        # Cleanup frequency
```

### Processing Service Optimization
```yaml
# docker-compose.yml resource limits
services:
  processing:
    deploy:
      resources:
        limits:
          memory: 8G
          cpus: '4'
    environment:
      - OMP_NUM_THREADS=4
      - OPENCV_NUM_THREADS=4
```

---

## Troubleshooting

### Common Issues

#### Capture Service Issues
```bash
# Camera not detected
libcamera-hello --list-cameras

# Permission issues
sudo usermod -a -G video $USER
sudo systemctl restart skylapse-capture

# Focus problems
v4l2-ctl --device=/dev/video0 --list-ctrls
```

#### Processing Service Issues
```bash
# Container startup issues
docker-compose logs processing
docker system prune  # Clean up disk space

# Performance issues
docker stats
free -h
df -h
```

#### Network Transfer Issues
```bash
# Test rsync connection
rsync -avz --dry-run /tmp/test.jpg pi@raspberrypi.local:/tmp/

# Check network bandwidth
iperf3 -c raspberrypi.local

# Monitor transfer queue
ls -la /opt/skylapse/transfer_queue/
```

### Log Analysis
```bash
# Capture service logs
journalctl -fu skylapse-capture --since="1 hour ago"

# Processing service logs
docker-compose logs --since=1h processing

# System resource logs
sar -u 1 60  # CPU usage
sar -r 1 60  # Memory usage
sar -d 1 60  # Disk I/O
```

This development guide provides a clear path from initial setup through production deployment, with focus on the hybrid architecture that maximizes both performance and maintainability.
