# Dagon Deployment Steps - Data-Driven Profiles Update

## What Just Happened

GitHub Actions built and pushed new Docker images with data-driven profiles to:
- `ghcr.io/nicholasmparker/skylapse/backend:main`
- `ghcr.io/nicholasmparker/skylapse/frontend:main`
- `ghcr.io/nicholasmparker/skylapse/worker:main`

## What You Need to Do on Dagon

### Step 1: SSH to Dagon

```bash
ssh your-user@dagon-server
cd /path/to/skylapse  # Your Skylapse installation directory
```

### Step 2: Update config.json with Profiles

Your Dagon `config.json` needs the new `profiles` section.

**Option A: Merge with existing config**

If your existing config.json looks like this:
```json
{
  "schedules": { ... },
  "location": { ... },
  "pi": { ... }
}
```

Add the `profiles` section at the top (see `config.json.example` in repo for full structure):

```bash
# Backup existing config
cp config.json config.json.backup

# Edit config.json and add profiles section
nano config.json
```

**Option B: Copy example and customize**

```bash
# Backup existing config
cp config.json config.json.backup

# Download new example
curl -o config.json https://raw.githubusercontent.com/nicholasmparker/Skylapse/main/config.json.example

# Edit with your specific values
nano config.json
```

### Step 3: Update Environment Variables (if using .env)

No changes needed to .env - all profile configuration is now in config.json!

### Step 4: Pull New Docker Images

```bash
# Authenticate to GitHub Container Registry (if needed)
echo $GITHUB_TOKEN | docker login ghcr.io -u nicholasmparker --password-stdin

# Pull new images
docker pull ghcr.io/nicholasmparker/skylapse/backend:main
docker pull ghcr.io/nicholasmparker/skylapse/frontend:main
docker pull ghcr.io/nicholasmparker/skylapse/worker:main
```

### Step 5: Restart Services

```bash
# Stop current services
docker-compose down

# Start with new images
docker-compose up -d

# Or if you have a restart script:
./restart.sh
```

### Step 6: Verify Deployment

```bash
# Check backend started successfully
docker-compose logs backend --tail=50

# Look for these success messages:
# ✓ Configuration validated successfully (config.json)
# ✓ Settings loaded successfully
# 🔍 Checking schedule: sunrise, enabled=True, profiles=['a', 'b', 'd', 'g']
```

**Check for errors**:
```bash
# If you see validation errors, fix config.json:
docker-compose logs backend | grep -i "error"

# Common issues:
# - Missing 'profiles' section → Add profiles from config.json.example
# - Invalid profile ID → Must be single lowercase letter (a-g)
# - Missing curve → adaptive_wb/adaptive_ev needs curve: "warm"|"balanced"|"conservative"|"adaptive"
```

### Step 7: Test the System

```bash
# Check API returns dynamic profiles
curl http://localhost:8082/system | jq '.camera.profiles_configured'
# Should return: ["a", "b", "c", "d", "e", "f", "g"]

# Check profiles endpoint
curl http://localhost:8082/profiles | jq
```

### Step 8: Monitor First Capture

```bash
# Watch scheduler logs
docker-compose logs -f backend

# Wait for next sunrise/sunset window to see:
# 📸 Triggering capture burst for sunrise - 4 profiles: ['a', 'b', 'd', 'g']
# 📸 Profile A (Pure Auto + Autofocus): ...
# 📸 Profile B (Ultra-Vibrant Warm WB + Maximum Sharpness): ...
```

## Configuration Reference

### Profile Structure

```json
{
  "profiles": {
    "a": {
      "name": "Profile Name",
      "description": "Profile description",
      "enabled": true,
      "settings": {
        "base": {
          "iso": 100,                    // or 0 for auto
          "shutter_speed": "1/500",      // or "auto"
          "awb_mode": 6,                 // 0=auto, 1=daylight, 6=custom
          "hdr_mode": 0,                 // 0=off, 1=on
          "bracket_count": 1,
          "af_mode": 0,                  // 0=manual, 2=auto
          "lens_position": 2.45,         // for manual focus
          "sharpness": 1.5,              // optional enhancement
          "contrast": 1.15,              // optional enhancement
          "saturation": 1.05             // optional enhancement
        },
        "adaptive_wb": {
          "enabled": true,
          "curve": "warm"                // "warm"|"balanced"|"conservative"
        },
        "adaptive_ev": {
          "enabled": true,
          "curve": "adaptive"            // currently only "adaptive"
        }
      },
      "video_filters": "unsharp=5:5:1.0:5:5:0.0"  // optional ffmpeg filters
    }
  }
}
```

### Schedule Structure

```json
{
  "schedules": {
    "sunrise": {
      "enabled": true,
      "type": "solar_relative",
      "anchor": "sunrise",
      "offset_minutes": -30,
      "duration_minutes": 60,
      "interval_seconds": 5,
      "profiles": ["a", "b", "d", "g"]  // NEW: specify which profiles to capture
    }
  }
}
```

## Customization Examples

### Example 1: Change Profile B Saturation

Edit config.json:
```json
"b": {
  "settings": {
    "base": {
      "saturation": 1.8  // Changed from 2.0
    }
  }
}
```

Then: `docker-compose restart backend` (5 seconds!)

### Example 2: Enable Profile C for Testing

```json
"c": {
  "enabled": true  // Changed from false
}
```

Add to schedule:
```json
"sunrise": {
  "profiles": ["a", "b", "c", "d", "g"]  // Added 'c'
}
```

Then: `docker-compose restart backend`

### Example 3: Add New Profile H

```json
"h": {
  "name": "Your Custom Profile",
  "description": "Custom settings for specific conditions",
  "enabled": true,
  "settings": {
    "base": {
      "iso": 200,
      "shutter_speed": "1/1000",
      "awb_mode": 1
    },
    "adaptive_wb": { "enabled": false },
    "adaptive_ev": { "enabled": false }
  }
}
```

## Rollback Instructions

If something goes wrong:

```bash
# Restore old config
cp config.json.backup config.json

# Pull previous images (replace COMMIT_SHA with previous commit)
docker pull ghcr.io/nicholasmparker/skylapse/backend:COMMIT_SHA

# Or use a specific version tag if available
docker pull ghcr.io/nicholasmparker/skylapse/backend:v1.0.0

# Restart
docker-compose down
docker-compose up -d
```

## Support

If you encounter issues:
1. Check backend logs: `docker-compose logs backend`
2. Validate config: Backend will show validation errors on startup
3. Compare with config.json.example in repo
4. Check GitHub Actions build status: https://github.com/nicholasmparker/Skylapse/actions
