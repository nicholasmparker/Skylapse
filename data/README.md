# Skylapse Data Storage

This directory contains persistent data for the Skylapse system.

## Directory Structure

```
data/
├── images/          # Images transferred from Pi (organized by profile)
│   ├── profile-a/
│   ├── profile-b/
│   ├── profile-c/
│   ├── profile-d/
│   ├── profile-e/
│   └── profile-f/
└── timelapses/      # Generated timelapse videos
    ├── sunrise-2025-10-01.mp4
    ├── sunset-2025-10-01.mp4
    └── ...
```

## Docker Volumes

These directories are mounted as Docker volumes in `docker-compose.yml`:

- `skylapse-images` → `/data/images` (inside containers)
- `skylapse-timelapses` → `/data/timelapses` (inside containers)

## Configuration

You can customize the storage paths by creating a `.env` file:

```bash
cp .env.example .env
# Edit paths as needed
SKYLAPSE_IMAGES_PATH=/path/to/your/images
SKYLAPSE_TIMELAPSES_PATH=/path/to/your/timelapses
```

## Storage Requirements

- **Images**: ~200MB per day per profile (6 profiles = 1.2GB/day)
- **Timelapses**: ~50MB per video
- **Recommended**: 100GB+ for multi-month storage

## Lifecycle

1. **Capture** - Pi captures images to `~/skylapse-images/`
2. **Transfer** - Images periodically synced to `data/images/`
3. **Process** - Timelapse generator creates videos in `data/timelapses/`
4. **Archive** - Old images can be deleted after processing
