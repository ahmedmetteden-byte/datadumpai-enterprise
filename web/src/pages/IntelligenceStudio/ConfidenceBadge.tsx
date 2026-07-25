import { cn } from '@/lib/cn';
import { formatPercent } from '@/lib/format';

export function ConfidenceBadge({
  value,
  className,
}: {
  value: number;
  className?: string;
}) {
  const percent = Math.round(value * 100);
  const tone =
    percent >= 80 ? 'text-success' : percent >= 60 ? 'text-warning' : 'text-danger';

  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full bg-surface-alt px-2 py-0.5 text-caption font-medium',
        tone,
        className,
      )}
    >
      {formatPercent(percent)} confidence
    </span>
  );
}
