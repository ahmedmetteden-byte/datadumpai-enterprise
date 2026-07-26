import { UI_COPY } from '@/constants/ui';
import { ConfidenceBadge } from './ConfidenceBadge';
import { SourceCard } from './SourceCard';
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
        {message.notice ? (
          <p className="mt-2 text-caption">{message.notice}</p>
        ) : null}
      </div>
    );
  }

  const linked =
    message.linkedDocuments && message.linkedDocuments.length > 0
      ? message.linkedDocuments
      : (message.sources ?? []).filter((item) => item.kind === 'document');
  const citations = message.citations ?? [];

  return (
    <article className="max-w-[92%] space-y-5 rounded-xl border border-surface-border bg-white p-4 shadow-sm sm:p-5">
      <header className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-caption uppercase tracking-wide text-ink-faint">
          {UI_COPY.studioAnswer}
        </h3>
        {typeof message.confidence === 'number' ? (
          <ConfidenceBadge value={message.confidence} />
        ) : null}
      </header>

      <section>
        <p className="whitespace-pre-wrap text-body leading-relaxed text-ink">
          {message.answer ?? message.content}
        </p>
      </section>

      {message.evidence ? (
        <section className="rounded-lg bg-surface-alt/60 px-3 py-3">
          <h3 className="text-caption uppercase tracking-wide text-ink-faint">
            {UI_COPY.studioEvidence}
          </h3>
          <p className="mt-2 text-small text-ink-muted">{message.evidence}</p>
        </section>
      ) : null}

      {citations.length > 0 ? (
        <section>
          <h3 className="mb-2 text-caption uppercase tracking-wide text-ink-faint">
            {UI_COPY.studioCitations}
          </h3>
          <ol className="space-y-2">
            {citations.map((citation) => (
              <li
                key={citation.id}
                className="rounded-lg border border-surface-border px-3 py-2"
              >
                <div className="flex items-baseline gap-2">
                  <span className="text-caption font-semibold text-brand-600">
                    [{citation.index}]
                  </span>
                  <span className="text-small font-medium text-ink">
                    {citation.label}
                  </span>
                </div>
                <p className="mt-1 text-caption text-ink-muted">
                  “{citation.quote}”
                </p>
                {citation.location ? (
                  <p className="mt-1 font-mono text-caption text-ink-faint">
                    {citation.location}
                  </p>
                ) : null}
              </li>
            ))}
          </ol>
        </section>
      ) : null}

      {linked.length > 0 ? (
        <section>
          <div className="mb-2 flex items-center justify-between gap-2">
            <h3 className="text-caption uppercase tracking-wide text-ink-faint">
              {UI_COPY.studioLinkedDocuments}
            </h3>
            <button
              type="button"
              onClick={onSelectSources}
              className="text-caption font-medium text-brand-600 hover:text-brand-700"
            >
              {UI_COPY.studioOpenSources}
            </button>
          </div>
          <div className="grid gap-2 sm:grid-cols-2">
            {linked.slice(0, 4).map((source) => (
              <SourceCard
                key={source.id}
                source={source}
                onOpen={() => onSelectSources?.()}
              />
            ))}
          </div>
        </section>
      ) : message.sources && message.sources.length > 0 ? (
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

      {message.notice ? (
        <p className="text-caption text-warning">{message.notice}</p>
      ) : null}
    </article>
  );
}
