import { cn } from '@/lib/cn';
import type { HTMLAttributes, ReactNode } from 'react';

export function Badge({
  children,
  className,
  tone = 'neutral',
  ...props
}: HTMLAttributes<HTMLSpanElement> & {
  children: ReactNode;
  tone?: 'neutral' | 'brand' | 'success' | 'warning';
}) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2 py-0.5 text-caption font-medium',
        tone === 'neutral' && 'bg-surface-alt text-ink-muted',
        tone === 'brand' && 'bg-brand-50 text-brand-700',
        tone === 'success' && 'bg-emerald-50 text-success',
        tone === 'warning' && 'bg-amber-50 text-warning',
        className,
      )}
      {...props}
    >
      {children}
    </span>
  );
}
