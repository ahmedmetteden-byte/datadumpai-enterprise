import { Button } from '@/components/ui/Button';
import { useRequestFeedback } from '@/context/RequestFeedbackContext';
import { UI_COPY } from '@/constants/ui';
import { cn } from '@/lib/cn';

const kindStyles = {
  loading: 'border-brand-200 bg-brand-50 text-brand-700',
  success: 'border-emerald-200 bg-emerald-50 text-success',
  error: 'border-danger/20 bg-red-50 text-danger',
} as const;

const kindLabel = {
  loading: UI_COPY.requestLoading,
  success: UI_COPY.requestSuccess,
  error: UI_COPY.requestErrorLabel,
} as const;

export function RequestFeedbackHost() {
  const { items, dismiss } = useRequestFeedback();

  if (items.length === 0) return null;

  return (
    <div
      className="pointer-events-none fixed bottom-4 right-4 z-[60] flex w-[min(100vw-2rem,22rem)] flex-col gap-2"
      aria-live="polite"
      aria-relevant="additions text"
    >
      {items.map((item) => (
        <div
          key={item.id}
          role={item.kind === 'error' ? 'alert' : 'status'}
          className={cn(
            'pointer-events-auto animate-slide-up rounded-lg border px-4 py-3 shadow-card',
            kindStyles[item.kind],
          )}
        >
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="text-caption font-semibold uppercase tracking-wide opacity-80">
                {kindLabel[item.kind]}
              </p>
              <p className="mt-1 text-small">{item.message}</p>
            </div>
            <button
              type="button"
              className="shrink-0 text-caption opacity-70 hover:opacity-100"
              aria-label={UI_COPY.requestDismiss}
              onClick={() => dismiss(item.id)}
            >
              ×
            </button>
          </div>
          {item.kind === 'error' && item.onRetry ? (
            <Button
              size="sm"
              variant="secondary"
              className="mt-3"
              onClick={() => {
                const retry = item.onRetry;
                dismiss(item.id);
                retry?.();
              }}
            >
              {UI_COPY.retry}
            </Button>
          ) : null}
        </div>
      ))}
    </div>
  );
}
