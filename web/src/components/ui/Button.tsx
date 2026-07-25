import { cn } from '@/lib/cn';
import type { ButtonHTMLAttributes, ReactNode } from 'react';

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger';
type Size = 'sm' | 'md' | 'lg';

const variantClass: Record<Variant, string> = {
  primary:
    'bg-brand-500 text-white hover:bg-brand-600 shadow-sm focus-visible:ring-brand-500',
  secondary:
    'bg-white text-ink border border-surface-border hover:bg-surface-alt focus-visible:ring-brand-500',
  ghost:
    'bg-transparent text-ink-muted hover:bg-surface-alt hover:text-ink focus-visible:ring-brand-500',
  danger:
    'bg-danger text-white hover:bg-red-700 focus-visible:ring-danger',
};

const sizeClass: Record<Size, string> = {
  sm: 'h-9 px-3 text-small',
  md: 'h-10 px-4 text-body',
  lg: 'h-11 px-5 text-body',
};

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
}

export function Button({
  className,
  variant = 'primary',
  size = 'md',
  leftIcon,
  rightIcon,
  children,
  type = 'button',
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      className={cn(
        'inline-flex items-center justify-center gap-2 rounded-md font-medium transition-colors duration-200',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2',
        'disabled:pointer-events-none disabled:opacity-50',
        variantClass[variant],
        sizeClass[size],
        className,
      )}
      {...props}
    >
      {leftIcon}
      {children}
      {rightIcon}
    </button>
  );
}
