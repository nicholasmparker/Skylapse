# Tech Debt Issue #6: Missing Error Boundaries in React Components

## ⚠️ Priority: CRITICAL
**Risk Level**: UI System Failure
**Effort**: 4 hours
**Impact**: UI crashes cascade to entire dashboard

---

## Problem Description

Most React components lack error boundaries for graceful failure handling. When errors occur in components, they crash the entire application instead of showing helpful error messages or fallback UI, creating a poor user experience.

## Specific Locations

### **Components Without Error Boundaries**
- **All Route Components**: Dashboard, Settings, Schedule, Gallery
- **Real-time Components**: System status, camera preview, resource monitoring
- **Complex Components**: Video generation, schedule management
- **Data Components**: Charts, tables, forms

### **Current Error Propagation**

```typescript
// frontend/src/components/dashboard/SystemDashboard.tsx - NO ERROR BOUNDARY
export function SystemDashboard() {
    const { systemStatus, error } = useRealTimeData()  // Can throw errors

    // If useRealTimeData throws, entire app crashes
    return (
        <div>
            <SystemStatusPanel data={systemStatus.services} />  {/* Can throw if systemStatus is undefined */}
            <ResourceMonitoringChart data={systemStatus.resources} />  {/* Can throw */}
            <CameraPreview />  {/* Can throw */}
        </div>
    )
}

// frontend/src/components/dashboard/ResourceMonitoringChart.tsx - NO ERROR BOUNDARY
import { Chart } from 'react-chartjs-2'

export function ResourceMonitoringChart({ data }) {
    // If chart.js throws an error, entire dashboard crashes
    const chartData = {
        datasets: [{
            data: data.map(d => d.value)  // Can throw if data is undefined
        }]
    }

    return <Chart data={chartData} />  // Chart.js errors crash entire app
}

// frontend/src/components/settings/CaptureSettingsInterface.tsx - NO ERROR BOUNDARY
export function CaptureSettingsInterface() {
    const [settings, setSettings] = useState(null)

    useEffect(() => {
        // API call can fail
        apiClient.capture.getSettings().then(setSettings)  // Unhandled promise rejection
    }, [])

    // If settings is null and we try to access properties, app crashes
    return (
        <form>
            <input value={settings.rotation_degrees} />  {/* Can throw */}
            <input value={settings.iso} />  {/* Can throw */}
        </form>
    )
}
```

### **Error Boundary Implementation Gaps**

```typescript
// frontend/src/components/ErrorBoundary.tsx - EXISTS BUT NOT USED
import React, { Component, ErrorInfo, ReactNode } from 'react'

export class ErrorBoundary extends Component {
    // Good error boundary implementation exists...
    // BUT IT'S NEVER ACTUALLY USED IN THE APP!
}

// frontend/src/App.tsx - NO ERROR BOUNDARIES IMPLEMENTED
function App() {
    return (
        <BrowserRouter>
            <Routes>
                {/* All routes can crash the entire app */}
                <Route path="/dashboard" element={<SystemDashboard />} />
                <Route path="/settings" element={<CaptureSettingsInterface />} />
                <Route path="/automation" element={<ScheduleManagementInterface />} />
                <Route path="/gallery" element={<VideoGenerationInterface />} />
            </Routes>
        </BrowserRouter>
    )
    // If any route component throws, entire app becomes unusable
}
```

## Real-World Failure Scenarios

### **Scenario 1: Real-time Connection Failure**
```typescript
// When WebSocket connection fails
function SystemDashboard() {
    const { systemStatus } = useRealTimeData()  // Throws connection error

    // ERROR: Cannot read property 'services' of undefined
    // RESULT: Entire dashboard white screen
    return <SystemStatusPanel data={systemStatus.services} />
}
```

### **Scenario 2: Chart.js Rendering Error**
```typescript
// When chart data is malformed
function ResourceMonitoringChart({ data }) {
    const chartData = {
        datasets: [{
            data: data.map(d => d.value)  // data is null, throws error
        }]
    }

    // Chart.js throws internal error
    // RESULT: Entire dashboard crashes, user sees blank page
    return <Chart data={chartData} />
}
```

### **Scenario 3: API Response Error**
```typescript
// When API returns unexpected data structure
function CaptureSettings() {
    const [settings, setSettings] = useState(null)

    useEffect(() => {
        apiClient.capture.getSettings()
            .then(response => {
                setSettings(response.data.settings)  // response.data is undefined, throws error
            })
    }, [])

    // RESULT: Settings page unusable, user can't configure camera
}
```

## Proposed Solution

### **Hierarchical Error Boundary Strategy**

```typescript
// frontend/src/components/boundaries/AppErrorBoundary.tsx - TOP LEVEL
import React, { Component, ReactNode } from 'react'
import { logger } from '../../utils/logger'

interface Props {
    children: ReactNode
}

interface State {
    hasError: boolean
    error?: Error
    errorInfo?: string
}

export class AppErrorBoundary extends Component<Props, State> {
    constructor(props: Props) {
        super(props)
        this.state = { hasError: false }
    }

    static getDerivedStateFromError(error: Error): State {
        return {
            hasError: true,
            error
        }
    }

    componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
        // Log error for monitoring
        logger.error('Application Error Boundary caught error:', {
            error: error.message,
            stack: error.stack,
            componentStack: errorInfo.componentStack,
            timestamp: new Date().toISOString()
        })

        this.setState({
            error,
            errorInfo: errorInfo.componentStack
        })
    }

    render() {
        if (this.state.hasError) {
            return (
                <div className="min-h-screen bg-mountain-900 flex items-center justify-center">
                    <div className="bg-mountain-800 p-8 rounded-lg max-w-2xl">
                        <h1 className="text-2xl font-bold text-red-400 mb-4">
                            🚨 Application Error
                        </h1>
                        <p className="text-mountain-200 mb-4">
                            Something went wrong with the Skylapse dashboard.
                            Please refresh the page or contact support.
                        </p>

                        <details className="mb-4">
                            <summary className="text-mountain-300 cursor-pointer">
                                Technical Details
                            </summary>
                            <pre className="text-xs text-mountain-400 mt-2 overflow-auto">
                                {this.state.error?.message}
                                {'\n\n'}
                                {this.state.error?.stack}
                            </pre>
                        </details>

                        <div className="flex space-x-4">
                            <button
                                onClick={() => window.location.reload()}
                                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                            >
                                Refresh Page
                            </button>
                            <button
                                onClick={() => this.setState({ hasError: false })}
                                className="px-4 py-2 bg-mountain-600 text-white rounded hover:bg-mountain-700"
                            >
                                Try Again
                            </button>
                        </div>
                    </div>
                </div>
            )
        }

        return this.props.children
    }
}

// frontend/src/components/boundaries/RouteErrorBoundary.tsx - ROUTE LEVEL
export class RouteErrorBoundary extends Component<Props, State> {
    // Similar implementation but with route-specific recovery

    render() {
        if (this.state.hasError) {
            return (
                <div className="p-8 bg-red-50 border border-red-200 rounded-lg">
                    <h2 className="text-xl font-semibold text-red-800 mb-2">
                        Page Error
                    </h2>
                    <p className="text-red-700 mb-4">
                        This page encountered an error. You can try refreshing or navigate to another section.
                    </p>
                    <div className="flex space-x-4">
                        <Link to="/dashboard" className="text-blue-600 hover:underline">
                            Go to Dashboard
                        </Link>
                        <button
                            onClick={() => this.setState({ hasError: false })}
                            className="text-blue-600 hover:underline"
                        >
                            Retry
                        </button>
                    </div>
                </div>
            )
        }

        return this.props.children
    }
}

// frontend/src/components/boundaries/ComponentErrorBoundary.tsx - COMPONENT LEVEL
interface ComponentErrorBoundaryProps {
    children: ReactNode
    fallback?: ReactNode
    componentName?: string
}

export class ComponentErrorBoundary extends Component<ComponentErrorBoundaryProps, State> {
    // Lighter weight error boundary for individual components

    render() {
        if (this.state.hasError) {
            return this.props.fallback || (
                <div className="p-4 bg-yellow-50 border border-yellow-200 rounded">
                    <p className="text-yellow-800">
                        {this.props.componentName || 'Component'} failed to load.
                    </p>
                    <button
                        onClick={() => this.setState({ hasError: false })}
                        className="text-sm text-yellow-600 hover:underline"
                    >
                        Retry
                    </button>
                </div>
            )
        }

        return this.props.children
    }
}
```

### **Strategic Error Boundary Placement**

```typescript
// frontend/src/App.tsx - TOP LEVEL PROTECTION
import { AppErrorBoundary } from './components/boundaries/AppErrorBoundary'
import { RouteErrorBoundary } from './components/boundaries/RouteErrorBoundary'

function App() {
    return (
        <AppErrorBoundary>
            <BrowserRouter>
                <Routes>
                    <Route path="/dashboard" element={
                        <RouteErrorBoundary>
                            <SystemDashboard />
                        </RouteErrorBoundary>
                    } />
                    <Route path="/settings" element={
                        <RouteErrorBoundary>
                            <CaptureSettingsInterface />
                        </RouteErrorBoundary>
                    } />
                    <Route path="/automation" element={
                        <RouteErrorBoundary>
                            <ScheduleManagementInterface />
                        </RouteErrorBoundary>
                    } />
                    <Route path="/gallery" element={
                        <RouteErrorBoundary>
                            <VideoGenerationInterface />
                        </RouteErrorBoundary>
                    } />
                </Routes>
            </BrowserRouter>
        </AppErrorBoundary>
    )
}

// frontend/src/components/dashboard/SystemDashboard.tsx - COMPONENT LEVEL
import { ComponentErrorBoundary } from '../boundaries/ComponentErrorBoundary'

export function SystemDashboard() {
    return (
        <div className="space-y-6">
            <ComponentErrorBoundary componentName="System Status">
                <SystemStatusPanel />
            </ComponentErrorBoundary>

            <ComponentErrorBoundary
                componentName="Camera Preview"
                fallback={<div className="p-4 bg-gray-100">Camera preview unavailable</div>}
            >
                <CameraPreview />
            </ComponentErrorBoundary>

            <ComponentErrorBoundary componentName="Resource Monitor">
                <ResourceMonitoringChart />
            </ComponentErrorBoundary>

            <ComponentErrorBoundary componentName="Recent Captures">
                <RecentCapturesGrid />
            </ComponentErrorBoundary>
        </div>
    )
}
```

### **Safe Component Implementation**

```typescript
// frontend/src/components/dashboard/ResourceMonitoringChart.tsx - SAFE VERSION
export function ResourceMonitoringChart({ data }) {
    // Defensive programming + error boundary protection
    if (!data || !Array.isArray(data)) {
        return (
            <div className="p-4 text-center text-gray-500">
                No resource data available
            </div>
        )
    }

    try {
        const chartData = {
            datasets: [{
                data: data.map(d => d?.value || 0)  // Safe property access
            }]
        }

        return <Chart data={chartData} />
    } catch (error) {
        // This shouldn't happen with error boundary, but just in case
        return (
            <div className="p-4 bg-red-50 text-red-700">
                Chart failed to render
            </div>
        )
    }
}
```

## Implementation Steps

### **Step 1: Create Error Boundary Components (1.5 hours)**
1. Create `AppErrorBoundary` for top-level errors
2. Create `RouteErrorBoundary` for page-level errors
3. Create `ComponentErrorBoundary` for component-level errors
4. Add comprehensive error logging

### **Step 2: Add Route-Level Error Boundaries (1 hour)**
1. Wrap all route components with `RouteErrorBoundary`
2. Test error handling for each route
3. Customize error messages per route

### **Step 3: Add Component-Level Error Boundaries (1 hour)**
1. Wrap critical components (charts, real-time data, forms)
2. Add custom fallback UI for each component type
3. Test error recovery mechanisms

### **Step 4: Improve Defensive Programming (30 minutes)**
1. Add null checks and safe property access
2. Add loading states and error states to components
3. Handle async errors properly

## Testing Strategy

```typescript
// tests/components/ErrorBoundary.test.tsx
describe('Error Boundaries', () => {
    const ThrowError = ({ shouldThrow }: { shouldThrow: boolean }) => {
        if (shouldThrow) {
            throw new Error('Test error')
        }
        return <div>No error</div>
    }

    test('AppErrorBoundary catches and displays errors', () => {
        const consoleSpy = jest.spyOn(console, 'error').mockImplementation()

        render(
            <AppErrorBoundary>
                <ThrowError shouldThrow={true} />
            </AppErrorBoundary>
        )

        expect(screen.getByText(/Application Error/)).toBeInTheDocument()
        expect(screen.getByText(/refresh the page/i)).toBeInTheDocument()

        consoleSpy.mockRestore()
    })

    test('ComponentErrorBoundary shows custom fallback', () => {
        render(
            <ComponentErrorBoundary
                fallback={<div>Custom error message</div>}
            >
                <ThrowError shouldThrow={true} />
            </ComponentErrorBoundary>
        )

        expect(screen.getByText('Custom error message')).toBeInTheDocument()
    })

    test('Error boundary recovery works', () => {
        const { rerender } = render(
            <ComponentErrorBoundary>
                <ThrowError shouldThrow={true} />
            </ComponentErrorBoundary>
        )

        // Should show error state
        expect(screen.getByText(/failed to load/)).toBeInTheDocument()

        // Click retry button
        fireEvent.click(screen.getByText('Retry'))

        // Re-render with no error
        rerender(
            <ComponentErrorBoundary>
                <ThrowError shouldThrow={false} />
            </ComponentErrorBoundary>
        )

        expect(screen.getByText('No error')).toBeInTheDocument()
    })
})
```

## Dependencies

**Required For**:
- Issue #37 (Bundle Splitting) - Lazy loading needs error boundaries
- Issue #4 (Real-time Client) - Real-time errors need graceful handling

**Enhanced By**:
- Issue #1 (Error Handling) - Better backend error responses improve error messages

---

*Error boundaries transform catastrophic UI failures into manageable, recoverable user experiences.*
