import { Link } from 'react-router-dom';
import { Badge } from '@/components/ui/Badge';
import { UI_COPY } from '@/constants/ui';
import { cn } from '@/lib/cn';
import { formatRelativeTime } from '@/lib/format';
import type { ContinueWorkingItem } from '@/types/home';

export function WorkspaceCard({
  item,
  className,
}: {
  item: ContinueWorkingItem;
  className?: string;
}) {
  return (
    <Link
      to={item.href}
      className={cn(
        'block rounded-lg border border-surface-border bg-white p-5 transition-all duration-200',
        'hover:-translate-y-0.5 hover:border-brand-200 hover:shadow-card',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500',
        className,
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="truncate text-card text-ink">{item.title}</h3>
          <p className="mt-1 truncate text-small text-ink-muted">
            {item.subtitle}
          </p>
        </div>
        <Badge tone="neutral">{item.kind}</Badge>
      </div>

      {typeof item.progressPercent === 'number' ? (
        <div className="mt-4">
          <div className="mb-1.5 flex justify-between text-caption text-ink-muted">
            <span>{UI_COPY.progress}</span>
            <span>{item.progressPercent}%</span>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-surface-alt">
            <div
              className="h-full rounded-full bg-brand-500 transition-all"
              style={{ width: `${item.progressPercent}%` }}
            />
          </div>
        </div>
      ) : null}

      <p className="mt-4 text-caption text-ink-faint">
        {UI_COPY.lastUpdated} {formatRelativeTime(item.updatedAt)}
      </p>
    </Link>
  );
}
