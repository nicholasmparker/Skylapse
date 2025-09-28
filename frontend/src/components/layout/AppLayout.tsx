/**
 * App Layout - Main navigation and layout structure
 * Professional Mountain Timelapse Camera System
 */

import React, { useState } from 'react';
import { Outlet, NavLink, useLocation } from 'react-router-dom';
import { cn } from '@/utils';

interface NavigationItem {
  id: string;
  name: string;
  path: string;
  icon: string;
  description: string;
}

const NAVIGATION_ITEMS: NavigationItem[] = [
  {
    id: 'dashboard',
    name: 'Dashboard',
    path: '/dashboard',
    icon: '🏔️',
    description: 'System monitoring and live camera preview',
  },
  {
    id: 'settings',
    name: 'Capture Settings',
    path: '/settings',
    icon: '📷',
    description: 'Camera controls and capture configuration',
  },
  {
    id: 'gallery',
    name: 'Gallery',
    path: '/gallery',
    icon: '🎬',
    description: 'Timelapse sequences and media management',
  },
  {
    id: 'automation',
    name: 'Schedule',
    path: '/automation',
    icon: '📅',
    description: 'Automated capture scheduling',
  },
  {
    id: 'analytics',
    name: 'Analytics',
    path: '/analytics',
    icon: '📊',
    description: 'Performance metrics and insights',
  },
];

export const AppLayout: React.FC = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();

  const currentPage = NAVIGATION_ITEMS.find(item =>
    location.pathname.startsWith(item.path)
  );

  return (
    <div className="min-h-screen bg-mountain-50">
      {/* Mobile sidebar backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-mountain-900/50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <div className={cn(
        'fixed inset-y-0 left-0 z-50 w-64 bg-white shadow-lg transform transition-transform duration-300 ease-in-out lg:translate-x-0',
        sidebarOpen ? 'translate-x-0' : '-translate-x-full'
      )}>
        <div className="flex flex-col h-full">
          {/* Logo and branding */}
          <div className="flex items-center h-16 px-6 border-b border-mountain-200">
            <div className="flex items-center space-x-3">
              <div className="text-2xl">🏔️</div>
              <div>
                <h1 className="text-xl font-bold text-mountain-900">Skylapse</h1>
                <p className="text-xs text-mountain-600">Mountain Timelapse</p>
              </div>
            </div>
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-4 py-6 space-y-2">
            {NAVIGATION_ITEMS.map((item) => (
              <NavLink
                key={item.id}
                to={item.path}
                className={({ isActive }) => cn(
                  'flex items-center px-3 py-3 text-sm font-medium rounded-lg transition-colors group',
                  isActive
                    ? 'bg-golden-50 text-golden-700 border border-golden-200'
                    : 'text-mountain-700 hover:bg-mountain-50 hover:text-mountain-900'
                )}
                onClick={() => setSidebarOpen(false)}
              >
                <span className="text-lg mr-3">{item.icon}</span>
                <div className="flex-1">
                  <div className="font-medium">{item.name}</div>
                  <div className="text-xs text-mountain-600 group-hover:text-mountain-700">
                    {item.description}
                  </div>
                </div>
              </NavLink>
            ))}
          </nav>

          {/* Footer info */}
          <div className="p-4 border-t border-mountain-200">
            <div className="text-xs text-mountain-500 space-y-1">
              <div>Sprint 3: Professional Interface</div>
              <div>Version 1.0.0-sprint3</div>
              <div className="flex items-center space-x-1">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                <span>System Online</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Main content area */}
      <div className="lg:pl-64">
        {/* Top bar */}
        <div className="sticky top-0 z-30 bg-white border-b border-mountain-200 lg:hidden">
          <div className="flex items-center justify-between h-16 px-4">
            <button
              onClick={() => setSidebarOpen(true)}
              className="p-2 text-mountain-600 hover:text-mountain-900 hover:bg-mountain-100 rounded-lg"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>

            <div className="flex items-center space-x-3">
              <span className="text-lg">{currentPage?.icon}</span>
              <div>
                <h1 className="text-lg font-semibold text-mountain-900">
                  {currentPage?.name || 'Skylapse'}
                </h1>
              </div>
            </div>

            <div className="w-10" /> {/* Spacer for balance */}
          </div>
        </div>

        {/* Page content */}
        <main className="relative">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export default AppLayout;
