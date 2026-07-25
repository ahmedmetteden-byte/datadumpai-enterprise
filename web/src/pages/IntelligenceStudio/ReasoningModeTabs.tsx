import { cn } from '@/lib/cn';
import { REASONING_MODES } from '@/lib/intelligence';
import type { ReasoningMode } from '@/types/intelligence';

export function ReasoningModeTabs({
  value,
  onChange,
}: {
  value: ReasoningMode;
  onChange: (mode: ReasoningMode) => void;
}) {
  return (
    <div
      role="tablist"
      aria-label="Reasoning mode"
      className="flex gap-1 overflow-x-auto pb-1"
    >
      {REASONING_MODES.map((mode) => {
        const selected = mode.id === value;
        return (
          <button
            key={mode.id}
            type="button"
            role="tab"
            aria-selected={selected}
            onClick={() => onChange(mode.id)}
            className={cn(
              'shrink-0 rounded-md px-3 py-1.5 text-caption font-medium transition-colors',
              selected
                ? 'bg-brand-50 text-brand-700'
                : 'text-ink-muted hover:bg-surface-alt hover:text-ink',
            )}
          >
            {mode.label}
          </button>
        );
      })}
    </div>
  );
}
