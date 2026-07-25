import { Link } from 'react-router-dom';
import { cn } from '@/lib/cn';
import type { QuickAction } from '@/types/home';

const ICONS: Record<QuickAction['icon'], string> = {
  upload: '↑',
  report: '▣',
  copilot: '✦',
  export: '⇩',
  search: '⌕',
};

export function ActionCard({
  action,
  className,
}: {
  action: QuickAction;
  className?: string;
}) {
  return (
    <Link
      to={action.href}
      className={cn(
        'group flex min-h-[7.5rem] flex-col justify-between rounded-lg border border-surface-border bg-white p-5',
        'transition-all duration-200 hover:-translate-y-0.5 hover:border-brand-200 hover:shadow-card',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500',
        className,
      )}
    >
      <span
        aria-hidden
        className="inline-flex h-10 w-10 items-center justify-center rounded-md bg-brand-50 text-brand-600 transition-colors group-hover:bg-brand-100"
      >
        {ICONS[action.icon]}
      </span>
      <div>
        <div className="text-card text-ink">{action.label}</div>
        <p className="mt-1 text-small text-ink-muted">{action.description}</p>
      </div>
    </Link>
  );
}
