import { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { UI_COPY } from '@/constants/ui';
import { placeholderForMode } from '@/lib/intelligence';
import { ReasoningModeTabs } from './ReasoningModeTabs';
import type { ReasoningMode } from '@/types/intelligence';

export function PromptComposer({
  mode,
  onModeChange,
  disabled,
  sending,
  onSend,
}: {
  mode: ReasoningMode;
  onModeChange: (mode: ReasoningMode) => void;
  disabled?: boolean;
  sending?: boolean;
  onSend: (value: string) => void;
}) {
  const [value, setValue] = useState('');

  function submit() {
    if (!value.trim() || disabled || sending) return;
    onSend(value.trim());
    setValue('');
  }

  return (
    <div className="border-t border-surface-border bg-white p-4">
      <ReasoningModeTabs value={mode} onChange={onModeChange} />
      <label htmlFor="studio-composer" className="sr-only">
        {UI_COPY.studioComposerLabel}
      </label>
      <div className="mt-3 flex items-end gap-2">
        <textarea
          id="studio-composer"
          rows={2}
          value={value}
          disabled={disabled || sending}
          placeholder={placeholderForMode(mode)}
          onChange={(event) => setValue(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault();
              submit();
            }
          }}
          className="min-h-[2.75rem] flex-1 resize-none rounded-lg border border-surface-border bg-white px-3 py-2.5 text-body text-ink shadow-sm placeholder:text-ink-faint focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 disabled:opacity-60"
        />
        <Button
          onClick={submit}
          disabled={disabled || sending || !value.trim()}
        >
          {sending ? UI_COPY.studioSending : UI_COPY.studioSend}
        </Button>
      </div>
    </div>
  );
}
