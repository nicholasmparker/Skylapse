/**
 * Card Component - Skylapse Design System
 * Professional Mountain Timelapse Camera System
 */

import { forwardRef } from 'react';
import { cn } from '@/utils';
import type { CardProps } from '@/api/types';

const Card = forwardRef<HTMLDivElement, CardProps>(
  ({ children, className, title, subtitle, actions, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          'bg-white rounded-lg shadow-sm border border-slate-200 overflow-hidden',
          className
        )}
        {...props}
      >
        {(title || subtitle || actions) && (
          <div className="px-6 py-4 border-b border-slate-200">
            <div className="flex items-center justify-between">
              <div className="flex-1 min-w-0">
                {title && (
                  <h3 className="text-lg font-medium text-slate-900 truncate">
                    {title}
                  </h3>
                )}
                {subtitle && (
                  <p className="text-sm text-slate-500 truncate mt-1">
                    {subtitle}
                  </p>
                )}
              </div>
              {actions && (
                <div className="flex items-center space-x-2 ml-4">
                  {actions}
                </div>
              )}
            </div>
          </div>
        )}

        <div className="p-6">
          {children}
        </div>
      </div>
    );
  }
);

Card.displayName = 'Card';

// Card sub-components for more flexible layouts
const CardHeader = forwardRef<HTMLDivElement, CardProps>(
  ({ children, className, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn('px-6 py-4 border-b border-slate-200', className)}
        {...props}
      >
        {children}
      </div>
    );
  }
);

CardHeader.displayName = 'CardHeader';

const CardBody = forwardRef<HTMLDivElement, CardProps>(
  ({ children, className, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn('p-6', className)}
        {...props}
      >
        {children}
      </div>
    );
  }
);

CardBody.displayName = 'CardBody';

const CardFooter = forwardRef<HTMLDivElement, CardProps>(
  ({ children, className, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          'px-6 py-4 border-t border-slate-200 bg-slate-50',
          className
        )}
        {...props}
      >
        {children}
      </div>
    );
  }
);

CardFooter.displayName = 'CardFooter';

// Status Card variant for dashboard
interface StatusCardProps extends CardProps {
  status: 'active' | 'paused' | 'error' | 'success';
  value: string | number;
  label: string;
  icon?: React.ReactNode;
  trend?: {
    value: number;
    label: string;
    direction: 'up' | 'down' | 'neutral';
  };
}

const StatusCard = forwardRef<HTMLDivElement, StatusCardProps>(
  ({ status, value, label, icon, trend, className, ...props }, ref) => {
    const statusColors = {
      active: 'text-success-600 bg-success-50 border-success-200',
      paused: 'text-warning-600 bg-warning-50 border-warning-200',
      error: 'text-error-600 bg-error-50 border-error-200',
      success: 'text-success-600 bg-success-50 border-success-200',
    };

    const trendColors = {
      up: 'text-success-600',
      down: 'text-error-600',
      neutral: 'text-slate-600',
    };

    return (
      <div
        ref={ref}
        className={cn(
          'bg-white rounded-lg shadow-sm border border-slate-200 p-6',
          className
        )}
        {...props}
      >
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <div className="flex items-center space-x-3">
              {icon && (
                <div className={cn(
                  'p-2 rounded-md border',
                  statusColors[status]
                )}>
                  <div className="h-5 w-5">
                    {icon}
                  </div>
                </div>
              )}
              <div>
                <p className="text-sm font-medium text-slate-600">{label}</p>
                <p className="text-2xl font-bold text-slate-900">{value}</p>
              </div>
            </div>
          </div>

          {trend && (
            <div className="text-right">
              <div className={cn(
                'flex items-center text-sm font-medium',
                trendColors[trend.direction]
              )}>
                {trend.direction === 'up' && (
                  <svg className="h-4 w-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M5.293 9.707a1 1 0 010-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 01-1.414 1.414L11 7.414V15a1 1 0 11-2 0V7.414L6.707 9.707a1 1 0 01-1.414 0z" clipRule="evenodd" />
                  </svg>
                )}
                {trend.direction === 'down' && (
                  <svg className="h-4 w-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M14.707 10.293a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 111.414-1.414L9 12.586V5a1 1 0 012 0v7.586l2.293-2.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                )}
                {trend.value}
              </div>
              <p className="text-xs text-slate-500">{trend.label}</p>
            </div>
          )}
        </div>
      </div>
    );
  }
);

StatusCard.displayName = 'StatusCard';

export { Card, CardHeader, CardBody, CardFooter, StatusCard };
export type { CardProps, StatusCardProps };
