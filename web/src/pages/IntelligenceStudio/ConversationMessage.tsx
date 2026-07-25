import { UI_COPY } from '@/constants/ui';
import { ConfidenceBadge } from './ConfidenceBadge';
import { ThinkingIndicator } from './ThinkingIndicator';
import type { IntelligenceMessage } from '@/types/intelligence';

export function ConversationMessage({
  message,
  onFollowUp,
  onSelectSources,
}: {
  message: IntelligenceMessage;
  onFollowUp?: (prompt: string) => void;
  onSelectSources?: () => void;
}) {
  if (message.role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-2xl rounded-br-md bg-brand-500 px-4 py-3 text-body text-white">
          {message.content}
        </div>
      </div>
    );
  }

  if (message.status === 'streaming') {
    return (
      <div className="max-w-[90%] space-y-3">
        <ThinkingIndicator />
        <div className="h-16 animate-pulse rounded-xl bg-surface-alt" />
      </div>
    );
  }

  if (message.status === 'error') {
    return (
      <div className="max-w-[90%] rounded-xl border border-danger/20 bg-red-50 px-4 py-3 text-small text-danger">
        {message.answer ?? UI_COPY.studioSendError}
      </div>
    );
  }

  return (
    <article className="max-w-[90%] space-y-4 rounded-xl border border-surface-border bg-white p-4 shadow-sm">
      <section>
        <h3 className="text-caption uppercase tracking-wide text-ink-faint">
          {UI_COPY.studioAnswer}
        </h3>
        <p className="mt-2 whitespace-pre-wrap text-body text-ink">
          {message.answer ?? message.content}
        </p>
      </section>

      {message.evidence ? (
        <section>
          <h3 className="text-caption uppercase tracking-wide text-ink-faint">
            {UI_COPY.studioEvidence}
          </h3>
          <p className="mt-2 text-small text-ink-muted">{message.evidence}</p>
        </section>
      ) : null}

      {typeof message.confidence === 'number' ? (
        <section>
          <h3 className="mb-2 text-caption uppercase tracking-wide text-ink-faint">
            {UI_COPY.studioConfidence}
          </h3>
          <ConfidenceBadge value={message.confidence} />
        </section>
      ) : null}

      {message.followUps && message.followUps.length > 0 ? (
        <section>
          <h3 className="mb-2 text-caption uppercase tracking-wide text-ink-faint">
            {UI_COPY.studioFollowUps}
          </h3>
          <ul className="space-y-2">
            {message.followUps.map((item) => (
              <li key={item}>
                <button
                  type="button"
                  onClick={() => onFollowUp?.(item)}
                  className="text-left text-small font-medium text-brand-600 hover:text-brand-700"
                >
                  {item}
                </button>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {message.sources && message.sources.length > 0 ? (
        <section>
          <h3 className="mb-2 text-caption uppercase tracking-wide text-ink-faint">
            {UI_COPY.studioSources}
          </h3>
          <button
            type="button"
            onClick={onSelectSources}
            className="text-small text-ink-muted hover:text-ink"
          >
            {message.sources.length} {UI_COPY.studioSourcesCount}
          </button>
        </section>
      ) : null}

      {message.notice ? (
        <p className="text-caption text-warning">{message.notice}</p>
      ) : null}
    </article>
  );
}
