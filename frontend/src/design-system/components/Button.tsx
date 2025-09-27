/**
 * Button Component - Skylapse Design System
 * Professional Mountain Timelapse Camera System
 */

import { forwardRef } from 'react';
import { cn } from '@/utils';
import type { ButtonProps } from '@/api/types';

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({
    children,
    className,
    variant = 'primary',
    size = 'md',
    disabled = false,
    loading = false,
    onClick,
    ...props
  }, ref) => {
    const baseStyles = `
      inline-flex items-center justify-center font-medium rounded-md shadow-sm
      transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2
      disabled:opacity-50 disabled:cursor-not-allowed
    `;

    const variants = {
      primary: `
        text-white bg-mountain-600 border border-transparent
        hover:bg-mountain-700 focus:ring-mountain-500
        active:bg-mountain-800
      `,
      secondary: `
        text-slate-700 bg-white border border-slate-300
        hover:bg-slate-50 focus:ring-mountain-500
        active:bg-slate-100
      `,
      outline: `
        text-mountain-600 bg-transparent border border-mountain-300
        hover:bg-mountain-50 focus:ring-mountain-500
        active:bg-mountain-100
      `,
      ghost: `
        text-mountain-600 bg-transparent border border-transparent
        hover:bg-mountain-50 focus:ring-mountain-500
        active:bg-mountain-100
      `,
      golden: `
        text-golden-900 bg-golden-400 border border-transparent
        hover:bg-golden-500 focus:ring-golden-500
        active:bg-golden-600
      `,
    };

    const sizes = {
      sm: 'px-3 py-1.5 text-sm leading-4',
      md: 'px-4 py-2 text-sm leading-5',
      lg: 'px-6 py-3 text-base leading-6',
    };

    const buttonClasses = cn(
      baseStyles,
      variants[variant],
      sizes[size],
      loading && 'cursor-wait',
      className
    );

    return (
      <button
        ref={ref}
        className={buttonClasses}
        disabled={disabled || loading}
        onClick={onClick}
        {...props}
      >
        {loading && (
          <svg
            className="animate-spin -ml-1 mr-2 h-4 w-4"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
        )}
        {children}
      </button>
    );
  }
);

Button.displayName = 'Button';

export { Button };
export type { ButtonProps };
