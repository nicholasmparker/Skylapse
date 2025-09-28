/**
 * Test Schedule Component - Simple debugging component
 */

import React, { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';

export const TestSchedule: React.FC = () => {
  const location = useLocation();
  const [renderTime] = useState(() => new Date().toISOString());
  const [debugInfo, setDebugInfo] = useState<string[]>([]);

  useEffect(() => {
    // Log component lifecycle for debugging
    console.log('🔥 TestSchedule: Component mounted at', renderTime);
    console.log('🔥 TestSchedule: Current location:', location);
    console.log('🔥 TestSchedule: Window location:', window.location.href);

    setDebugInfo([
      `Mounted at: ${renderTime}`,
      `Route location: ${location.pathname}`,
      `Window location: ${window.location.pathname}`,
      `Component rendered successfully`
    ]);

    // Add route change listener for debugging
    const handleLocationChange = () => {
      console.log('🔥 TestSchedule: Location changed to:', window.location.pathname);
      if (window.location.pathname !== '/schedule') {
        console.error('🚨 TestSchedule: UNEXPECTED REDIRECT DETECTED!');
        console.error('🚨 Expected: /schedule, Got:', window.location.pathname);
      }
    };

    // Monitor for navigation changes
    const originalPushState = history.pushState;
    const originalReplaceState = history.replaceState;

    history.pushState = function(...args) {
      console.log('🔥 TestSchedule: History pushState called with:', args);
      return originalPushState.apply(this, args);
    };

    history.replaceState = function(...args) {
      console.log('🔥 TestSchedule: History replaceState called with:', args);
      return originalReplaceState.apply(this, args);
    };

    window.addEventListener('popstate', handleLocationChange);

    return () => {
      console.log('🔥 TestSchedule: Component unmounting');
      window.removeEventListener('popstate', handleLocationChange);
      history.pushState = originalPushState;
      history.replaceState = originalReplaceState;
    };
  }, [location, renderTime]);

  // Render with extensive debugging information
  return (
    <div className="p-6 space-y-6">
      <div className="bg-green-50 border border-green-200 rounded-lg p-4">
        <h1 className="text-3xl font-bold text-mountain-900 mb-2">
          📅 Test Schedule Page - SUCCESS!
        </h1>
        <p className="text-green-700 font-medium">
          ✅ This component rendered successfully without errors
        </p>
      </div>

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h2 className="text-lg font-semibold text-blue-900 mb-3">Debug Information</h2>
        <div className="space-y-2">
          {debugInfo.map((info, index) => (
            <div key={index} className="text-sm text-blue-800">
              • {info}
            </div>
          ))}
        </div>
      </div>

      <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
        <h2 className="text-lg font-semibold text-amber-900 mb-3">Route State</h2>
        <div className="text-sm text-amber-800 space-y-1">
          <div>React Router pathname: {location.pathname}</div>
          <div>React Router search: {location.search}</div>
          <div>React Router state: {JSON.stringify(location.state)}</div>
          <div>Window pathname: {window.location.pathname}</div>
          <div>Window href: {window.location.href}</div>
        </div>
      </div>

      <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
        <h2 className="text-lg font-semibold text-purple-900 mb-3">Test Content</h2>
        <p className="text-purple-800">
          This is the schedule page content. If you're seeing this message,
          the routing is working correctly and the component has rendered without errors.
        </p>
        <div className="mt-4 p-3 bg-purple-100 rounded text-sm text-purple-700">
          <strong>Next Steps:</strong> If this page stays visible, the routing works.
          If it redirects, check the browser console for the debug messages above.
        </div>
      </div>
    </div>
  );
};

export default TestSchedule;
