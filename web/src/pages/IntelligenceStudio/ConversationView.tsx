import { useEffect, useRef } from 'react';
import { Badge } from '@/components/ui/Badge';
import { UI_COPY } from '@/constants/ui';
import { ConversationMessage } from './ConversationMessage';
import { EmptyConversation } from './EmptyConversation';
import { PromptComposer } from './PromptComposer';
import type {
  IntelligenceConversation,
  IntelligenceMessage as Message,
  ReasoningMode,
  StudioReadiness,
} from '@/types/intelligence';

export function ConversationView({
  workspaceName,
  readiness,
  conversation,
  suggestions,
  mode,
  sending,
  disabled,
  onModeChange,
  onSend,
  onSelectSources,
}: {
  workspaceName: string | null;
  readiness: StudioReadiness | null;
  conversation: IntelligenceConversation | null;
  suggestions: string[];
  mode: ReasoningMode;
  sending: boolean;
  disabled: boolean;
  onModeChange: (mode: ReasoningMode) => void;
  onSend: (content: string) => void;
  onSelectSources: (message: Message) => void;
}) {
  const endRef = useRef<HTMLDivElement>(null);
  const messages = conversation?.messages ?? [];
  const isEmpty = messages.length === 0;

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages.length, sending]);

  return (
    <section
      className="flex min-h-0 min-w-0 flex-1 flex-col bg-canvas/40"
      aria-label={UI_COPY.studioConversation}
    >
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-surface-border bg-white px-4 py-3 sm:px-5">
        <div className="min-w-0">
          <h1 className="truncate text-section text-ink">
            {conversation?.title ?? UI_COPY.studioTitle}
          </h1>
          <p className="mt-0.5 text-caption text-ink-muted">
            {readiness?.status ?? UI_COPY.studioCheckingReadiness}
          </p>
        </div>
        {workspaceName ? (
          <Badge tone="brand">{workspaceName}</Badge>
        ) : null}
      </header>

      <div
        className="min-h-0 flex-1 space-y-4 overflow-y-auto px-4 py-5 sm:px-6"
        role="log"
        aria-live="polite"
        aria-relevant="additions"
      >
        {isEmpty ? (
          <EmptyConversation prompts={suggestions} onSelectPrompt={onSend} />
        ) : (
          messages.map((message) => (
            <ConversationMessage
              key={message.id}
              message={message}
              onFollowUp={onSend}
              onSelectSources={() => onSelectSources(message)}
            />
          ))
        )}
        <div ref={endRef} />
      </div>

      <PromptComposer
        mode={mode}
        onModeChange={onModeChange}
        disabled={disabled}
        sending={sending}
        onSend={onSend}
      />
    </section>
  );
}
