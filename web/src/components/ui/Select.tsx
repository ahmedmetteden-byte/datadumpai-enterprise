import { cn } from '@/lib/cn';
import type { SelectHTMLAttributes } from 'react';
import { forwardRef } from 'react';

export const Select = forwardRef<
  HTMLSelectElement,
  SelectHTMLAttributes<HTMLSelectElement>
>(function Select({ className, children, ...props }, ref) {
  return (
    <select
      ref={ref}
      className={cn(
        'h-10 appearance-none rounded-md border border-surface-border bg-white pl-3 pr-9 text-small text-ink',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500',
        className,
      )}
      {...props}
    >
      {children}
    </select>
  );
});
