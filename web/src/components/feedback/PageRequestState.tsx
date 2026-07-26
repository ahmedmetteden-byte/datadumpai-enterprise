import type { ReactNode } from 'react';
import { Button } from '@/components/ui/Button';
import { UI_COPY } from '@/constants/ui';

/**
 * Full-page Loading / Error (+ Retry) gate for initial API loads.
 * Renders children once data is ready.
 */
export function PageRequestState({
  loading,
  error,
  onRetry,
  loadingMessage = UI_COPY.requestLoading,
  errorTitle = UI_COPY.requestError,
  children,
}: {
  loading: boolean;
  error: string | null;
  onRetry?: () => void;
  loadingMessage?: string;
  errorTitle?: string;
  children: ReactNode;
}) {
  if (loading) {
    return (
      <div
        className="flex min-h-[40vh] items-center justify-center text-small text-ink-muted"
        role="status"
        aria-live="polite"
      >
        {loadingMessage}
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-[40vh] flex-col items-center justify-center gap-3 text-center">
        <p className="text-body text-ink">{errorTitle}</p>
        <p className="max-w-md text-small text-ink-muted">{error}</p>
        {onRetry ? (
          <Button onClick={onRetry}>{UI_COPY.retry}</Button>
        ) : null}
      </div>
    );
  }

  return <>{children}</>;
}
