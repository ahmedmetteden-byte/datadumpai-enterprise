import { UI_COPY } from '@/constants/ui';

export function SuggestedPrompts({
  prompts,
  onSelect,
}: {
  prompts: string[];
  onSelect: (prompt: string) => void;
}) {
  if (prompts.length === 0) return null;

  return (
    <div>
      <p className="mb-2 text-caption uppercase tracking-wide text-ink-faint">
        {UI_COPY.studioSuggestedPrompts}
      </p>
      <div className="flex flex-wrap gap-2">
        {prompts.map((prompt) => (
          <button
            key={prompt}
            type="button"
            onClick={() => onSelect(prompt)}
            className="rounded-lg border border-surface-border bg-white px-3 py-2 text-left text-small text-ink transition-colors hover:border-brand-200 hover:bg-brand-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
          >
            {prompt}
          </button>
        ))}
      </div>
    </div>
  );
}
