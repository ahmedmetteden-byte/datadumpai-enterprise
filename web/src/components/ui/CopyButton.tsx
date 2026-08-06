import { useState } from 'react';
import { cn } from '@/lib/cn';
import { UI_COPY } from '@/constants/ui';

export function CopyButton({
  text,
  label,
  className,
}: {
  text: string;
  label?: string;
  className?: string;
}) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      /* clipboard access denied — silently no-op */
    }
  }

  return (
    <button
      type="button"
      onClick={() => void handleCopy()}
      className={cn(
        'inline-flex items-center gap-1 text-caption font-medium text-ink-muted transition-colors hover:text-ink',
        className,
      )}
    >
      <span aria-hidden>{copied ? '✓' : '⧉'}</span>
      {copied ? UI_COPY.copied : (label ?? UI_COPY.copy)}
    </button>
  );
}
