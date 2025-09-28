/**
 * Skylapse Frontend Application
 * Professional Mountain Timelapse Camera System
 *
 * Production-ready React application with authentication,
 * error boundaries, and bulletproof real-time connectivity.
 */

import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { ApplicationErrorBoundary, DashboardErrorBoundary } from './components/ErrorBoundary';
import { SystemDashboard } from './components/dashboard';
import { CaptureSettingsInterface } from './components/settings/CaptureSettingsInterface';
import { VideoGenerationInterface } from './components/video/VideoGenerationInterface';
import { ScheduleManagementInterface } from './components/schedule/ScheduleManagementInterface';
import { AppLayout } from './components/layout/AppLayout';
import './config/environment'; // Initialize and validate environment

function App() {

  return (
    <ApplicationErrorBoundary>
      <AuthProvider>
        <BrowserRouter>
          <DashboardErrorBoundary>
            <Routes>
              <Route path="/" element={<AppLayout />}>
                <Route index element={<Navigate to="/dashboard" replace />} />
                <Route path="dashboard" element={<SystemDashboard />} />
                <Route path="settings" element={<CaptureSettingsInterface />} />
                <Route path="gallery" element={<VideoGenerationInterface />} />
                <Route path="automation" element={<ScheduleManagementInterface />} />
                <Route path="*" element={<Navigate to="/dashboard" replace />} />
              </Route>
            </Routes>
          </DashboardErrorBoundary>
        </BrowserRouter>
      </AuthProvider>
    </ApplicationErrorBoundary>
  );
}

export default App;
