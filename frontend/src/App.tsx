/**
 * Skylapse Frontend Application
 * Professional Mountain Timelapse Camera System
 *
 * Production-ready React application with authentication,
 * error boundaries, and bulletproof real-time connectivity.
 */

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { ApplicationErrorBoundary, DashboardErrorBoundary } from './components/ErrorBoundary';
import {
  LazySystemDashboard,
  LazyCaptureSettings,
  LazyVideoGeneration,
  LazyScheduleManagement,
  LazyAppLayout
} from './components/routing/LazyRoutes';
import './config/environment'; // Initialize and validate environment

function App() {

  return (
    <ApplicationErrorBoundary>
      <AuthProvider>
        <BrowserRouter>
          <DashboardErrorBoundary>
            <Routes>
              <Route path="/" element={<LazyAppLayout />}>
                <Route index element={<Navigate to="/dashboard" replace />} />
                <Route path="dashboard" element={<LazySystemDashboard />} />
                <Route path="settings" element={<LazyCaptureSettings />} />
                <Route path="gallery" element={<LazyVideoGeneration />} />
                <Route path="automation" element={<LazyScheduleManagement />} />
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
