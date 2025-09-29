# Tech Debt Issue #7: Settings Management Duplication

## 🔥 Priority: HIGH
**Risk Level**: Maintenance Complexity
**Effort**: 6 hours
**Impact**: Settings bugs, data inconsistency, development slowdown

---

## Problem Description

Settings persistence logic is duplicated across multiple modules with different implementations, validation rules, and storage mechanisms. This creates maintenance overhead and potential data inconsistency issues.

## Specific Locations

### **Duplicated Settings Implementations**

```python
# capture/src/api_server.py:29-98 - Implementation #1
class CaptureAPIServer:
    def __init__(self):
        self.settings_file = Path("config/capture_settings.json")
        self.current_settings = {}

    async def load_settings(self):
        """Load settings from JSON file."""
        if self.settings_file.exists():
            with open(self.settings_file, 'r') as f:
                self.current_settings = json.load(f)
        else:
            self.current_settings = self._get_default_settings()

    def _get_default_settings(self):
        """Get default capture settings."""
        return {
            "rotation_degrees": 180,
            "iso": 100,
            "quality": 95,
            "format": "JPEG"
        }

    async def save_settings(self, settings):
        """Save settings to JSON file."""
        self.current_settings.update(settings)
        with open(self.settings_file, 'w') as f:
            json.dump(self.current_settings, f, indent=2)

# processing/src/api_server.py:156-203 - Implementation #2
class ProcessingAPIServer:
    def __init__(self):
        self.config_path = Path("processing.config")  # Different file format!
        self.settings = {}

    def read_settings(self):  # Different method name!
        """Read settings from config file."""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                # Different parsing format!
                for line in f:
                    if '=' in line:
                        key, value = line.strip().split('=', 1)
                        try:
                            self.settings[key] = json.loads(value)  # JSON values in key=value file
                        except json.JSONDecodeError:
                            self.settings[key] = value
        else:
            self.settings = self.default_processing_settings()  # Different default method name!

    def default_processing_settings(self):
        """Get default processing settings."""
        return {
            "hdr_enabled": True,
            "max_jobs": 2,
            "output_quality": 90,  # Different key name for similar concept!
            "cleanup_hours": 24
        }

    def write_settings(self, new_settings):  # Different method name!
        """Write settings to config file."""
        self.settings.update(new_settings)
        with open(self.config_path, 'w') as f:
            for key, value in self.settings.items():
                f.write(f"{key}={json.dumps(value)}\n")  # Custom format!

# backend/src/realtime_server.py:89-134 - Implementation #3
class RealTimeServer:
    def __init__(self):
        # No file persistence at all - only in-memory!
        self.app_settings = {
            "theme": "dark",
            "auto_refresh": True,
            "notification_level": "all"
        }

    def get_user_settings(self):  # Different method name again!
        """Get current user settings."""
        return self.app_settings.copy()

    def update_user_settings(self, updates):  # Different method name!
        """Update user settings in memory only."""
        self.app_settings.update(updates)
        # NO PERSISTENCE - settings lost on restart!
```

## Root Cause Analysis

### **1. Service Isolation**
- Each service developed independently
- No shared settings infrastructure
- Different developers, different approaches

### **2. Format Inconsistency**
- **Capture**: JSON files
- **Processing**: Custom key=value format
- **Backend**: In-memory only (no persistence)

### **3. Interface Inconsistency**
- **Capture**: `load_settings()` / `save_settings()`
- **Processing**: `read_settings()` / `write_settings()`
- **Backend**: `get_user_settings()` / `update_user_settings()`

### **4. Validation Gaps**
- No schema validation across services
- Different validation rules per service
- Silent failures on invalid settings

## Proposed Solution

### **Unified Settings Manager**

```python
# common/settings.py - SHARED SETTINGS FRAMEWORK
import json
import yaml
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import Dict, Any, Type, TypeVar, Generic, Optional
from pathlib import Path
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')

class SettingsStorage(ABC):
    """Abstract base for settings storage backends."""

    @abstractmethod
    async def load(self, key: str) -> Dict[str, Any]:
        """Load settings for given key."""
        pass

    @abstractmethod
    async def save(self, key: str, data: Dict[str, Any]) -> None:
        """Save settings for given key."""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if settings exist for given key."""
        pass

class FileSettingsStorage(SettingsStorage):
    """File-based settings storage with JSON/YAML support."""

    def __init__(self, base_path: Path = Path("config")):
        self.base_path = base_path
        self.base_path.mkdir(exist_ok=True)

    async def load(self, key: str) -> Dict[str, Any]:
        """Load settings from file."""
        file_path = self.base_path / f"{key}.json"

        if not file_path.exists():
            return {}

        try:
            with file_path.open('r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load settings {key}: {e}")
            return {}

    async def save(self, key: str, data: Dict[str, Any]) -> None:
        """Save settings to file."""
        file_path = self.base_path / f"{key}.json"

        try:
            with file_path.open('w') as f:
                json.dump(data, f, indent=2, default=str)
            logger.info(f"Settings saved: {key}")
        except IOError as e:
            logger.error(f"Failed to save settings {key}: {e}")
            raise SettingsError(f"Failed to save settings: {e}")

    async def exists(self, key: str) -> bool:
        """Check if settings file exists."""
        file_path = self.base_path / f"{key}.json"
        return file_path.exists()

class SettingsManager(Generic[T]):
    """Generic settings manager with validation and caching."""

    def __init__(self,
                 settings_class: Type[T],
                 storage: SettingsStorage,
                 key: str):
        self.settings_class = settings_class
        self.storage = storage
        self.key = key
        self._cache: Optional[T] = None
        self._cache_time: Optional[datetime] = None

    async def load(self) -> T:
        """Load settings with caching."""
        if self._cache and self._is_cache_valid():
            return self._cache

        data = await self.storage.load(self.key)

        if not data:
            # No settings exist, use defaults
            instance = self.settings_class()
        else:
            try:
                # Create instance from loaded data
                instance = self.settings_class(**data)
            except TypeError as e:
                logger.error(f"Invalid settings data for {self.key}: {e}")
                # Fallback to defaults
                instance = self.settings_class()

        self._cache = instance
        self._cache_time = datetime.now()
        return instance

    async def save(self, settings: T) -> None:
        """Save settings with validation."""
        if hasattr(settings, '_validate'):
            settings._validate()  # Run validation if available

        data = asdict(settings) if hasattr(settings, '__dataclass_fields__') else settings.__dict__
        await self.storage.save(self.key, data)

        # Update cache
        self._cache = settings
        self._cache_time = datetime.now()

    async def update(self, **kwargs) -> T:
        """Update specific settings fields."""
        current = await self.load()

        # Create updated instance
        current_dict = asdict(current) if hasattr(current, '__dataclass_fields__') else current.__dict__
        current_dict.update(kwargs)

        try:
            updated = self.settings_class(**current_dict)
            await self.save(updated)
            return updated
        except TypeError as e:
            raise SettingsError(f"Invalid settings update: {e}")

    def _is_cache_valid(self, max_age_seconds: int = 30) -> bool:
        """Check if cache is still valid."""
        if not self._cache_time:
            return False
        return (datetime.now() - self._cache_time).seconds < max_age_seconds

class SettingsError(Exception):
    """Settings-related errors."""
    pass

# Service-specific settings classes
@dataclass
class CaptureSettings:
    """Capture service settings with validation."""
    rotation_degrees: int = 180
    iso: int = 100
    quality: int = 95
    format: str = "JPEG"
    preview_width: int = 1920
    preview_height: int = 1440

    def _validate(self):
        """Validate settings values."""
        if self.rotation_degrees not in [0, 90, 180, 270]:
            raise ValueError(f"Invalid rotation: {self.rotation_degrees}")

        if not 50 <= self.iso <= 3200:
            raise ValueError(f"Invalid ISO: {self.iso}")

        if not 1 <= self.quality <= 100:
            raise ValueError(f"Invalid quality: {self.quality}")

        if self.format not in ["JPEG", "PNG", "RAW"]:
            raise ValueError(f"Invalid format: {self.format}")

@dataclass
class ProcessingSettings:
    """Processing service settings with validation."""
    hdr_enabled: bool = True
    max_concurrent_jobs: int = 2
    output_quality: int = 90
    cleanup_hours: int = 24
    temp_dir: str = "/tmp/skylapse"

    def _validate(self):
        """Validate processing settings."""
        if not 1 <= self.max_concurrent_jobs <= 10:
            raise ValueError(f"Invalid max jobs: {self.max_concurrent_jobs}")

        if not 10 <= self.output_quality <= 100:
            raise ValueError(f"Invalid output quality: {self.output_quality}")

        if self.cleanup_hours < 1:
            raise ValueError(f"Invalid cleanup hours: {self.cleanup_hours}")

@dataclass
class UISettings:
    """UI/Backend settings with validation."""
    theme: str = "dark"
    auto_refresh: bool = True
    notification_level: str = "all"
    refresh_interval: int = 5000
    language: str = "en"

    def _validate(self):
        """Validate UI settings."""
        if self.theme not in ["light", "dark", "auto"]:
            raise ValueError(f"Invalid theme: {self.theme}")

        if self.notification_level not in ["none", "error", "warning", "all"]:
            raise ValueError(f"Invalid notification level: {self.notification_level}")

        if not 1000 <= self.refresh_interval <= 60000:
            raise ValueError(f"Invalid refresh interval: {self.refresh_interval}")
```

### **Service Integration**

```python
# capture/src/api_server.py - UPDATED TO USE SHARED SETTINGS
from common.settings import SettingsManager, FileSettingsStorage, CaptureSettings

class CaptureAPIServer:
    def __init__(self):
        storage = FileSettingsStorage(Path("config"))
        self.settings_manager = SettingsManager(
            CaptureSettings,
            storage,
            "capture_settings"
        )

    async def get_settings(self, request):
        """Get current capture settings."""
        settings = await self.settings_manager.load()
        return web.json_response(asdict(settings))

    async def update_settings(self, request):
        """Update capture settings."""
        data = await request.json()

        try:
            updated_settings = await self.settings_manager.update(**data)
            return web.json_response({
                "success": True,
                "settings": asdict(updated_settings)
            })
        except (ValueError, SettingsError) as e:
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=400)

# processing/src/api_server.py - UPDATED TO USE SHARED SETTINGS
from common.settings import SettingsManager, FileSettingsStorage, ProcessingSettings

class ProcessingAPIServer:
    def __init__(self):
        storage = FileSettingsStorage(Path("config"))
        self.settings_manager = SettingsManager(
            ProcessingSettings,
            storage,
            "processing_settings"
        )

    # Same interface as capture service - consistent!
```

## Implementation Steps

### **Step 1: Create Shared Settings Framework (2.5 hours)**
1. Create `common/settings.py` with unified settings management
2. Implement file storage backend
3. Create service-specific settings classes with validation
4. Add comprehensive tests

### **Step 2: Migrate Capture Service (1 hour)**
1. Replace existing settings management with `SettingsManager`
2. Convert settings to `CaptureSettings` dataclass
3. Update API endpoints to use new interface
4. Test settings persistence and validation

### **Step 3: Migrate Processing Service (1 hour)**
1. Replace custom key=value format with JSON
2. Convert to `ProcessingSettings` dataclass
3. Migrate existing settings file
4. Test processing configuration

### **Step 4: Add Backend Settings Persistence (1.5 hours)**
1. Add `UISettings` class for user preferences
2. Implement settings persistence for backend service
3. Create settings API endpoints
4. Test settings survive server restarts

## Testing Strategy

```python
# tests/common/test_settings.py
@pytest.mark.asyncio
async def test_settings_manager_load_and_save():
    """Test basic settings load and save functionality."""
    storage = FileSettingsStorage(Path("/tmp/test_settings"))
    manager = SettingsManager(CaptureSettings, storage, "test")

    # Load default settings
    settings = await manager.load()
    assert settings.rotation_degrees == 180
    assert settings.iso == 100

    # Update settings
    settings.rotation_degrees = 270
    await manager.save(settings)

    # Load again and verify persistence
    reloaded = await manager.load()
    assert reloaded.rotation_degrees == 270

@pytest.mark.asyncio
async def test_settings_validation():
    """Test that invalid settings are rejected."""
    storage = FileSettingsStorage(Path("/tmp/test_settings"))
    manager = SettingsManager(CaptureSettings, storage, "test")

    with pytest.raises(SettingsError):
        await manager.update(rotation_degrees=45)  # Invalid rotation

    with pytest.raises(SettingsError):
        await manager.update(iso=10000)  # Invalid ISO
```

## Dependencies

**Enables These Issues**:
- Issue #3 (Configuration Management) - Settings are part of configuration
- Issue #29 (Config Schema Validation) - Settings framework includes validation

**Enhanced By**:
- Issue #1 (Error Handling) - Better error responses for settings failures

---

*This unified settings system eliminates duplication and provides consistent, validated settings management across all services.*
