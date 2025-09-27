/**
 * Skylapse Frontend Application
 * Professional Mountain Timelapse Camera System
 */

import { useState } from 'react';
import { Button, Card, StatusCard, StatusIndicator, ServiceStatus, Input } from '@/design-system/components';

// Sample data for component showcase
const sampleServices = [
  { name: 'Capture Service', status: 'running' as const, uptime: '2d 4h 32m', version: '1.0.0' },
  { name: 'Processing Service', status: 'running' as const, uptime: '2d 4h 30m', version: '1.0.0' },
  { name: 'Camera Driver', status: 'running' as const, uptime: '2d 4h 31m', version: '2.1.3' },
];

function App() {
  const [loading, setLoading] = useState(false);

  const handleTestAction = () => {
    setLoading(true);
    setTimeout(() => setLoading(false), 2000);
  };

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-4">
              <h1 className="text-xl font-bold text-gradient-mountain">
                Skylapse
              </h1>
              <span className="text-sm text-slate-500">Mountain Timelapse System</span>
            </div>
            <div className="flex items-center space-x-3">
              <StatusIndicator status="active" label="System Online" pulse />
              <Button variant="outline" size="sm">
                Settings
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="space-y-8">
          {/* Welcome Section */}
          <div className="text-center">
            <h2 className="text-3xl font-bold text-slate-900 mb-4">
              Welcome to Sprint 3 🏔️
            </h2>
            <p className="text-lg text-slate-600 max-w-2xl mx-auto">
              Professional web interface for the Skylapse mountain timelapse camera system.
              Built with React, TypeScript, and Tailwind CSS.
            </p>
          </div>

          {/* Component Showcase */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Button Showcase */}
            <Card title="Button Components" subtitle="Professional mountain photography styled buttons">
              <div className="space-y-4">
                <div className="flex flex-wrap gap-3">
                  <Button variant="primary">Primary</Button>
                  <Button variant="secondary">Secondary</Button>
                  <Button variant="outline">Outline</Button>
                  <Button variant="ghost">Ghost</Button>
                  <Button variant="golden">Golden Hour</Button>
                </div>
                <div className="flex flex-wrap gap-3">
                  <Button size="sm">Small</Button>
                  <Button size="md">Medium</Button>
                  <Button size="lg">Large</Button>
                </div>
                <div className="flex flex-wrap gap-3">
                  <Button loading={loading} onClick={handleTestAction}>
                    {loading ? 'Processing...' : 'Test Loading'}
                  </Button>
                  <Button disabled>Disabled</Button>
                </div>
              </div>
            </Card>

            {/* Status Cards */}
            <Card title="Status Cards" subtitle="Real-time system monitoring components">
              <div className="space-y-4">
                <StatusCard
                  status="active"
                  value="127"
                  label="Captures Today"
                  icon={
                    <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M4 5a2 2 0 00-2 2v6a2 2 0 002 2h12a2 2 0 002-2V7a2 2 0 00-2-2h-1.586a1 1 0 01-.707-.293l-1.121-1.121A2 2 0 0011.172 3H8.828a2 2 0 00-1.414.586L6.293 4.707A1 1 0 015.586 5H4zm6 9a3 3 0 100-6 3 3 0 000 6z" clipRule="evenodd" />
                    </svg>
                  }
                  trend={{ value: 12, label: 'vs yesterday', direction: 'up' }}
                />
                <StatusCard
                  status="success"
                  value="98.5%"
                  label="Success Rate"
                  icon={
                    <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                  }
                  trend={{ value: 2.1, label: 'improvement', direction: 'up' }}
                />
              </div>
            </Card>

            {/* Input Components */}
            <Card title="Input Components" subtitle="Form controls for camera configuration">
              <div className="space-y-4">
                <Input
                  label="Camera ISO"
                  type="number"
                  placeholder="Enter ISO value"
                  helperText="Choose between 100-6400"
                />
                <Input
                  label="Exposure Time"
                  placeholder="e.g., 1/125"
                  leftIcon={
                    <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.414-1.415L11 9.586V6z" clipRule="evenodd" />
                    </svg>
                  }
                />
                <Input
                  label="Test Error State"
                  defaultValue="Invalid value"
                  error="This field contains an error"
                />
              </div>
            </Card>

            {/* Service Status */}
            <Card title="Service Status" subtitle="Real-time system health monitoring">
              <ServiceStatus services={sampleServices} />
            </Card>
          </div>

          {/* Status Indicators */}
          <Card title="Status Indicators" subtitle="System status visualization">
            <div className="flex flex-wrap gap-4">
              <StatusIndicator status="active" label="Capturing" pulse />
              <StatusIndicator status="paused" label="Paused" />
              <StatusIndicator status="error" label="Error" />
              <StatusIndicator status="success" label="Complete" />
            </div>
          </Card>

          {/* Architecture Info */}
          <Card
            title="Sprint 3 Architecture"
            subtitle="Docker containerized frontend with mountain photography theme"
          >
            <div className="prose max-w-none">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <h4 className="font-semibold text-slate-900 mb-3">✅ Completed</h4>
                  <ul className="space-y-2 text-sm text-slate-600">
                    <li>• React 18+ with TypeScript setup</li>
                    <li>• Tailwind CSS v4 mountain theme</li>
                    <li>• Docker containerization</li>
                    <li>• Component library foundation</li>
                    <li>• Professional design system</li>
                    <li>• API client architecture</li>
                  </ul>
                </div>
                <div>
                  <h4 className="font-semibold text-slate-900 mb-3">🚧 Next Steps</h4>
                  <ul className="space-y-2 text-sm text-slate-600">
                    <li>• React Router implementation</li>
                    <li>• Zustand state management</li>
                    <li>• WebSocket real-time updates</li>
                    <li>• Backend API extensions</li>
                    <li>• Dashboard implementation</li>
                    <li>• Gallery and settings pages</li>
                  </ul>
                </div>
              </div>
            </div>
          </Card>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-slate-200 mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="text-center text-sm text-slate-500">
            <p>
              Skylapse Professional Mountain Timelapse System - Sprint 3 Development
            </p>
            <p className="mt-1">
              Built with excellence by the Skylapse development team 🏔️📸✨
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
