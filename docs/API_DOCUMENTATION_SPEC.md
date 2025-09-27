# Skylapse API Documentation Specification

**Date**: September 27, 2025
**Product Manager**: Cooper - Technical PM & Raspberry Pi Development
**Purpose**: **AMAZING, BEAUTIFUL, MOST MODERN** API documentation standards
**Status**: **COMPREHENSIVE SPECIFICATION FOR SPRINT 3** 📚

---

## 🎯 **API Documentation Vision**

### **Mission Statement**
Create **THE MOST BEAUTIFUL AND COMPREHENSIVE** API documentation that showcases our engineering excellence and makes developers fall in love with integrating Skylapse.

### **Success Criteria**
- **Developer Delight**: Developers can integrate in <30 minutes
- **Professional Quality**: Documentation quality matches our code quality
- **Interactive Experience**: Every endpoint testable from documentation
- **Beautiful Design**: Modern, clean aesthetic matching our interface
- **Comprehensive Coverage**: 100% API coverage with examples

---

## 📋 **OpenAPI 3.0 Specification Requirements**

### **Complete API Specification Structure**
```yaml
# skylapse-api.yaml - Complete OpenAPI 3.0 specification
openapi: 3.0.3
info:
  title: Skylapse Mountain Timelapse API
  version: 1.0.0
  description: |
    # 🏔️ Skylapse API Documentation

    Professional mountain timelapse capture and processing system with intelligent scheduling,
    HDR processing, and real-time monitoring capabilities.

    ## 🚀 Features
    - **Real-time Capture Control**: Start, stop, and configure timelapse captures
    - **Intelligent Scheduling**: Astronomical event-based scheduling with golden hour optimization
    - **HDR Processing**: Professional HDR bracketing and tone mapping
    - **Resource Monitoring**: Real-time system health and performance metrics
    - **Timelapse Assembly**: Automated video generation with multiple format support

    ## 🔐 Authentication
    All endpoints require JWT authentication. Obtain a token from the `/auth/login` endpoint.

    ```python
    # Python example
    import requests

    response = requests.post('/auth/login', json={
        'username': 'photographer',
        'password': 'your_password'
    })
    token = response.json()['access_token']
    headers = {'Authorization': f'Bearer {token}'}
    ```

    ## ⚡ Rate Limiting
    - **Authenticated Users**: 1000 requests per hour
    - **Unauthenticated**: 100 requests per hour
    - **WebSocket Connections**: 10 concurrent connections per user

    ## 📡 Real-time Updates
    WebSocket connections available at `/ws/dashboard` for real-time system updates.

  contact:
    name: Skylapse API Support
    url: https://skylapse.dev/support
    email: api@skylapse.dev
  license:
    name: MIT
    url: https://opensource.org/licenses/MIT
  x-logo:
    url: /static/skylapse-logo.png
    altText: Skylapse Mountain Timelapse System

servers:
  - url: https://api.skylapse.dev/v1
    description: Production server
  - url: https://staging-api.skylapse.dev/v1
    description: Staging server
  - url: http://localhost:8000/api/v1
    description: Local development server

# Security schemes
components:
  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
      description: |
        JWT token obtained from `/auth/login` endpoint.

        **Example**: `Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`

security:
  - BearerAuth: []

# Global tags for organization
tags:
  - name: Authentication
    description: User authentication and token management
  - name: Capture Control
    description: Timelapse capture control and configuration
  - name: System Monitoring
    description: Real-time system health and performance monitoring
  - name: Processing
    description: HDR processing and timelapse assembly
  - name: Gallery
    description: Timelapse gallery and metadata management
  - name: Scheduling
    description: Intelligent capture scheduling and astronomical events
  - name: Settings
    description: System configuration and user preferences
```

### **Endpoint Documentation Standards**
```yaml
# Example endpoint with comprehensive documentation
paths:
  /capture/start:
    post:
      tags: [Capture Control]
      summary: Start Timelapse Capture
      description: |
        Begin capturing a timelapse sequence with specified settings. The system will
        automatically handle scheduling, HDR bracketing, and resource management.

        ## 🎯 Use Cases
        - **Manual Capture**: Immediate start with custom settings
        - **Scheduled Capture**: Start with predefined schedule rules
        - **Golden Hour Capture**: Optimized settings for mountain photography

        ## ⚠️ Important Notes
        - Only one capture session can be active at a time
        - Settings are validated before starting capture
        - System resources are monitored during capture

      operationId: startCapture
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CaptureStartRequest'
            examples:
              basic_capture:
                summary: Basic 1-hour capture
                description: Simple timelapse with default settings
                value:
                  interval_seconds: 300
                  duration_minutes: 60
                  hdr_enabled: false
              golden_hour_hdr:
                summary: Golden hour HDR capture
                description: Optimized for mountain golden hour photography
                value:
                  interval_seconds: 2
                  duration_minutes: 120
                  hdr_enabled: true
                  bracket_stops: 5
                  iso: 100
                  location:
                    latitude: 40.7589
                    longitude: -111.8883
                    name: "Park City, UT"
              burst_mode:
                summary: Sunrise burst capture
                description: High-frequency capture for sunrise sequences
                value:
                  interval_seconds: 1
                  duration_minutes: 30
                  hdr_enabled: true
                  bracket_stops: 3
                  trigger_condition: "sunrise_window"
      responses:
        '200':
          description: Capture started successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/CaptureStartResponse'
              example:
                capture_id: "cap_20250927_golden_001"
                status: "started"
                estimated_frames: 240
                estimated_completion: "2025-09-27T18:30:00Z"
                next_capture_at: "2025-09-27T16:32:00Z"
        '400':
          description: Invalid capture settings
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
              examples:
                invalid_interval:
                  summary: Invalid capture interval
                  value:
                    error: "validation_error"
                    message: "Capture interval must be between 1 and 3600 seconds"
                    details:
                      field: "interval_seconds"
                      provided: 0
                      allowed_range: [1, 3600]
        '409':
          description: Capture already in progress
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
              example:
                error: "capture_in_progress"
                message: "Another capture session is currently active"
                details:
                  active_capture_id: "cap_20250927_morning_001"
                  started_at: "2025-09-27T14:15:00Z"
        '503':
          description: System not ready for capture
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
              example:
                error: "system_not_ready"
                message: "Camera not available or system resources insufficient"
                details:
                  camera_status: "disconnected"
                  available_storage_gb: 2.1
                  required_storage_gb: 5.0
      x-code-samples:
        - lang: Python
          source: |
            import requests

            # Start a golden hour HDR capture
            response = requests.post('/api/v1/capture/start',
                headers={'Authorization': f'Bearer {token}'},
                json={
                    'interval_seconds': 2,
                    'duration_minutes': 120,
                    'hdr_enabled': True,
                    'bracket_stops': 5,
                    'location': {
                        'latitude': 40.7589,
                        'longitude': -111.8883,
                        'name': 'Park City, UT'
                    }
                }
            )

            if response.status_code == 200:
                capture_info = response.json()
                print(f"Capture started: {capture_info['capture_id']}")
            else:
                print(f"Error: {response.json()['message']}")
        - lang: JavaScript
          source: |
            // Start capture with fetch API
            const response = await fetch('/api/v1/capture/start', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    interval_seconds: 2,
                    duration_minutes: 120,
                    hdr_enabled: true,
                    bracket_stops: 5,
                    location: {
                        latitude: 40.7589,
                        longitude: -111.8883,
                        name: 'Park City, UT'
                    }
                })
            });

            if (response.ok) {
                const captureInfo = await response.json();
                console.log(`Capture started: ${captureInfo.capture_id}`);
            } else {
                const error = await response.json();
                console.error(`Error: ${error.message}`);
            }
        - lang: curl
          source: |
            # Start golden hour HDR capture
            curl -X POST "https://api.skylapse.dev/v1/capture/start" \
                -H "Authorization: Bearer $TOKEN" \
                -H "Content-Type: application/json" \
                -d '{
                    "interval_seconds": 2,
                    "duration_minutes": 120,
                    "hdr_enabled": true,
                    "bracket_stops": 5,
                    "location": {
                        "latitude": 40.7589,
                        "longitude": -111.8883,
                        "name": "Park City, UT"
                    }
                }'
```

---

## 🎨 **Documentation Design Requirements**

### **Custom Styling Specification**
```css
/* swagger-ui-custom.css - Beautiful mountain photography theme */
:root {
  /* Mountain-inspired color palette */
  --mountain-snow: #f8fafc;
  --mountain-mist: #f1f5f9;
  --mountain-stone: #64748b;
  --mountain-forest: #334155;
  --mountain-night: #0f172a;
  --golden-hour: #f59e0b;
  --blue-hour: #3b82f6;

  /* Typography */
  --font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  --font-mono: 'JetBrains Mono', 'Monaco', monospace;
}

/* Custom Swagger UI styling */
.swagger-ui {
  font-family: var(--font-family);
}

.swagger-ui .topbar {
  background: linear-gradient(135deg, var(--mountain-forest), var(--mountain-stone));
  border-bottom: 3px solid var(--golden-hour);
}

.swagger-ui .info {
  margin: 2rem 0;
}

.swagger-ui .info .title {
  color: var(--mountain-forest);
  font-size: 2.5rem;
  font-weight: 700;
}

.swagger-ui .scheme-container {
  background: var(--mountain-mist);
  border: 1px solid var(--mountain-stone);
  border-radius: 8px;
  padding: 1rem;
}

/* Operation styling */
.swagger-ui .opblock {
  border-radius: 8px;
  margin-bottom: 1rem;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.swagger-ui .opblock.opblock-post {
  border-color: var(--golden-hour);
}

.swagger-ui .opblock.opblock-get {
  border-color: var(--blue-hour);
}

/* Code examples */
.swagger-ui .highlight-code {
  font-family: var(--font-mono);
  background: var(--mountain-night);
  color: var(--mountain-snow);
  border-radius: 6px;
  padding: 1rem;
}

/* Response examples */
.swagger-ui .response-col_status {
  font-family: var(--font-mono);
  font-weight: 600;
}

/* Custom logo styling */
.swagger-ui .info .logo {
  max-height: 60px;
  margin-bottom: 1rem;
}
```

### **Interactive Features Requirements**
```javascript
// Custom JavaScript for enhanced documentation experience
document.addEventListener('DOMContentLoaded', function() {
  // Add copy-to-clipboard functionality
  document.querySelectorAll('.highlight-code').forEach(block => {
    const button = document.createElement('button');
    button.className = 'copy-button';
    button.textContent = 'Copy';
    button.onclick = () => {
      navigator.clipboard.writeText(block.textContent);
      button.textContent = 'Copied!';
      setTimeout(() => button.textContent = 'Copy', 2000);
    };
    block.appendChild(button);
  });

  // Add endpoint testing functionality
  const testButtons = document.querySelectorAll('.try-out-btn');
  testButtons.forEach(button => {
    button.addEventListener('click', function() {
      // Enhanced try-it-out functionality
      console.log('Testing endpoint...');
    });
  });

  // Add search functionality
  const searchInput = document.createElement('input');
  searchInput.type = 'search';
  searchInput.placeholder = 'Search endpoints...';
  searchInput.className = 'api-search';
  document.querySelector('.topbar').appendChild(searchInput);
});
```

---

## 📚 **Documentation Sections Required**

### **1. Getting Started Guide**
```markdown
# 🚀 Getting Started with Skylapse API

## Quick Start (5 minutes)

### 1. Authentication
```python
import requests

# Login to get access token
response = requests.post('https://api.skylapse.dev/v1/auth/login', json={
    'username': 'your_username',
    'password': 'your_password'
})
token = response.json()['access_token']
```

### 2. Check System Status
```python
# Verify system is ready
headers = {'Authorization': f'Bearer {token}'}
status = requests.get('https://api.skylapse.dev/v1/system/status', headers=headers)
print(status.json())
```

### 3. Start Your First Capture
```python
# Start a basic timelapse
capture = requests.post('https://api.skylapse.dev/v1/capture/start',
    headers=headers,
    json={
        'interval_seconds': 300,
        'duration_minutes': 60
    }
)
print(f"Capture started: {capture.json()['capture_id']}")
```

## 📖 Next Steps
- [Authentication Guide](#authentication)
- [Capture Control](#capture-control)
- [Real-time Monitoring](#websocket-api)
- [SDK Documentation](#sdks)
```

### **2. WebSocket API Documentation**
```markdown
# 📡 Real-time WebSocket API

## Connection
```javascript
const socket = io('wss://api.skylapse.dev', {
    auth: { token: 'your_jwt_token' }
});

// System status updates
socket.on('system_status', (data) => {
    console.log('System status:', data);
});

// Capture progress updates
socket.on('capture_progress', (data) => {
    console.log('Capture progress:', data);
});

// Resource monitoring
socket.on('resource_metrics', (data) => {
    console.log('Resource usage:', data);
});
```

## Event Types
| Event | Description | Frequency |
|-------|-------------|-----------|
| `system_status` | Overall system health | Every 10 seconds |
| `capture_progress` | Active capture status | Every capture |
| `resource_metrics` | CPU, memory, temperature | Every 5 seconds |
| `environmental_data` | Sun position, weather | Every minute |
```

### **3. Error Handling Guide**
```markdown
# ⚠️ Error Handling

## Error Response Format
All API errors follow a consistent format:

```json
{
    "error": "error_code",
    "message": "Human-readable error description",
    "details": {
        "field": "specific_field_with_error",
        "provided": "invalid_value",
        "expected": "expected_format"
    },
    "timestamp": "2025-09-27T16:30:00Z",
    "request_id": "req_abc123"
}
```

## Common Error Codes
| Code | HTTP Status | Description | Resolution |
|------|-------------|-------------|------------|
| `authentication_required` | 401 | Missing or invalid token | Obtain new token from `/auth/login` |
| `insufficient_permissions` | 403 | User lacks required permissions | Contact administrator |
| `validation_error` | 400 | Invalid request parameters | Check request format |
| `capture_in_progress` | 409 | Another capture is active | Stop current capture first |
| `system_not_ready` | 503 | System unavailable | Check system status |
```

---

## 🔧 **Implementation Requirements for Alex**

### **FastAPI Integration**
```python
# Enhanced FastAPI app with comprehensive documentation
from fastapi import FastAPI, HTTPException
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# Mount static files for custom styling
app.mount("/static", StaticFiles(directory="static"), name="static")

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="Skylapse Mountain Timelapse API",
        version="1.0.0",
        description=open("docs/api_description.md").read(),
        routes=app.routes,
    )

    # Add custom extensions
    openapi_schema["info"]["x-logo"] = {"url": "/static/skylapse-logo.png"}
    openapi_schema["info"]["contact"] = {
        "name": "Skylapse API Support",
        "url": "https://skylapse.dev/support",
        "email": "api@skylapse.dev"
    }

    # Add code examples to all endpoints
    for path, methods in openapi_schema["paths"].items():
        for method, operation in methods.items():
            if "x-code-samples" not in operation:
                operation["x-code-samples"] = generate_code_samples(path, method, operation)

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="Skylapse API Documentation",
        swagger_css_url="/static/swagger-ui-custom.css",
        swagger_js_url="/static/swagger-ui-custom.js",
        swagger_favicon_url="/static/favicon.ico",
    )

@app.get("/redoc", include_in_schema=False)
async def redoc_html():
    return get_redoc_html(
        openapi_url="/openapi.json",
        title="Skylapse API Documentation",
        redoc_favicon_url="/static/favicon.ico",
    )
```

### **Comprehensive Schema Definitions**
```python
# Complete Pydantic models for API documentation
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class CaptureStatus(str, Enum):
    IDLE = "idle"
    STARTING = "starting"
    ACTIVE = "active"
    STOPPING = "stopping"
    ERROR = "error"

class LocationInfo(BaseModel):
    """Geographic location information for astronomical calculations."""
    latitude: float = Field(..., ge=-90, le=90, description="Latitude in decimal degrees")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude in decimal degrees")
    name: Optional[str] = Field(None, description="Human-readable location name")
    timezone: Optional[str] = Field(None, description="IANA timezone identifier")

    class Config:
        schema_extra = {
            "example": {
                "latitude": 40.7589,
                "longitude": -111.8883,
                "name": "Park City, UT",
                "timezone": "America/Denver"
            }
        }

class CaptureSettings(BaseModel):
    """Comprehensive capture configuration settings."""
    interval_seconds: int = Field(..., ge=1, le=3600, description="Interval between captures in seconds")
    duration_minutes: Optional[int] = Field(None, ge=1, description="Total capture duration in minutes")
    hdr_enabled: bool = Field(False, description="Enable HDR bracketing")
    bracket_stops: Optional[int] = Field(3, ge=1, le=7, description="Number of HDR bracket exposures")
    iso: Optional[int] = Field(100, ge=100, le=6400, description="ISO sensitivity")
    location: Optional[LocationInfo] = Field(None, description="Location for astronomical calculations")

    class Config:
        schema_extra = {
            "examples": [
                {
                    "name": "Basic Capture",
                    "value": {
                        "interval_seconds": 300,
                        "duration_minutes": 60,
                        "hdr_enabled": False
                    }
                },
                {
                    "name": "Golden Hour HDR",
                    "value": {
                        "interval_seconds": 2,
                        "duration_minutes": 120,
                        "hdr_enabled": True,
                        "bracket_stops": 5,
                        "iso": 100,
                        "location": {
                            "latitude": 40.7589,
                            "longitude": -111.8883,
                            "name": "Park City, UT"
                        }
                    }
                }
            ]
        }
```

---

## 📊 **Documentation Quality Metrics**

### **Automated Quality Checks**
```python
# Documentation quality validation script
import requests
import json
from typing import Dict, List

def validate_api_documentation():
    """Validate API documentation completeness and quality."""

    # Check OpenAPI specification
    spec = requests.get('/openapi.json').json()

    quality_score = 0
    max_score = 100

    # Check basic completeness (20 points)
    if spec.get('info', {}).get('description'):
        quality_score += 5
    if spec.get('info', {}).get('contact'):
        quality_score += 5
    if spec.get('servers'):
        quality_score += 5
    if spec.get('components', {}).get('securitySchemes'):
        quality_score += 5

    # Check endpoint documentation (40 points)
    total_endpoints = 0
    documented_endpoints = 0

    for path, methods in spec.get('paths', {}).items():
        for method, operation in methods.items():
            total_endpoints += 1

            # Check for comprehensive documentation
            if operation.get('description') and len(operation['description']) > 50:
                documented_endpoints += 1
            if operation.get('examples') or operation.get('x-code-samples'):
                documented_endpoints += 0.5

    if total_endpoints > 0:
        endpoint_score = (documented_endpoints / total_endpoints) * 40
        quality_score += endpoint_score

    # Check schema documentation (20 points)
    schemas = spec.get('components', {}).get('schemas', {})
    schema_score = min(len(schemas) * 2, 20)  # 2 points per schema, max 20
    quality_score += schema_score

    # Check error documentation (20 points)
    error_responses = 0
    total_responses = 0

    for path, methods in spec.get('paths', {}).items():
        for method, operation in methods.items():
            for status_code, response in operation.get('responses', {}).items():
                total_responses += 1
                if status_code.startswith('4') or status_code.startswith('5'):
                    if response.get('content') and response.get('description'):
                        error_responses += 1

    if total_responses > 0:
        error_score = (error_responses / total_responses) * 20
        quality_score += error_score

    return {
        'quality_score': quality_score,
        'max_score': max_score,
        'percentage': (quality_score / max_score) * 100,
        'total_endpoints': total_endpoints,
        'documented_endpoints': documented_endpoints,
        'total_schemas': len(schemas)
    }

# Target: >95% documentation quality score
```

---

## 🎯 **Success Criteria & Validation**

### **Documentation Completeness Checklist**
- [ ] **OpenAPI 3.0 Specification**: Complete with all endpoints
- [ ] **Interactive Testing**: Every endpoint testable from Swagger UI
- [ ] **Code Examples**: Python, JavaScript, curl for all endpoints
- [ ] **Error Documentation**: All error responses with examples
- [ ] **Authentication Guide**: Complete JWT flow documentation
- [ ] **WebSocket Documentation**: Real-time API documentation
- [ ] **Getting Started Guide**: 5-minute quick start tutorial
- [ ] **SDK Documentation**: Auto-generated client libraries
- [ ] **Beautiful Design**: Custom styling matching brand
- [ ] **Search Functionality**: Fast search across all documentation

### **Quality Gates**
- [ ] **Documentation Score**: >95% on automated quality checks
- [ ] **All Endpoints**: 100% coverage with working examples
- [ ] **Error Handling**: All error codes documented with solutions
- [ ] **Performance**: Documentation loads in <2 seconds
- [ ] **Mobile Responsive**: Documentation works on all devices
- [ ] **Accessibility**: Screen reader compatible
- [ ] **SEO Optimized**: Proper meta tags and structure

---

## 🚀 **Alex's Documentation Mission**

**Create API documentation so beautiful and comprehensive that developers will want to integrate with Skylapse just to experience the documentation quality.**

### **Your Documentation Goals**:
1. **Showcase Engineering Excellence**: Let the documentation reflect code quality
2. **Developer Delight**: Make integration a joy, not a chore
3. **Professional Standards**: Set the bar for API documentation excellence
4. **Beautiful Design**: Match the interface aesthetics with documentation design

**SUCCESS VISION**: When developers see our API documentation, they should immediately think: *"This is exactly the level of professionalism I want to work with."*

**LET'S CREATE THE MOST BEAUTIFUL API DOCUMENTATION THAT SHOWCASES OUR EXCEPTIONAL ENGINEERING! 📚✨🏔️**

---

*API Documentation Specification by Cooper - September 27, 2025*
*Make the documentation as beautiful as the code! 🚀*
