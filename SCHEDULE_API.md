# Schedule Management API

This document describes the complete Schedule Management API implementation for the Skylapse mountain timelapse camera system.

## Overview

The Schedule Management API provides full CRUD (Create, Read, Update, Delete) operations for managing automated capture schedules. These schedules define when the camera should take photos, with support for:

- Time-based scheduling (start/end times, days of week, intervals)
- Environmental conditions (weather dependency, light levels, wind speed)
- Capture settings (presets or manual camera settings)
- Execution tracking and status monitoring

## API Endpoints

All endpoints use the base path `/api/schedule` on the capture service (default: `helios.local:8080`).

### GET /api/schedule

Get all schedule rules.

**Response:**
```json
{
  "data": [
    {
      "id": "uuid-string",
      "name": "Golden Hour Schedule",
      "description": "Captures during golden hour",
      "enabled": true,
      "startTime": "06:00",
      "endTime": "08:00",
      "intervalMinutes": 5,
      "daysOfWeek": [1, 2, 3, 4, 5],
      "captureSettings": {
        "preset": "golden_hour"
      },
      "conditions": {
        "weatherDependent": true,
        "minLightLevel": 10.0,
        "maxWindSpeed": 20.0
      },
      "nextExecution": "2025-09-29T06:00:00",
      "lastExecution": null,
      "status": "active",
      "executionCount": 0,
      "createdAt": "2025-09-28T12:00:00"
    }
  ],
  "total": 1,
  "status": 200,
  "message": "Schedules retrieved successfully"
}
```

### POST /api/schedule

Create a new schedule rule.

**Request Body:**
```json
{
  "name": "Golden Hour Schedule",
  "description": "Automated golden hour captures",
  "enabled": true,
  "startTime": "06:00",
  "endTime": "08:00",
  "intervalMinutes": 5,
  "daysOfWeek": [1, 2, 3, 4, 5],
  "captureSettings": {
    "preset": "golden_hour"
  },
  "conditions": {
    "weatherDependent": true,
    "minLightLevel": 10.0,
    "maxWindSpeed": 20.0
  }
}
```

**Response (201 Created):**
```json
{
  "data": {
    "id": "generated-uuid",
    "name": "Golden Hour Schedule",
    // ... full schedule object
  },
  "status": 201,
  "message": "Schedule 'Golden Hour Schedule' created successfully"
}
```

### GET /api/schedule/{id}

Get a specific schedule by ID.

**Response (200 OK):**
```json
{
  "data": {
    // ... full schedule object
  },
  "status": 200,
  "message": "Schedule retrieved successfully"
}
```

**Response (404 Not Found):**
```json
{
  "error": "Schedule not found"
}
```

### PUT /api/schedule/{id}

Update an existing schedule.

**Request Body:**
```json
{
  "name": "Updated Schedule Name",
  "intervalMinutes": 10,
  "enabled": false
}
```

**Response (200 OK):**
```json
{
  "data": {
    // ... updated schedule object
  },
  "status": 200,
  "message": "Schedule 'Updated Schedule Name' updated successfully"
}
```

### DELETE /api/schedule/{id}

Delete a schedule.

**Response (200 OK):**
```json
{
  "data": {
    "id": "schedule-id",
    "deleted": true
  },
  "status": 200,
  "message": "Schedule 'Schedule Name' deleted successfully"
}
```

## Data Models

### ScheduleRule

The main schedule object with the following properties:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | No* | Unique identifier (auto-generated if not provided) |
| `name` | string | Yes | Human-readable schedule name |
| `description` | string | No | Optional description |
| `enabled` | boolean | No | Whether schedule is active (default: true) |
| `startTime` | string | Yes | Start time in HH:MM format (24-hour) |
| `endTime` | string | Yes | End time in HH:MM format (24-hour) |
| `intervalMinutes` | integer | Yes | Capture interval in minutes |
| `daysOfWeek` | array | No | Days when schedule runs (0=Sunday, 1=Monday, etc.) |
| `captureSettings` | object | No | Camera capture settings |
| `conditions` | object | No | Environmental conditions |
| `nextExecution` | string | No* | Next scheduled execution (ISO datetime) |
| `lastExecution` | string | No* | Last execution time (ISO datetime) |
| `status` | string | No* | Schedule status: "active", "paused", "completed", "error" |
| `executionCount` | integer | No* | Number of times schedule has executed |
| `createdAt` | string | No* | Creation timestamp (ISO datetime) |

*Auto-managed fields

### CaptureSettings

Defines how the camera should capture images:

```json
{
  "preset": "golden_hour"
}
```

Or for manual settings:

```json
{
  "manual": {
    "iso": 100,
    "exposureTime": "1/125",
    "hdrBracketing": true,
    "quality": 95
  }
}
```

### Conditions

Environmental conditions for schedule execution:

```json
{
  "weatherDependent": true,
  "minLightLevel": 10.0,
  "maxWindSpeed": 20.0
}
```

## Schedule Execution

The schedule executor runs continuously and:

1. Checks for schedules ready for execution every 30 seconds
2. Validates environmental conditions (if specified)
3. Triggers camera captures according to schedule settings
4. Updates execution statistics and next execution times
5. Handles failures with appropriate error tracking

### Status Values

- **active**: Schedule is running and will execute at scheduled times
- **paused**: Schedule is temporarily disabled
- **completed**: Schedule has finished (not currently used for recurring schedules)
- **error**: Schedule encountered an error and needs attention

## Time Handling

- All times use 24-hour format (HH:MM)
- Overnight schedules are supported (e.g., startTime: "22:00", endTime: "06:00")
- Days of week: 0=Sunday, 1=Monday, 2=Tuesday, 3=Wednesday, 4=Thursday, 5=Friday, 6=Saturday
- All timestamps in responses are in ISO format

## Error Handling

The API returns appropriate HTTP status codes:

- **200**: Success
- **201**: Created
- **400**: Bad Request (validation errors)
- **404**: Not Found
- **500**: Internal Server Error

Error responses include descriptive error messages:

```json
{
  "error": "Missing required field: name"
}
```

## Validation Rules

- Schedule names must be unique and non-empty
- Time format must be HH:MM (24-hour)
- Interval must be positive integer (minutes)
- Days of week must be integers 0-6
- Cannot specify both preset and manual capture settings
- Manual settings require: iso, exposureTime, hdrBracketing, quality

## Integration with Existing System

The schedule management system integrates with:

- **Camera Controller**: Executes captures with specified settings
- **Storage Manager**: Stores captured images
- **Transfer Manager**: Queues images for processing service
- **Environmental Sensor**: Checks conditions before capture

## File Storage

Schedules are persisted to `/opt/skylapse/data/schedules/schedules.json` with automatic backup and recovery.

## Testing

Use the provided test script to validate the API:

```bash
python3 test_schedule_api.py
```

This script tests all endpoints and validates proper error handling.

## Examples

### Basic Schedule
```bash
curl -X POST http://helios.local:8080/api/schedule \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Hourly Daylight",
    "startTime": "08:00",
    "endTime": "18:00",
    "intervalMinutes": 60,
    "captureSettings": {"preset": "daylight"}
  }'
```

### Advanced Schedule with Conditions
```bash
curl -X POST http://helios.local:8080/api/schedule \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Weather-Dependent Sunrise",
    "description": "Captures sunrise only in good weather",
    "startTime": "05:30",
    "endTime": "07:30",
    "intervalMinutes": 2,
    "daysOfWeek": [6, 0],
    "captureSettings": {
      "manual": {
        "iso": 200,
        "exposureTime": "1/60",
        "hdrBracketing": true,
        "quality": 100
      }
    },
    "conditions": {
      "weatherDependent": true,
      "minLightLevel": 5.0,
      "maxWindSpeed": 15.0
    }
  }'
```

### Get All Schedules
```bash
curl http://helios.local:8080/api/schedule
```

### Update Schedule
```bash
curl -X PUT http://helios.local:8080/api/schedule/{schedule-id} \
  -H "Content-Type: application/json" \
  -d '{
    "intervalMinutes": 30,
    "enabled": false
  }'
```

### Delete Schedule
```bash
curl -X DELETE http://helios.local:8080/api/schedule/{schedule-id}
```
