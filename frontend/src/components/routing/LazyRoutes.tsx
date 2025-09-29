/**
 * Lazy Route Components for Code Splitting
 * Professional Mountain Timelapse Camera System
 *
 * Implements React.lazy() for all route components to enable
 * route-based code splitting and reduced initial bundle size.
 */

import { lazy, Suspense } from 'react';
import { LoadingSpinner } from '../ui/LoadingSpinner';

// Lazy load all route components
export const SystemDashboard = lazy(() =>
  import('../dashboard').then(module => ({ default: module.SystemDashboard }))
);

export const CaptureSettingsInterface = lazy(() =>
  import('../settings/CaptureSettingsInterface').then(module => ({
    default: module.CaptureSettingsInterface
  }))
);

export const VideoGenerationInterface = lazy(() =>
  import('../video/VideoGenerationInterface').then(module => ({
    default: module.VideoGenerationInterface
  }))
);

export const ScheduleManagementInterface = lazy(() =>
  import('../schedule/ScheduleManagementInterface').then(module => ({
    default: module.ScheduleManagementInterface
  }))
);

export const AppLayout = lazy(() =>
  import('../layout/AppLayout').then(module => ({
    default: module.AppLayout
  }))
);

// Additional lazy-loaded components for performance
export const CameraPreview = lazy(() =>
  import('../camera/CameraPreview').then(module => ({
    default: module.CameraPreview
  }))
);

export const SystemHealthDashboard = lazy(() =>
  import('../SystemHealthDashboard').then(module => ({
    default: module.SystemHealthDashboard
  }))
);

/**
 * Route Loading Fallback Component
 * Shows spinner while route component is loading
 */
export const RouteLoadingFallback = () => (
  <div className="flex items-center justify-center min-h-screen bg-mountain-50">
    <div className="text-center">
      <LoadingSpinner size="lg" />
      <p className="mt-4 text-mountain-600">Loading...</p>
    </div>
  </div>
);

/**
 * HOC to wrap lazy components with Suspense
 */
export function withSuspense<T extends object>(
  Component: React.ComponentType<T>,
  fallback?: React.ReactNode
) {
  return function SuspenseWrapper(props: T) {
    return (
      <Suspense fallback={fallback || <RouteLoadingFallback />}>
        <Component {...props} />
      </Suspense>
    );
  };
}

// Export wrapped components ready for routing
export const LazySystemDashboard = withSuspense(SystemDashboard);
export const LazyCaptureSettings = withSuspense(CaptureSettingsInterface);
export const LazyVideoGeneration = withSuspense(VideoGenerationInterface);
export const LazyScheduleManagement = withSuspense(ScheduleManagementInterface);
export const LazyAppLayout = withSuspense(AppLayout);

// Export wrapped components for additional lazy loading
export const LazyCameraPreview = withSuspense(CameraPreview);
export const LazySystemHealthDashboard = withSuspense(SystemHealthDashboard);
