# Tech Debt Issue #31: Test File Coverage Gaps

## 🧪 Priority: HIGH
**Risk Level**: Quality & Reliability
**Effort**: 16 hours
**Impact**: Undetected bugs, refactoring risks, deployment confidence

---

## Problem Description

Critical components lack comprehensive test coverage, creating significant risk for bugs and making refactoring dangerous. Several key modules have no tests at all, while others have incomplete coverage of edge cases and error scenarios.

## Specific Locations

### **Files With No Tests**
- `backend/src/realtime_server.py` - **0% coverage**
- `frontend/src/services/RealTimeClient.ts` - **0% coverage**
- `processing/src/image_processor.py` fallback logic - **Untested**
- `capture/src/schedule_executor.py` - **Minimal coverage**

### **Critical Untested Code Paths**

```python
# backend/src/realtime_server.py - NO TESTS FOUND
class RealTimeServer:
    async def handle_websocket(self, request):
        """Handle WebSocket connections - UNTESTED"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        # Complex connection management logic - NO TESTS
        self.active_connections[ws] = {
            'connected_at': datetime.now(),
            'user_id': request.headers.get('Authorization'),  # Potential security issue
            'subscriptions': set()
        }

        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                await self._handle_message(ws, json.loads(msg.data))  # Can throw - UNTESTED
            elif msg.type == aiohttp.WSMsgType.ERROR:
                logger.error(f'WebSocket error: {ws.exception()}')  # Error handling - UNTESTED

        # Cleanup logic - UNTESTED
        del self.active_connections[ws]
        return ws

    async def _handle_message(self, ws, message):
        """Message handling logic - UNTESTED"""
        msg_type = message.get('type')

        if msg_type == 'subscribe':
            # Subscription logic - UNTESTED
            topic = message.get('topic')
            self.active_connections[ws]['subscriptions'].add(topic)

        elif msg_type == 'camera_command':
            # Camera control via WebSocket - UNTESTED & DANGEROUS
            command = message.get('command')
            params = message.get('params', {})

            # Direct command execution - NO VALIDATION TESTS
            if command == 'capture':
                await self._trigger_capture(params)  # UNTESTED
            elif command == 'change_settings':
                await self._update_camera_settings(params)  # UNTESTED
```

### **Frontend Real-Time Client - No Tests**

```typescript
// frontend/src/services/RealTimeClient.ts - NO TESTS FOUND
export class RealTimeClient {
    private socket: Socket | null = null
    private reconnectAttempts = 0
    private maxReconnectAttempts = 5

    connect(url: string): Promise<void> {
        // Connection logic - UNTESTED
        return new Promise((resolve, reject) => {
            this.socket = io(url, {
                transports: ['websocket'],
                timeout: 10000
            })

            this.socket.on('connect', () => {
                this.reconnectAttempts = 0  // Reset counter - UNTESTED
                resolve()
            })

            this.socket.on('disconnect', (reason) => {
                // Reconnection logic - UNTESTED
                if (reason === 'io server disconnect') {
                    // Server initiated disconnect - should not reconnect
                    return
                }

                this.attemptReconnect()  // UNTESTED RECONNECTION
            })

            this.socket.on('error', (error) => {
                // Error handling - UNTESTED
                if (this.reconnectAttempts >= this.maxReconnectAttempts) {
                    reject(new Error(`Failed to connect after ${this.maxReconnectAttempts} attempts`))
                }
            })
        })
    }

    private attemptReconnect(): void {
        // Complex reconnection logic - COMPLETELY UNTESTED
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            this.emit('maxReconnectAttemptsReached')
            return
        }

        const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000)

        setTimeout(() => {
            this.reconnectAttempts++
            this.connect(this.lastUrl)  // UNTESTED - lastUrl might be undefined
        }, delay)
    }
}
```

### **Image Processing Fallback Logic - Untested**

```python
# processing/src/image_processor.py:430-479 - FALLBACK LOGIC UNTESTED
async def _fallback_hdr_merge(self, image_paths: List[str], output_path: str) -> str:
    """HDR merge fallback when OpenCV fails - NO TESTS"""

    if not PIL_AVAILABLE:
        # Ultimate fallback: copy middle exposure - UNTESTED
        middle_idx = len(image_paths) // 2
        shutil.copy2(image_paths[middle_idx], output_path)
        logger.warning("Using single image fallback for HDR")
        return output_path

    try:
        # PIL-based HDR merge attempt - UNTESTED
        from PIL import Image, ImageEnhance

        images = []
        for path in image_paths:
            img = Image.open(path)
            images.append(img)

        # Exposure blending algorithm - COMPLEX & UNTESTED
        base_img = images[len(images) // 2]  # Middle exposure as base

        for i, img in enumerate(images):
            if i == len(images) // 2:
                continue

            # Blend based on exposure difference - UNTESTED ALGORITHM
            blend_ratio = self._calculate_blend_ratio(i, len(images))
            base_img = Image.blend(base_img, img, blend_ratio)

        base_img.save(output_path, quality=95)
        return output_path

    except Exception as e:
        # Double fallback - UNTESTED
        logger.error(f"PIL HDR fallback failed: {e}")
        middle_idx = len(image_paths) // 2
        shutil.copy2(image_paths[middle_idx], output_path)
        return output_path

def _calculate_blend_ratio(self, index: int, total: int) -> float:
    """Calculate blend ratio for HDR - UNTESTED MATH"""
    # Complex mathematical algorithm - NO TESTS VERIFY CORRECTNESS
    center = total // 2
    distance = abs(index - center)
    return 1.0 / (1.0 + distance * 0.3)  # Magic numbers - UNTESTED
```

## Testing Strategy Requirements

### **Priority 1: Backend Real-Time Server Tests (6 hours)**

```python
# tests/backend/test_realtime_server.py - NEW COMPREHENSIVE TESTS
import pytest
import asyncio
import aiohttp
from aiohttp import web, WSMsgType
from unittest.mock import Mock, patch, AsyncMock
from backend.src.realtime_server import RealTimeServer

@pytest.fixture
async def server():
    """Create test real-time server."""
    server = RealTimeServer()
    await server.initialize()
    return server

@pytest.fixture
async def websocket_client(aiohttp_client, server):
    """Create test WebSocket client."""
    app = server.create_app()
    client = await aiohttp_client(app)
    return client

class TestWebSocketConnection:
    async def test_websocket_connection_lifecycle(self, websocket_client):
        """Test WebSocket connection and disconnection."""
        async with websocket_client.ws_connect('/ws') as ws:
            # Test connection established
            assert ws.closed is False

            # Test connection tracking
            # server should have this connection in active_connections

        # Test connection cleanup after close
        assert ws.closed is True

    async def test_websocket_message_handling(self, websocket_client):
        """Test WebSocket message handling."""
        async with websocket_client.ws_connect('/ws') as ws:
            # Test subscription message
            await ws.send_json({
                'type': 'subscribe',
                'topic': 'system_status'
            })

            response = await ws.receive()
            assert response.type == WSMsgType.TEXT
            data = json.loads(response.data)
            assert data.get('type') == 'subscription_confirmed'

    async def test_websocket_error_handling(self, websocket_client):
        """Test WebSocket error scenarios."""
        async with websocket_client.ws_connect('/ws') as ws:
            # Test invalid message format
            await ws.send_str("invalid json")

            response = await ws.receive()
            assert response.type == WSMsgType.TEXT
            error_data = json.loads(response.data)
            assert error_data.get('type') == 'error'
            assert 'invalid message format' in error_data.get('message', '').lower()

    async def test_websocket_camera_commands(self, websocket_client):
        """Test camera command handling via WebSocket."""
        with patch('backend.src.realtime_server.RealTimeServer._trigger_capture') as mock_capture:
            mock_capture.return_value = AsyncMock()

            async with websocket_client.ws_connect('/ws') as ws:
                await ws.send_json({
                    'type': 'camera_command',
                    'command': 'capture',
                    'params': {'iso': 200}
                })

                # Verify capture was triggered with correct params
                mock_capture.assert_called_once_with({'iso': 200})

    async def test_websocket_security_validation(self, websocket_client):
        """Test WebSocket security and authorization."""
        # Test unauthorized access
        async with websocket_client.ws_connect('/ws') as ws:
            await ws.send_json({
                'type': 'camera_command',
                'command': 'format_storage'  # Dangerous command
            })

            response = await ws.receive()
            error_data = json.loads(response.data)
            assert error_data.get('type') == 'error'
            assert 'unauthorized' in error_data.get('message', '').lower()

    async def test_websocket_connection_limits(self, websocket_client, server):
        """Test connection limits and resource management."""
        connections = []

        # Create maximum allowed connections
        for i in range(server.max_connections):
            ws = await websocket_client.ws_connect('/ws')
            connections.append(ws)

        # Try to create one more connection - should fail
        with pytest.raises(aiohttp.WSServerHandshakeError):
            await websocket_client.ws_connect('/ws')

        # Clean up
        for ws in connections:
            await ws.close()
```

### **Priority 2: Frontend Real-Time Client Tests (4 hours)**

```typescript
// tests/services/RealTimeClient.test.ts - NEW COMPREHENSIVE TESTS
import { RealTimeClient } from '../../src/services/RealTimeClient'
import { io } from 'socket.io-client'
import { jest } from '@jest/globals'

// Mock Socket.IO
jest.mock('socket.io-client')
const mockIo = io as jest.MockedFunction<typeof io>

describe('RealTimeClient', () => {
    let client: RealTimeClient
    let mockSocket: any

    beforeEach(() => {
        mockSocket = {
            on: jest.fn(),
            emit: jest.fn(),
            disconnect: jest.fn(),
            connected: false
        }
        mockIo.mockReturnValue(mockSocket)
        client = new RealTimeClient()
    })

    afterEach(() => {
        jest.clearAllMocks()
    })

    describe('Connection Management', () => {
        test('connects to server successfully', async () => {
            // Setup success scenario
            mockSocket.on.mockImplementation((event, callback) => {
                if (event === 'connect') {
                    setTimeout(callback, 0)
                }
            })

            const promise = client.connect('http://localhost:8081')

            expect(mockIo).toHaveBeenCalledWith('http://localhost:8081', {
                transports: ['websocket'],
                timeout: 10000
            })

            await expect(promise).resolves.toBeUndefined()
        })

        test('handles connection errors', async () => {
            mockSocket.on.mockImplementation((event, callback) => {
                if (event === 'error') {
                    setTimeout(() => callback(new Error('Connection failed')), 0)
                }
            })

            await expect(client.connect('http://localhost:8081'))
                .rejects.toThrow('Failed to connect')
        })

        test('handles reconnection on disconnect', async () => {
            const reconnectSpy = jest.spyOn(client as any, 'attemptReconnect')

            mockSocket.on.mockImplementation((event, callback) => {
                if (event === 'disconnect') {
                    setTimeout(() => callback('transport close'), 0)
                }
            })

            await client.connect('http://localhost:8081')

            expect(reconnectSpy).toHaveBeenCalled()
        })

        test('respects maximum reconnection attempts', async () => {
            const maxAttempts = 5
            let reconnectCount = 0

            const originalConnect = client.connect.bind(client)
            client.connect = jest.fn().mockImplementation(() => {
                reconnectCount++
                if (reconnectCount <= maxAttempts) {
                    return Promise.reject(new Error('Connection failed'))
                }
                return originalConnect('http://localhost:8081')
            })

            await expect(client.connect('http://localhost:8081'))
                .rejects.toThrow('Failed to connect after 5 attempts')
        })
    })

    describe('Message Handling', () => {
        test('emits received messages correctly', () => {
            const messageHandler = jest.fn()
            client.on('system_status', messageHandler)

            // Simulate receiving a message
            const mockData = { cpu: 50, memory: 75 }
            mockSocket.on.mockImplementation((event, callback) => {
                if (event === 'system_status') {
                    setTimeout(() => callback(mockData), 0)
                }
            })

            // Trigger the mock
            const callback = mockSocket.on.mock.calls.find(call => call[0] === 'system_status')[1]
            callback(mockData)

            expect(messageHandler).toHaveBeenCalledWith(mockData)
        })
    })
})
```

### **Priority 3: Image Processing Fallback Tests (3 hours)**

```python
# tests/processing/test_image_processor_fallbacks.py - NEW FALLBACK TESTS
import pytest
import tempfile
import shutil
from unittest.mock import patch, Mock
from pathlib import Path
from processing.src.image_processor import ImageProcessor

@pytest.fixture
def temp_images():
    """Create temporary test images."""
    temp_dir = tempfile.mkdtemp()

    # Create mock image files
    image_paths = []
    for i in range(3):
        image_path = Path(temp_dir) / f"test_image_{i}.jpg"
        image_path.write_bytes(b"mock_image_data")
        image_paths.append(str(image_path))

    yield image_paths

    # Cleanup
    shutil.rmtree(temp_dir)

class TestImageProcessorFallbacks:
    def test_hdr_fallback_when_opencv_unavailable(self, temp_images):
        """Test HDR fallback when OpenCV is not available."""
        processor = ImageProcessor()

        with patch.dict('sys.modules', {'cv2': None}):
            with patch('processing.src.image_processor.PIL_AVAILABLE', False):
                output_path = "/tmp/test_output.jpg"

                result = await processor._fallback_hdr_merge(temp_images, output_path)

                # Should use middle image as fallback
                assert Path(result).exists()

                # Verify it's a copy of the middle image
                middle_path = temp_images[len(temp_images) // 2]
                assert Path(output_path).read_bytes() == Path(middle_path).read_bytes()

    def test_hdr_pil_fallback_success(self, temp_images):
        """Test PIL-based HDR fallback when OpenCV fails."""
        processor = ImageProcessor()

        # Mock PIL to simulate successful processing
        mock_image = Mock()
        mock_image.save = Mock()

        with patch('processing.src.image_processor.PIL_AVAILABLE', True):
            with patch('PIL.Image.open', return_value=mock_image):
                with patch('PIL.Image.blend', return_value=mock_image):
                    output_path = "/tmp/test_output.jpg"

                    result = await processor._fallback_hdr_merge(temp_images, output_path)

                    assert result == output_path
                    mock_image.save.assert_called_once_with(output_path, quality=95)

    def test_blend_ratio_calculation(self):
        """Test HDR blend ratio calculation."""
        processor = ImageProcessor()

        # Test blend ratio for different positions
        assert processor._calculate_blend_ratio(0, 5) == 1.0 / (1.0 + 2 * 0.3)  # Distance from center = 2
        assert processor._calculate_blend_ratio(2, 5) == 1.0  # Center position
        assert processor._calculate_blend_ratio(4, 5) == 1.0 / (1.0 + 2 * 0.3)  # Distance from center = 2

    def test_double_fallback_on_pil_failure(self, temp_images):
        """Test ultimate fallback when PIL also fails."""
        processor = ImageProcessor()

        with patch('processing.src.image_processor.PIL_AVAILABLE', True):
            with patch('PIL.Image.open', side_effect=Exception("PIL failed")):
                output_path = "/tmp/test_output.jpg"

                result = await processor._fallback_hdr_merge(temp_images, output_path)

                # Should fall back to copying middle image
                assert Path(result).exists()
                middle_path = temp_images[len(temp_images) // 2]
                assert Path(output_path).read_bytes() == Path(middle_path).read_bytes()
```

### **Priority 4: Schedule Executor Tests (3 hours)**

```python
# tests/capture/test_schedule_executor.py - NEW SCHEDULE TESTS
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch
from capture.src.schedule_executor import ScheduleExecutor
from capture.src.schedule_models import ScheduleRule, CaptureSchedule

@pytest.fixture
def executor():
    """Create test schedule executor."""
    return ScheduleExecutor()

class TestScheduleExecutor:
    @pytest.mark.asyncio
    async def test_schedule_execution_timing(self, executor):
        """Test that schedules execute at correct times."""
        capture_mock = AsyncMock()
        executor.capture_service = capture_mock

        # Create schedule for 1 second from now
        future_time = datetime.now() + timedelta(seconds=1)
        schedule = CaptureSchedule(
            id="test_schedule",
            start_time=future_time.time(),
            end_time=(future_time + timedelta(hours=1)).time(),
            interval_minutes=60
        )

        executor.add_schedule(schedule)

        # Wait for execution
        await asyncio.sleep(1.1)

        # Verify capture was triggered
        capture_mock.manual_capture.assert_called_once()

    @pytest.mark.asyncio
    async def test_schedule_error_handling(self, executor):
        """Test error handling during schedule execution."""
        # Mock capture service to raise an error
        capture_mock = AsyncMock()
        capture_mock.manual_capture.side_effect = Exception("Capture failed")
        executor.capture_service = capture_mock

        schedule = CaptureSchedule(
            id="error_schedule",
            start_time=datetime.now().time(),
            end_time=(datetime.now() + timedelta(hours=1)).time(),
            interval_minutes=1
        )

        # Should not raise exception, should handle gracefully
        try:
            executor.add_schedule(schedule)
            await asyncio.sleep(0.1)  # Brief wait for execution attempt
        except Exception:
            pytest.fail("Schedule executor should handle capture errors gracefully")
```

## Implementation Steps

### **Step 1: Backend Real-Time Tests (6 hours)**
1. Create comprehensive WebSocket connection tests
2. Test message handling and error scenarios
3. Test security and authorization
4. Test connection limits and cleanup

### **Step 2: Frontend Real-Time Tests (4 hours)**
1. Create RealTimeClient connection tests
2. Test reconnection logic and limits
3. Test message handling and event emission
4. Mock Socket.IO for isolated testing

### **Step 3: Image Processing Tests (3 hours)**
1. Test HDR fallback scenarios
2. Test PIL fallback when OpenCV unavailable
3. Test blend ratio calculations
4. Test error handling in fallback paths

### **Step 4: Schedule Executor Tests (3 hours)**
1. Test schedule timing accuracy
2. Test error handling during execution
3. Test schedule lifecycle management
4. Test concurrent schedule handling

## Dependencies

**Required For**:
- All refactoring efforts - Need tests before major changes
- Issue #30 (Dependency Injection) - Need tests to validate DI changes
- Production deployment confidence

**Enhanced By**:
- Issue #32 (Mock Camera) - Better mocks improve test quality

---

*Comprehensive test coverage is essential for safe refactoring and reliable production deployments.*
