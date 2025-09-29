# Tech Debt Issue #3: Inconsistent Configuration Management

## ⚠️ Priority: CRITICAL
**Risk Level**: System Instability
**Effort**: 8 hours
**Impact**: Configuration bugs, deployment failures, inconsistent behavior

---

## Problem Description

Each service implements its own configuration loading with different patterns, file formats, and validation approaches. This leads to configuration bugs, inconsistent behavior across services, and deployment complexity.

## Specific Locations

### **Configuration Inconsistencies**

```python
# capture/src/config_manager.py - YAML-based configuration
import yaml
from pathlib import Path

class ConfigManager:
    def __init__(self, config_file: str = "config/capture.yaml"):
        self.config_file = config_file
        self.config_data = {}

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(self.config_file, 'r') as f:
                return yaml.safe_load(f)  # YAML format
        except FileNotFoundError:
            logger.warning(f"Config file {self.config_file} not found, using defaults")
            return self._get_defaults()  # Custom defaults method
        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error: {e}")
            raise ConfigurationError(f"Invalid YAML: {e}")

    def _get_defaults(self) -> Dict[str, Any]:
        """Return default configuration."""
        return {
            "camera": {"default_iso": 100, "default_quality": 95},
            "api": {"host": "0.0.0.0", "port": 8080}
        }

# processing/src/config_manager.py - JSON-based configuration
import json
from typing import Dict, Any

class ProcessingConfig:  # Different class name!
    def __init__(self, config_path: str = "config.json"):  # Different parameter name!
        self.config_path = config_path

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file."""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)  # JSON format instead of YAML
        except FileNotFoundError:
            print(f"Config file {self.config_path} not found")  # print() instead of logger!
            return {}  # Empty dict instead of defaults!
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")  # No custom exception!
            return {}  # Returns empty on error instead of raising

    def get_setting(self, key: str, default=None):  # Different interface!
        """Get specific setting with dot notation."""
        config = self.load_config()  # Reloads file every time!
        keys = key.split('.')
        value = config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

# backend/src/realtime_server.py - Environment variables only
import os

class RealTimeServerConfig:  # Yet another class name!
    def __init__(self):
        pass  # No file-based config at all!

    @staticmethod
    def get_config():
        """Load configuration from environment variables only."""
        return {
            "host": os.getenv("RT_HOST", "localhost"),  # Different env var pattern
            "port": int(os.getenv("RT_PORT", "8082")),  # No validation of int conversion!
            "jwt_secret": os.getenv("JWT_SECRET", "default_secret"),  # Security issue!
            "cors_origins": os.getenv("CORS_ORIGINS", "*").split(",")  # String splitting without validation
        }
```

## Root Cause Analysis

### **1. Service-First Development**
- Each service developed independently
- No shared configuration library established
- Different developers chose different approaches

### **2. Inconsistent Requirements**
- Capture service needs complex camera settings (YAML suited)
- Processing service needs simple key-value pairs (JSON chosen)
- Backend service needs environment-based config (direct env vars)

### **3. Missing Standards**
- No configuration schema validation
- No standard error handling
- No environment variable naming conventions
- No default value strategies

### **4. Deployment Complexity**
- Multiple config formats to manage
- Different override strategies per service
- No unified configuration validation

## Configuration Problems in Practice

### **Problem 1: Production Deployment Failures**
```yaml
# capture/config/capture.yaml - Works in development
camera:
  default_iso: 100
  rotation_degrees: 180

# Production deployment breaks because:
# 1. File path is hardcoded
# 2. No environment variable override
# 3. No validation of camera settings
```

### **Problem 2: Environment Inconsistencies**
```bash
# Development works:
RT_HOST=localhost
RT_PORT=8082

# Production fails:
REALTIME_HOST=production-host  # Different env var name!
REALTIME_PORT=8082            # Service doesn't recognize this name
```

### **Problem 3: Configuration Drift**
```python
# Capture service has camera.default_iso
# Processing service has processing.iso_setting
# Same setting, different keys, no synchronization
```

## Proposed Solution

### **Unified Configuration Framework**

```python
# common/config.py - UNIFIED CONFIGURATION SYSTEM
import json
import yaml
import os
from typing import Any, Dict, Optional, Type, Union
from dataclasses import dataclass, field
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

@dataclass
class BaseConfig:
    """Base configuration class that all service configs inherit from."""

    # Common settings all services need
    host: str = field(default="0.0.0.0")
    port: int = field(default=8080)
    debug: bool = field(default=False)
    log_level: str = field(default="INFO")

    @classmethod
    def load(cls,
             config_file: Optional[str] = None,
             env_prefix: Optional[str] = None) -> 'BaseConfig':
        """Load configuration from file + environment variables."""

        config_data = {}

        # 1. Load from file if provided
        if config_file:
            config_data = cls._load_from_file(config_file)

        # 2. Override with environment variables
        if env_prefix:
            config_data.update(cls._load_from_env(env_prefix))

        # 3. Validate and create instance
        return cls._create_instance(config_data)

    @staticmethod
    def _load_from_file(config_file: str) -> Dict[str, Any]:
        """Load configuration from YAML or JSON file."""
        config_path = Path(config_file)

        if not config_path.exists():
            logger.warning(f"Config file {config_file} not found, using defaults")
            return {}

        try:
            with config_path.open('r') as f:
                if config_path.suffix.lower() in ['.yaml', '.yml']:
                    return yaml.safe_load(f) or {}
                elif config_path.suffix.lower() == '.json':
                    return json.load(f)
                else:
                    raise ValueError(f"Unsupported config format: {config_path.suffix}")

        except (yaml.YAMLError, json.JSONDecodeError) as e:
            logger.error(f"Failed to parse {config_file}: {e}")
            raise ConfigurationError(f"Invalid configuration file {config_file}: {e}")

    @classmethod
    def _load_from_env(cls, prefix: str) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        env_config = {}

        for field_name, field_info in cls.__dataclass_fields__.items():
            env_var = f"{prefix}_{field_name.upper()}"
            env_value = os.getenv(env_var)

            if env_value is not None:
                # Type conversion based on field type
                field_type = field_info.type
                try:
                    if field_type == bool:
                        env_config[field_name] = env_value.lower() in ('true', '1', 'yes', 'on')
                    elif field_type == int:
                        env_config[field_name] = int(env_value)
                    elif field_type == float:
                        env_config[field_name] = float(env_value)
                    else:
                        env_config[field_name] = env_value
                except ValueError as e:
                    logger.error(f"Invalid value for {env_var}={env_value}: {e}")
                    raise ConfigurationError(f"Invalid environment variable {env_var}={env_value}")

        return env_config

    @classmethod
    def _create_instance(cls, config_data: Dict[str, Any]) -> 'BaseConfig':
        """Create and validate configuration instance."""
        try:
            instance = cls(**config_data)
            instance._validate()
            return instance
        except TypeError as e:
            raise ConfigurationError(f"Invalid configuration data: {e}")

    def _validate(self):
        """Validate configuration values. Override in subclasses."""
        if self.port < 1 or self.port > 65535:
            raise ConfigurationError(f"Invalid port number: {self.port}")

        if self.log_level not in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
            raise ConfigurationError(f"Invalid log level: {self.log_level}")

class ConfigurationError(Exception):
    """Configuration-related errors."""
    pass

# Service-specific configurations
@dataclass
class CaptureConfig(BaseConfig):
    """Configuration for capture service."""

    # Service-specific settings
    camera_model: str = field(default="arducam_imx519")
    default_iso: int = field(default=100)
    default_quality: int = field(default=95)
    rotation_degrees: int = field(default=180)
    preview_width: int = field(default=1920)
    preview_height: int = field(default=1440)
    capture_timeout: float = field(default=10.0)

    def _validate(self):
        """Validate capture-specific settings."""
        super()._validate()

        if self.default_iso < 50 or self.default_iso > 3200:
            raise ConfigurationError(f"Invalid ISO: {self.default_iso}")

        if self.default_quality < 1 or self.default_quality > 100:
            raise ConfigurationError(f"Invalid quality: {self.default_quality}")

        if self.rotation_degrees not in [0, 90, 180, 270]:
            raise ConfigurationError(f"Invalid rotation: {self.rotation_degrees}")

@dataclass
class ProcessingConfig(BaseConfig):
    """Configuration for processing service."""

    # Processing-specific settings
    max_concurrent_jobs: int = field(default=2)
    temp_dir: str = field(default="/tmp/skylapse")
    hdr_enabled: bool = field(default=True)
    video_bitrate: int = field(default=5000)
    cleanup_after_hours: int = field(default=24)

    def _validate(self):
        """Validate processing-specific settings."""
        super()._validate()

        if self.max_concurrent_jobs < 1 or self.max_concurrent_jobs > 10:
            raise ConfigurationError(f"Invalid concurrent jobs: {self.max_concurrent_jobs}")

        if self.video_bitrate < 1000 or self.video_bitrate > 50000:
            raise ConfigurationError(f"Invalid bitrate: {self.video_bitrate}")

@dataclass
class BackendConfig(BaseConfig):
    """Configuration for backend/realtime service."""

    # Backend-specific settings
    jwt_secret: str = field(default="")  # Must be provided
    cors_origins: list = field(default_factory=lambda: ["http://localhost:3000"])
    websocket_timeout: float = field(default=30.0)
    max_connections: int = field(default=100)

    def _validate(self):
        """Validate backend-specific settings."""
        super()._validate()

        if not self.jwt_secret or len(self.jwt_secret) < 32:
            raise ConfigurationError("JWT secret must be at least 32 characters long")

        if self.max_connections < 1 or self.max_connections > 10000:
            raise ConfigurationError(f"Invalid max connections: {self.max_connections}")
```

### **Configuration Files**

```yaml
# config/capture.yaml - STANDARDIZED FORMAT
# Capture Service Configuration
host: "0.0.0.0"
port: 8080
debug: false
log_level: "INFO"

# Camera settings
camera_model: "arducam_imx519"
default_iso: 100
default_quality: 95
rotation_degrees: 180
preview_width: 1920
preview_height: 1440
capture_timeout: 10.0
```

```yaml
# config/processing.yaml - SAME FORMAT
# Processing Service Configuration
host: "0.0.0.0"
port: 8081
debug: false
log_level: "INFO"

# Processing settings
max_concurrent_jobs: 2
temp_dir: "/tmp/skylapse"
hdr_enabled: true
video_bitrate: 5000
cleanup_after_hours: 24
```

### **Environment Variable Standards**

```bash
# .env.production - CONSISTENT NAMING
# Capture service
SKYLAPSE_CAPTURE_HOST=0.0.0.0
SKYLAPSE_CAPTURE_PORT=8080
SKYLAPSE_CAPTURE_DEFAULT_ISO=100
SKYLAPSE_CAPTURE_ROTATION_DEGREES=180

# Processing service
SKYLAPSE_PROCESSING_HOST=0.0.0.0
SKYLAPSE_PROCESSING_PORT=8081
SKYLAPSE_PROCESSING_MAX_CONCURRENT_JOBS=4

# Backend service
SKYLAPSE_BACKEND_HOST=0.0.0.0
SKYLAPSE_BACKEND_PORT=8082
SKYLAPSE_BACKEND_JWT_SECRET=your_super_secure_secret_here
SKYLAPSE_BACKEND_CORS_ORIGINS=https://your-domain.com
```

## Implementation Steps

### **Step 1: Create Common Config Framework (3 hours)**
1. Create `common/config.py` with unified configuration classes
2. Add comprehensive validation for each service
3. Add thorough unit tests

### **Step 2: Migrate Capture Service (1.5 hours)**
1. Replace `ConfigManager` with `CaptureConfig.load()`
2. Update all config access points
3. Test configuration loading and validation

### **Step 3: Migrate Processing Service (1.5 hours)**
1. Replace `ProcessingConfig` class with new framework
2. Convert JSON config files to YAML for consistency
3. Test processing configuration

### **Step 4: Migrate Backend Service (2 hours)**
1. Add file-based config support to backend
2. Maintain environment variable compatibility
3. Add proper JWT secret validation

## Testing Strategy

```python
# tests/common/test_config.py
def test_capture_config_from_file():
    """Test loading capture config from YAML file."""
    config_file = create_temp_config({
        'host': '127.0.0.1',
        'port': 8080,
        'default_iso': 200
    })

    config = CaptureConfig.load(config_file=config_file)

    assert config.host == '127.0.0.1'
    assert config.port == 8080
    assert config.default_iso == 200

def test_config_environment_override():
    """Test that environment variables override file values."""
    with patch.dict(os.environ, {
        'SKYLAPSE_CAPTURE_PORT': '9090',
        'SKYLAPSE_CAPTURE_DEBUG': 'true'
    }):
        config = CaptureConfig.load(env_prefix='SKYLAPSE_CAPTURE')

        assert config.port == 9090
        assert config.debug is True

def test_config_validation_errors():
    """Test that invalid configurations raise appropriate errors."""
    with pytest.raises(ConfigurationError, match="Invalid ISO"):
        CaptureConfig(default_iso=5000)  # Too high

    with pytest.raises(ConfigurationError, match="Invalid port"):
        CaptureConfig(port=99999)  # Out of range
```

## Dependencies

**Enables These Issues**:
- Issue #2 (CORS Configuration) - Uses same environment variable patterns
- Issue #5 (JWT Secret) - Proper validation and environment handling
- Issue #42 (Environment Variables) - Comprehensive env var framework

## Expected Results

### **Configuration Consistency**
- **Single Format**: All services use YAML + environment variables
- **Standard Validation**: All configs validated with clear error messages
- **Unified Interface**: Same loading pattern across all services

### **Deployment Simplification**
- **Environment-First**: Production uses environment variables
- **File Fallback**: Development can use config files
- **Validation**: Startup fails fast with clear error messages

---

*This unified configuration system eliminates inconsistencies and provides a solid foundation for all other configuration-related improvements.*
