/**
 * Status Indicator Component - Skylapse Design System
 * Professional Mountain Timelapse Camera System
 */

import { forwardRef } from 'react';
import { cn } from '@/utils';
import type { StatusIndicatorProps } from '@/api/types';

const StatusIndicator = forwardRef<HTMLDivElement, StatusIndicatorProps>(
  ({ status, label, pulse = false, className, ...props }, ref) => {
    const statusStyles = {
      active: {
        dot: 'bg-success-400',
        text: 'text-success-800',
        bg: 'bg-success-100',
      },
      paused: {
        dot: 'bg-warning-400',
        text: 'text-warning-800',
        bg: 'bg-warning-100',
      },
      error: {
        dot: 'bg-error-400',
        text: 'text-error-800',
        bg: 'bg-error-100',
      },
      success: {
        dot: 'bg-success-400',
        text: 'text-success-800',
        bg: 'bg-success-100',
      },
    };

    const styles = statusStyles[status];

    return (
      <div
        ref={ref}
        className={cn(
          'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
          styles.bg,
          styles.text,
          className
        )}
        {...props}
      >
        <div
          className={cn(
            'w-1.5 h-1.5 rounded-full mr-1.5',
            styles.dot,
            pulse && 'animate-pulse'
          )}
        />
        {label}
      </div>
    );
  }
);

StatusIndicator.displayName = 'StatusIndicator';

// Service Status Component for system health
interface ServiceStatusProps {
  services: Array<{
    name: string;
    status: 'running' | 'stopped' | 'error';
    uptime?: string;
    version?: string;
  }>;
  className?: string;
}

const ServiceStatus = forwardRef<HTMLDivElement, ServiceStatusProps>(
  ({ services, className }, ref) => {
    return (
      <div ref={ref} className={cn('space-y-3', className)}>
        {services.map((service) => (
          <div
            key={service.name}
            className="flex items-center justify-between p-3 bg-white rounded-lg border border-slate-200"
          >
            <div className="flex items-center space-x-3">
              <StatusIndicator
                status={service.status === 'running' ? 'active' : service.status === 'error' ? 'error' : 'paused'}
                label={service.status}
                pulse={service.status === 'running'}
              />
              <div>
                <h4 className="text-sm font-medium text-slate-900">{service.name}</h4>
                {service.uptime && (
                  <p className="text-xs text-slate-500">Uptime: {service.uptime}</p>
                )}
              </div>
            </div>
            {service.version && (
              <span className="text-xs text-slate-400 font-mono">
                v{service.version}
              </span>
            )}
          </div>
        ))}
      </div>
    );
  }
);

ServiceStatus.displayName = 'ServiceStatus';

export { StatusIndicator, ServiceStatus };
export type { StatusIndicatorProps, ServiceStatusProps };
