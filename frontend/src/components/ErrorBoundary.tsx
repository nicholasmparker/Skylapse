/**
 * Error Boundary Components for Skylapse Dashboard
 * Professional Mountain Timelapse Camera System
 *
 * Provides comprehensive error handling with graceful degradation
 * and user-friendly error messages for production deployment.
 */

import React, { Component, ErrorInfo, ReactNode } from 'react';
import { Button } from '../design-system/components/Button';
import { Card } from '../design-system/components/Card';

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  errorId: string;
}

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  level?: 'application' | 'component' | 'feature';
  resetKeys?: Array<string | number>;
  resetOnPropsChange?: boolean;
}

class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  private resetTimeoutId: number | null = null;

  constructor(props: ErrorBoundaryProps) {
    super(props);

    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      errorId: '',
    };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    // Generate unique error ID for tracking
    const errorId = `err_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

    return {
      hasError: true,
      error,
      errorId,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log error details
    console.error('ErrorBoundary caught an error:', error, errorInfo);

    // Update state with error info
    this.setState({
      errorInfo,
    });

    // Call custom error handler if provided
    this.props.onError?.(error, errorInfo);

    // Send error to monitoring service in production
    if (process.env.NODE_ENV === 'production') {
      this.reportError(error, errorInfo);
    }
  }

  componentDidUpdate(prevProps: ErrorBoundaryProps) {
    const { resetKeys, resetOnPropsChange } = this.props;
    const { hasError } = this.state;

    // Reset error state if resetKeys have changed
    if (hasError && resetKeys && prevProps.resetKeys) {
      if (resetKeys.some((resetKey, idx) => prevProps.resetKeys![idx] !== resetKey)) {
        this.resetErrorBoundary();
      }
    }

    // Reset error state if any props have changed (when enabled)
    if (hasError && resetOnPropsChange && prevProps !== this.props) {
      this.resetErrorBoundary();
    }
  }

  componentWillUnmount() {
    if (this.resetTimeoutId) {
      clearTimeout(this.resetTimeoutId);
    }
  }

  private reportError = (error: Error, errorInfo: ErrorInfo) => {
    // In a real application, send this to your error reporting service
    const errorReport = {
      message: error.message,
      stack: error.stack,
      componentStack: errorInfo.componentStack,
      errorId: this.state.errorId,
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      url: window.location.href,
      level: this.props.level || 'component',
    };

    console.log('Error report:', errorReport);
    // Example: sendToErrorService(errorReport);
  };

  private resetErrorBoundary = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
      errorId: '',
    });
  };

  private handleRetry = () => {
    this.resetErrorBoundary();
  };

  private handleReload = () => {
    window.location.reload();
  };

  private renderErrorUI() {
    const { error, errorId } = this.state;
    const { level = 'component' } = this.props;

    // Application-level error (most severe)
    if (level === 'application') {
      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
          <Card className="max-w-md w-full text-center">
            <div className="space-y-4">
              <div className="w-16 h-16 mx-auto bg-red-100 rounded-full flex items-center justify-center">
                <svg className="w-8 h-8 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
              </div>
              <h1 className="text-xl font-semibold text-gray-900">
                Skylapse Dashboard Error
              </h1>
              <p className="text-gray-600">
                The dashboard encountered an unexpected error and needs to be reloaded.
              </p>
              <div className="bg-gray-100 p-3 rounded text-sm text-left">
                <strong>Error ID:</strong> {errorId}
                <br />
                <strong>Message:</strong> {error?.message}
              </div>
              <div className="flex gap-2 justify-center">
                <Button variant="primary" onClick={this.handleReload}>
                  Reload Dashboard
                </Button>
                <Button variant="outline" onClick={this.handleRetry}>
                  Try Again
                </Button>
              </div>
            </div>
          </Card>
        </div>
      );
    }

    // Feature-level error (moderate)
    if (level === 'feature') {
      return (
        <Card className="border-red-200 bg-red-50">
          <div className="flex items-start space-x-3">
            <div className="flex-shrink-0">
              <svg className="w-5 h-5 text-red-600 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="text-sm font-medium text-red-800">
                Feature Unavailable
              </h3>
              <p className="text-sm text-red-700 mt-1">
                This feature encountered an error and is temporarily unavailable.
              </p>
              <div className="mt-3">
                <Button size="sm" variant="outline" onClick={this.handleRetry}>
                  Retry
                </Button>
              </div>
            </div>
          </div>
        </Card>
      );
    }

    // Component-level error (minimal)
    return (
      <div className="border border-red-200 bg-red-50 rounded-lg p-4">
        <div className="flex items-center">
          <svg className="w-4 h-4 text-red-600 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span className="text-sm text-red-800">Component error occurred</span>
          <Button
            size="sm"
            variant="ghost"
            className="ml-auto text-xs"
            onClick={this.handleRetry}
          >
            Retry
          </Button>
        </div>
      </div>
    );
  }

  render() {
    if (this.state.hasError) {
      // Use custom fallback if provided
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // Otherwise render default error UI
      return this.renderErrorUI();
    }

    return this.props.children;
  }
}

// Higher-order component for wrapping components with error boundaries
export function withErrorBoundary<P extends object>(
  Component: React.ComponentType<P>,
  errorBoundaryProps?: Partial<ErrorBoundaryProps>
) {
  const WrappedComponent = (props: P) => (
    <ErrorBoundary {...errorBoundaryProps}>
      <Component {...props} />
    </ErrorBoundary>
  );

  WrappedComponent.displayName = `withErrorBoundary(${Component.displayName || Component.name})`;
  return WrappedComponent;
}

// React Hook for catching async errors
export function useErrorHandler() {
  const [error, setError] = React.useState<Error | null>(null);

  const resetError = React.useCallback(() => {
    setError(null);
  }, []);

  const captureError = React.useCallback((error: Error) => {
    setError(error);
  }, []);

  // Throw error to trigger error boundary
  if (error) {
    throw error;
  }

  return { captureError, resetError };
}

// Specific error boundaries for different parts of the application
export const DashboardErrorBoundary: React.FC<{ children: ReactNode }> = ({ children }) => (
  <ErrorBoundary
    level="feature"
    resetOnPropsChange={true}
    onError={(error, errorInfo) => {
      console.error('🚨 DashboardErrorBoundary: Error caught!', error, errorInfo);
      console.error('🚨 Current URL when error occurred:', window.location.href);
      console.error('🚨 Component stack:', errorInfo.componentStack);

      // Check if this is happening on the schedule route
      if (window.location.pathname === '/schedule') {
        console.error('🚨 CRITICAL: Error occurred on /schedule route!');
        console.error('🚨 This might be causing the redirect to /dashboard');
      }
    }}
  >
    {children}
  </ErrorBoundary>
);

export const RealTimeErrorBoundary: React.FC<{ children: ReactNode }> = ({ children }) => (
  <ErrorBoundary
    level="component"
    resetOnPropsChange={true}
    fallback={
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <div className="flex items-center">
          <svg className="w-4 h-4 text-yellow-600 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span className="text-sm text-yellow-800">
            Real-time updates temporarily unavailable. Dashboard will continue to work with manual refresh.
          </span>
        </div>
      </div>
    }
    onError={(error, errorInfo) => {
      console.error('Real-time connection error:', error, errorInfo);
    }}
  >
    {children}
  </ErrorBoundary>
);

export const ApplicationErrorBoundary: React.FC<{ children: ReactNode }> = ({ children }) => (
  <ErrorBoundary
    level="application"
    onError={(error, errorInfo) => {
      console.error('Application-level error:', error, errorInfo);
    }}
  >
    {children}
  </ErrorBoundary>
);

export default ErrorBoundary;
