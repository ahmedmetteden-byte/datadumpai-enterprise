import { UI_COPY } from '@/constants/ui';

export function ThinkingIndicator() {
  return (
    <div
      className="flex items-center gap-2 rounded-lg bg-surface-alt px-3 py-2 text-small text-ink-muted"
      role="status"
      aria-live="polite"
    >
      <span className="inline-flex gap-1" aria-hidden>
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-brand-500" />
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-brand-500 [animation-delay:150ms]" />
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-brand-500 [animation-delay:300ms]" />
      </span>
      {UI_COPY.studioThinking}
    </div>
  );
}
