/**
 * Input Component - Skylapse Design System
 * Professional Mountain Timelapse Camera System
 */

import { forwardRef } from 'react';
import { cn } from '@/utils';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  variant?: 'default' | 'filled';
}

const Input = forwardRef<HTMLInputElement, InputProps>(
  ({
    className,
    type = 'text',
    label,
    error,
    helperText,
    leftIcon,
    rightIcon,
    variant = 'default',
    disabled,
    id,
    ...props
  }, ref) => {
    const inputId = id || `input-${Math.random().toString(36).substr(2, 9)}`;

    const baseStyles = `
      block w-full rounded-md shadow-sm transition-colors duration-200
      focus:ring-2 focus:ring-offset-2 focus:ring-mountain-500
      disabled:opacity-50 disabled:cursor-not-allowed
      placeholder:text-slate-400
    `;

    const variants = {
      default: `
        border border-slate-300 bg-white text-slate-900
        hover:border-slate-400 focus:border-mountain-500
      `,
      filled: `
        border border-transparent bg-slate-100 text-slate-900
        hover:bg-slate-200 focus:bg-white focus:border-mountain-500
      `,
    };

    const stateStyles = error
      ? 'border-error-300 focus:border-error-500 focus:ring-error-500'
      : variants[variant];

    const inputClasses = cn(
      baseStyles,
      stateStyles,
      leftIcon && 'pl-10',
      rightIcon && 'pr-10',
      'h-10 px-3 py-2',
      className
    );

    return (
      <div className="space-y-1">
        {label && (
          <label
            htmlFor={inputId}
            className="block text-sm font-medium text-slate-700"
          >
            {label}
          </label>
        )}

        <div className="relative">
          {leftIcon && (
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <div className="h-5 w-5 text-slate-400">
                {leftIcon}
              </div>
            </div>
          )}

          <input
            ref={ref}
            type={type}
            id={inputId}
            className={inputClasses}
            disabled={disabled}
            {...props}
          />

          {rightIcon && (
            <div className="absolute inset-y-0 right-0 pr-3 flex items-center">
              <div className="h-5 w-5 text-slate-400">
                {rightIcon}
              </div>
            </div>
          )}
        </div>

        {(error || helperText) && (
          <div className="text-sm">
            {error ? (
              <p className="text-error-600">{error}</p>
            ) : (
              <p className="text-slate-500">{helperText}</p>
            )}
          </div>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';

export { Input };
