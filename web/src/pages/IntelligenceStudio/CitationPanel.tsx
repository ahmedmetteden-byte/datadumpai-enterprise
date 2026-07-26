import { UI_COPY } from '@/constants/ui';
import { ConfidenceBadge } from './ConfidenceBadge';
import { SourceCard } from './SourceCard';
import type {
  IntelligenceCitation,
  IntelligenceSource,
} from '@/types/intelligence';

export function CitationPanel({
  sources,
  citations = [],
  confidence,
  onOpenSource,
}: {
  sources: IntelligenceSource[];
  citations?: IntelligenceCitation[];
  confidence?: number;
  onOpenSource: (source: IntelligenceSource) => void;
}) {
  const documents = sources.filter((item) => item.kind === 'document');
  const meetings = sources.filter((item) => item.kind === 'meeting');
  const reports = sources.filter((item) => item.kind === 'report');
  const other = sources.filter(
    (item) =>
      item.kind !== 'document' &&
      item.kind !== 'meeting' &&
      item.kind !== 'report',
  );

  return (
    <aside
      className="flex h-full min-h-0 flex-col border-l border-surface-border bg-white"
      aria-label={UI_COPY.studioEvidence}
    >
      <div className="border-b border-surface-border px-4 py-4">
        <h2 className="text-card text-ink">{UI_COPY.studioEvidence}</h2>
        <p className="mt-1 text-caption text-ink-muted">
          {UI_COPY.studioEvidenceSubtitle}
        </p>
        {typeof confidence === 'number' ? (
          <div className="mt-3">
            <ConfidenceBadge value={confidence} />
          </div>
        ) : null}
      </div>

      <div className="min-h-0 flex-1 space-y-5 overflow-y-auto p-4">
        {sources.length === 0 && citations.length === 0 ? (
          <p className="text-small text-ink-muted">{UI_COPY.studioNoEvidence}</p>
        ) : (
          <>
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
                    </li>
                  ))}
                </ol>
              </section>
            ) : null}

            <SourceGroup
              title={UI_COPY.studioLinkedDocuments}
              items={documents}
              onOpen={onOpenSource}
            />
            <SourceGroup
              title={UI_COPY.studioReferencedMeetings}
              items={meetings}
              onOpen={onOpenSource}
            />
            <SourceGroup
              title={UI_COPY.studioReferencedReports}
              items={reports}
              onOpen={onOpenSource}
            />
            <SourceGroup
              title={UI_COPY.studioSources}
              items={other}
              onOpen={onOpenSource}
            />
          </>
        )}
      </div>
    </aside>
  );
}

function SourceGroup({
  title,
  items,
  onOpen,
}: {
  title: string;
  items: IntelligenceSource[];
  onOpen: (source: IntelligenceSource) => void;
}) {
  if (items.length === 0) return null;
  return (
    <section>
      <h3 className="mb-2 text-caption uppercase tracking-wide text-ink-faint">
        {title}
      </h3>
      <div className="space-y-2">
        {items.map((source) => (
          <SourceCard key={source.id} source={source} onOpen={onOpen} />
        ))}
      </div>
    </section>
  );
}
