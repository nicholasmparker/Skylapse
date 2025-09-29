# Tech Debt Issue #4: Real-Time Client Confusion

## ⚠️ Priority: CRITICAL
**Risk Level**: System Instability
**Effort**: 6 hours
**Impact**: Real-time features may fail silently, circular dependencies

---

## Problem Description

The real-time client architecture has circular dependencies, undefined references, and confusing multiple implementations that create silent failures and make the system unreliable.

## Specific Locations

### **Primary Issues**
- **File**: `frontend/src/hooks/useRealTimeData.ts:478`
- **Line**: References undefined `useRealTimeClient`
- **File**: `frontend/src/services/RealTimeClient.ts`
- **Issue**: Circular import dependencies

### **Circular Dependency Problem**

```typescript
// frontend/src/hooks/useRealTimeData.ts:478 - UNDEFINED REFERENCE
import { useConnectionState } from './useConnectionState'
import { useRealTimeConnection } from './useRealTimeConnection'
// Missing import causes runtime error

export function useRealTimeData() {
    // ... 400+ lines of complex state management

    // LINE 478 - CRITICAL ERROR
    const realTimeClient = useRealTimeClient()  // ❌ UNDEFINED - Not imported!
    const PRODUCTION_REALTIME_CONFIG = PRODUCTION_REALTIME_CONFIG  // ❌ UNDEFINED

    // This code will crash at runtime but TypeScript doesn't catch it
    // because of the complex dependency graph
}

// frontend/src/services/RealTimeClient.ts - CIRCULAR IMPORT
import { useRealTimeData } from '../hooks/useRealTimeData'  // ❌ CIRCULAR!

export class RealTimeClient {
    constructor() {
        // Uses useRealTimeData hook from inside a service class
        // This creates a React hook being called outside component lifecycle
        this.dataHook = useRealTimeData()  // ❌ BREAKS RULES OF HOOKS
    }
}

// frontend/src/hooks/useRealTimeClient.ts - MISSING FILE
// This file is referenced but doesn't exist!
// Causes runtime errors when useRealTimeData tries to import it
```

### **Multiple Conflicting Implementations**

```typescript
// frontend/src/services/RealTimeService.ts - Implementation #1
export class RealTimeService {
    private socket: Socket | null = null
    private connectionState: ConnectionState = 'disconnected'

    connect() {
        this.socket = io('http://localhost:8081', {
            transports: ['websocket']
        })
    }
}

// frontend/src/services/RealTimeClient.ts - Implementation #2
export class RealTimeClient {
    private ws: WebSocket | null = null  // Different transport!
    private status: string = 'offline'   // Different state naming!

    connect() {
        this.ws = new WebSocket('ws://localhost:8081')  // Different URL format!
    }
}

// frontend/src/hooks/useRealTimeConnection.ts - Implementation #3
export function useRealTimeConnection() {
    const [connected, setConnected] = useState(false)  // Different state type!

    useEffect(() => {
        // Yet another Socket.IO implementation
        const socket = io('ws://localhost:8082', {  // Different port!
            autoConnect: true
        })
    }, [])
}
```

### **Configuration Chaos**

```typescript
// frontend/src/hooks/useRealTimeData.ts:219 - Hardcoded config
const PRODUCTION_REALTIME_CONFIG = {
    wsUrl: 'ws://production-host:8081'  // Hardcoded production URL!
}

// frontend/src/services/RealTimeClient.ts:31 - Different config pattern
export class RealTimeClient {
    constructor(config: RealTimeClientConfig) {
        // Expects 'wsUrl' property
        this.wsUrl = config.wsUrl  // ❌ Property doesn't exist on type
    }
}

// frontend/src/hooks/useRealTimeClient.ts - Would be missing config
const client = new RealTimeClient({
    // Missing required wsUrl property
    apiUrl: 'http://localhost:8081'  // Wrong property name
})
```

## Root Cause Analysis

### **1. Architectural Confusion**
- **No Clear Boundaries**: Services, hooks, and clients all mixed together
- **Multiple Transport Methods**: Socket.IO, WebSocket, HTTP polling all used
- **Inconsistent State Management**: Different state shapes across implementations

### **2. Development Iteration Issues**
- **Rapid Prototyping**: Multiple approaches tried without cleanup
- **Copy-Paste Development**: Similar functionality duplicated
- **Missing Refactoring**: Old code not removed when new approaches added

### **3. Import/Export Problems**
- **Circular Dependencies**: Files import each other in loops
- **Missing Files**: References to non-existent modules
- **TypeScript Configuration**: Module resolution not catching errors

## Real-World Impact

### **Silent Failures**
```typescript
// This code appears to work in development but fails in production
function Dashboard() {
    const { systemData } = useRealTimeData()  // Returns undefined data silently

    // Component renders with no real-time updates
    // User sees stale data without knowing system is broken
    return <div>{systemData?.status || 'Unknown'}</div>
}
```

### **Performance Issues**
```typescript
// Multiple real-time connections opened simultaneously
const connection1 = new RealTimeService()  // Socket.IO connection
const connection2 = new RealTimeClient()   // WebSocket connection
const connection3 = useRealTimeConnection() // Another Socket.IO connection

// All three connections compete for same data, causing:
// - Excessive network usage
// - Conflicting state updates
// - Memory leaks from unclosed connections
```

## Proposed Solution

### **Unified Real-Time Architecture**

```typescript
// frontend/src/services/realtime/RealTimeManager.ts - SINGLE SOURCE OF TRUTH
import { io, Socket } from 'socket.io-client'
import { EventEmitter } from 'events'

export type ConnectionState = 'disconnected' | 'connecting' | 'connected' | 'error'

export interface RealTimeConfig {
    url: string
    reconnectAttempts: number
    reconnectDelay: number
    timeout: number
}

export interface RealTimeEvent {
    type: string
    data: any
    timestamp: number
}

export class RealTimeManager extends EventEmitter {
    private socket: Socket | null = null
    private config: RealTimeConfig
    private connectionState: ConnectionState = 'disconnected'
    private reconnectCount = 0

    constructor(config: RealTimeConfig) {
        super()
        this.config = config
        this.setupEventHandlers()
    }

    connect(): void {
        if (this.connectionState === 'connected') return

        this.connectionState = 'connecting'
        this.emit('stateChange', this.connectionState)

        this.socket = io(this.config.url, {
            transports: ['websocket'],
            timeout: this.config.timeout,
            reconnection: false  // We handle reconnection manually
        })

        this.socket.on('connect', this.handleConnect.bind(this))
        this.socket.on('disconnect', this.handleDisconnect.bind(this))
        this.socket.on('error', this.handleError.bind(this))

        // Data event handlers
        this.socket.on('system_status', (data) => this.emit('systemStatus', data))
        this.socket.on('camera_status', (data) => this.emit('cameraStatus', data))
        this.socket.on('capture_progress', (data) => this.emit('captureProgress', data))
    }

    disconnect(): void {
        if (this.socket) {
            this.socket.disconnect()
            this.socket = null
        }
        this.connectionState = 'disconnected'
        this.emit('stateChange', this.connectionState)
    }

    private handleConnect(): void {
        this.connectionState = 'connected'
        this.reconnectCount = 0
        this.emit('stateChange', this.connectionState)
    }

    private handleDisconnect(): void {
        this.connectionState = 'disconnected'
        this.emit('stateChange', this.connectionState)
        this.attemptReconnect()
    }

    private handleError(error: any): void {
        this.connectionState = 'error'
        this.emit('stateChange', this.connectionState)
        this.emit('error', error)
    }

    private attemptReconnect(): void {
        if (this.reconnectCount >= this.config.reconnectAttempts) {
            return  // Give up reconnecting
        }

        setTimeout(() => {
            this.reconnectCount++
            this.connect()
        }, this.config.reconnectDelay * Math.pow(2, this.reconnectCount))  // Exponential backoff
    }

    getConnectionState(): ConnectionState {
        return this.connectionState
    }
}

// Singleton instance
let realTimeManager: RealTimeManager | null = null

export function getRealTimeManager(config?: RealTimeConfig): RealTimeManager {
    if (!realTimeManager && config) {
        realTimeManager = new RealTimeManager(config)
    }

    if (!realTimeManager) {
        throw new Error('RealTimeManager not initialized. Provide config on first call.')
    }

    return realTimeManager
}
```

### **Clean React Integration**

```typescript
// frontend/src/hooks/useRealTime.ts - SINGLE REAL-TIME HOOK
import { useState, useEffect, useCallback } from 'react'
import { getRealTimeManager, ConnectionState, RealTimeConfig } from '../services/realtime/RealTimeManager'

const DEFAULT_CONFIG: RealTimeConfig = {
    url: process.env.VITE_WS_URL || 'http://localhost:8081',
    reconnectAttempts: 5,
    reconnectDelay: 1000,
    timeout: 10000
}

export function useRealTime(config: RealTimeConfig = DEFAULT_CONFIG) {
    const [connectionState, setConnectionState] = useState<ConnectionState>('disconnected')
    const [systemStatus, setSystemStatus] = useState<any>(null)
    const [cameraStatus, setCameraStatus] = useState<any>(null)
    const [captureProgress, setCaptureProgress] = useState<any>(null)

    useEffect(() => {
        const manager = getRealTimeManager(config)

        // Event handlers
        const handleStateChange = (state: ConnectionState) => setConnectionState(state)
        const handleSystemStatus = (data: any) => setSystemStatus(data)
        const handleCameraStatus = (data: any) => setCameraStatus(data)
        const handleCaptureProgress = (data: any) => setCaptureProgress(data)

        // Subscribe to events
        manager.on('stateChange', handleStateChange)
        manager.on('systemStatus', handleSystemStatus)
        manager.on('cameraStatus', handleCameraStatus)
        manager.on('captureProgress', handleCaptureProgress)

        // Connect
        manager.connect()

        // Cleanup
        return () => {
            manager.off('stateChange', handleStateChange)
            manager.off('systemStatus', handleSystemStatus)
            manager.off('cameraStatus', handleCameraStatus)
            manager.off('captureProgress', handleCaptureProgress)
            // Don't disconnect here - let the manager handle connection lifecycle
        }
    }, [config])

    const connect = useCallback(() => {
        const manager = getRealTimeManager()
        manager.connect()
    }, [])

    const disconnect = useCallback(() => {
        const manager = getRealTimeManager()
        manager.disconnect()
    }, [])

    return {
        connectionState,
        systemStatus,
        cameraStatus,
        captureProgress,
        connect,
        disconnect,
        isConnected: connectionState === 'connected',
        isConnecting: connectionState === 'connecting'
    }
}
```

### **Simple Component Usage**

```typescript
// frontend/src/components/dashboard/SystemDashboard.tsx - CLEAN USAGE
import { useRealTime } from '../../hooks/useRealTime'

export function SystemDashboard() {
    const {
        connectionState,
        systemStatus,
        cameraStatus,
        isConnected
    } = useRealTime()

    if (connectionState === 'error') {
        return <div>Real-time connection failed</div>
    }

    return (
        <div>
            <div>Status: {isConnected ? 'Connected' : 'Disconnected'}</div>
            <div>System: {systemStatus?.health || 'Unknown'}</div>
            <div>Camera: {cameraStatus?.model || 'Unknown'}</div>
        </div>
    )
}
```

## Implementation Steps

### **Step 1: Create Unified Manager (2 hours)**
1. Create `RealTimeManager` class with proper event handling
2. Implement connection lifecycle management
3. Add comprehensive error handling and reconnection logic

### **Step 2: Create Clean Hook Interface (1 hour)**
1. Create single `useRealTime` hook
2. Remove all existing real-time hooks
3. Test hook with various connection scenarios

### **Step 3: Remove Circular Dependencies (2 hours)**
1. Delete conflicting service classes
2. Remove unused imports and references
3. Fix all TypeScript compilation errors

### **Step 4: Update All Components (1 hour)**
1. Replace all real-time usage with new `useRealTime` hook
2. Remove old service instantiations
3. Test all components with real-time data

## Testing Strategy

```typescript
// tests/services/RealTimeManager.test.ts
describe('RealTimeManager', () => {
    let manager: RealTimeManager

    beforeEach(() => {
        manager = new RealTimeManager({
            url: 'http://localhost:3001',
            reconnectAttempts: 3,
            reconnectDelay: 100,
            timeout: 1000
        })
    })

    test('connects and emits state changes', async () => {
        const stateChanges: ConnectionState[] = []
        manager.on('stateChange', (state) => stateChanges.push(state))

        manager.connect()

        await waitFor(() => {
            expect(stateChanges).toContain('connecting')
        })
    })

    test('handles reconnection on disconnect', async () => {
        manager.connect()
        await waitFor(() => expect(manager.getConnectionState()).toBe('connected'))

        // Simulate disconnect
        manager['socket']?.disconnect()

        await waitFor(() => {
            expect(manager.getConnectionState()).toBe('connected')  // Should reconnect
        })
    })
})
```

## Dependencies

**Must Complete After**:
- Issue #3 (Configuration) - Need proper config for WebSocket URLs

**Enables These Issues**:
- Issue #35 (Memory Leaks) - Clean connection management prevents leaks
- Issue #28 (Event System) - Provides clean event architecture

---

*This refactoring eliminates circular dependencies and provides a reliable foundation for all real-time functionality.*
