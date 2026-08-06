import { cn } from '@/lib/cn';
import type { ReactNode } from 'react';

export function EyebrowBadge({
  children,
  tone = 'light',
  className,
}: {
  children: ReactNode;
  tone?: 'light' | 'dark';
  className?: string;
}) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-eyebrow uppercase',
        tone === 'light'
          ? 'bg-surface-alt text-ink-muted'
          : 'bg-white/10 text-white/80',
        className,
      )}
    >
      <span
        aria-hidden
        className={cn(
          'h-1.5 w-1.5 rounded-full',
          tone === 'light' ? 'bg-brand-500' : 'bg-accent',
        )}
      />
      {children}
    </span>
  );
}
