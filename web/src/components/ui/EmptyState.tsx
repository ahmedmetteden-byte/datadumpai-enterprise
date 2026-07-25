import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/cn';
import type { ReactNode } from 'react';

export function EmptyState({
  title,
  description,
  actionLabel,
  onAction,
  actionHref,
  icon,
  className,
}: {
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  actionHref?: string;
  icon?: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center rounded-xl border border-dashed border-surface-border bg-white/80 px-6 py-14 text-center',
        className,
      )}
      role="status"
    >
      {icon ? (
        <div
          aria-hidden
          className="mb-5 flex h-14 w-14 items-center justify-center rounded-xl bg-brand-50 text-2xl text-brand-600"
        >
          {icon}
        </div>
      ) : null}
      <h3 className="max-w-md text-section text-ink">{title}</h3>
      <p className="mt-2 max-w-md text-small text-ink-muted">{description}</p>
      {actionLabel && actionHref ? (
        <Link
          to={actionHref}
          className="mt-6 inline-flex h-10 items-center justify-center rounded-md bg-brand-500 px-4 text-body font-medium text-white transition-colors hover:bg-brand-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2"
        >
          {actionLabel}
        </Link>
      ) : null}
      {actionLabel && onAction && !actionHref ? (
        <Button className="mt-6" onClick={onAction}>
          {actionLabel}
        </Button>
      ) : null}
    </div>
  );
}
