/**
 * Skylapse Frontend Application
 * Professional Mountain Timelapse Camera System
 *
 * Production-ready React application with authentication,
 * error boundaries, and bulletproof real-time connectivity.
 */

import React from 'react';
import { AuthProvider } from './contexts/AuthContext';
import { ApplicationErrorBoundary, DashboardErrorBoundary } from './components/ErrorBoundary';
import { SystemDashboard } from './components/dashboard';
import './config/environment'; // Initialize and validate environment

function App() {
  return (
    <ApplicationErrorBoundary>
      <AuthProvider>
        <DashboardErrorBoundary>
          <SystemDashboard />
        </DashboardErrorBoundary>
      </AuthProvider>
    </ApplicationErrorBoundary>
  );
}

export default App;
