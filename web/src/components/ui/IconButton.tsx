import { cn } from '@/lib/cn';
import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react';

export interface IconButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement> {
  label: string;
  children: ReactNode;
  tone?: 'default' | 'onDark';
}

export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(
  function IconButton(
    { label, children, className, tone = 'default', type = 'button', ...props },
    ref,
  ) {
    return (
      <button
        ref={ref}
        type={type}
        aria-label={label}
        title={label}
        className={cn(
          'relative inline-flex h-10 w-10 items-center justify-center rounded-md transition-colors',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2',
          tone === 'default' &&
            'text-ink-muted hover:bg-surface-alt hover:text-ink',
          tone === 'onDark' &&
            'text-white/90 hover:bg-white/15 hover:text-white',
          className,
        )}
        {...props}
      >
        {children}
      </button>
    );
  },
);
