import { greetingForNow } from '@/lib/intelligence';
import { UI_COPY } from '@/constants/ui';
import { SuggestedPrompts } from './SuggestedPrompts';

export function EmptyConversation({
  prompts,
  onSelectPrompt,
}: {
  prompts: string[];
  onSelectPrompt: (prompt: string) => void;
}) {
  return (
    <div className="mx-auto flex max-w-xl flex-col justify-center px-2 py-10">
      <p className="text-caption uppercase tracking-[0.14em] text-ink-faint">
        {UI_COPY.studioTitle}
      </p>
      <h2 className="mt-3 text-page-title text-ink">{greetingForNow()}</h2>
      <p className="mt-2 text-body text-ink-muted">
        {UI_COPY.studioEmptySubtitle}
      </p>
      <div className="mt-8">
        <SuggestedPrompts prompts={prompts} onSelect={onSelectPrompt} />
      </div>
    </div>
  );
}
