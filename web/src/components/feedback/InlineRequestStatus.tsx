import { Button } from '@/components/ui/Button';
import { Spinner } from '@/components/ui/Spinner';
import { UI_COPY } from '@/constants/ui';
import { cn } from '@/lib/cn';

export type InlineStatusKind = 'loading' | 'success' | 'error' | null;

/**
 * Inline banner for in-page API feedback: Loading… / Success / Error + Retry.
 */
export function InlineRequestStatus({
  kind,
  message,
  onRetry,
  className,
}: {
  kind: InlineStatusKind;
  message?: string | null;
  onRetry?: () => void;
  className?: string;
}) {
  if (!kind) return null;

  const resolved =
    message ||
    (kind === 'loading'
      ? UI_COPY.requestLoading
      : kind === 'success'
        ? UI_COPY.requestSuccess
        : UI_COPY.requestError);

  return (
    <div
      role={kind === 'error' ? 'alert' : 'status'}
      aria-live="polite"
      className={cn(
        'rounded-lg border px-4 py-3 text-small',
        kind === 'loading' && 'border-brand-200 bg-brand-50 text-brand-700',
        kind === 'success' && 'border-emerald-200 bg-emerald-50 text-success',
        kind === 'error' && 'border-danger/20 bg-red-50 text-danger',
        className,
      )}
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-start gap-2.5">
          {kind === 'loading' ? <Spinner size={16} className="mt-0.5 shrink-0" /> : null}
          <div>
            <p className="text-caption font-semibold uppercase tracking-wide opacity-80">
              {kind === 'loading'
                ? UI_COPY.requestLoading
                : kind === 'success'
                  ? UI_COPY.requestSuccess
                  : UI_COPY.requestErrorLabel}
            </p>
            <p className="mt-0.5">{resolved}</p>
          </div>
        </div>
        {kind === 'error' && onRetry ? (
          <Button size="sm" variant="secondary" onClick={onRetry}>
            {UI_COPY.retry}
          </Button>
        ) : null}
      </div>
    </div>
  );
}
