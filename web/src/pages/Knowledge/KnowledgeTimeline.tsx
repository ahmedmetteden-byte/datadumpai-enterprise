import { UI_COPY } from '@/constants/ui';
import { formatKnowledgeDateTime } from '@/lib/knowledgeLabels';
import type { KnowledgeTimelineEvent } from '@/types/knowledge';

export function KnowledgeTimeline({
  events,
}: {
  events: KnowledgeTimelineEvent[];
}) {
  return (
    <section aria-label={UI_COPY.knowledgeTimeline}>
      <h3 className="text-caption font-semibold uppercase tracking-wide text-ink-muted">
        {UI_COPY.knowledgeTimeline}
      </h3>
      <ol className="mt-3 space-y-3 border-l border-surface-border pl-4">
        {events.map((event) => (
          <li key={event.id} className="relative">
            <span
              aria-hidden
              className="absolute -left-[1.15rem] top-1.5 h-2.5 w-2.5 rounded-full bg-brand-500"
            />
            <p className="text-small font-medium text-ink">{event.label}</p>
            <p className="text-caption text-ink-muted">
              {formatKnowledgeDateTime(event.at)}
              {event.detail ? ` · ${event.detail}` : ''}
            </p>
          </li>
        ))}
      </ol>
    </section>
  );
}
