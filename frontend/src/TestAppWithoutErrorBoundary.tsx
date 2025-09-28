/**
 * Test App without DashboardErrorBoundary for debugging
 * Use this temporarily to isolate error boundary issues
 */

import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { ApplicationErrorBoundary } from './components/ErrorBoundary';
import { SystemDashboard } from './components/dashboard';
import { CaptureSettingsInterface } from './components/settings/CaptureSettingsInterface';
import { VideoGenerationInterface } from './components/video/VideoGenerationInterface';
import { TestSchedule } from './components/schedule/TestSchedule';
import { MinimalSchedule } from './components/schedule/MinimalSchedule';
import { AppLayout } from './components/layout/AppLayout';

function TestAppWithoutErrorBoundary() {
  console.log('🔥 TestApp: Starting without DashboardErrorBoundary');

  return (
    <ApplicationErrorBoundary>
      <AuthProvider>
        <BrowserRouter>
          {/* NO DashboardErrorBoundary here */}
          <Routes>
            <Route path="/" element={<AppLayout />}>
              <Route index element={<Navigate to="/dashboard" replace />} />
              <Route path="dashboard" element={<SystemDashboard />} />
              <Route path="settings" element={<CaptureSettingsInterface />} />
              <Route path="gallery" element={<VideoGenerationInterface />} />
              <Route path="schedule" element={<TestSchedule />} />
              <Route path="minimal-schedule" element={<MinimalSchedule />} />
              <Route path="*" element={<Navigate to="/dashboard" replace />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ApplicationErrorBoundary>
  );
}

export default TestAppWithoutErrorBoundary;
