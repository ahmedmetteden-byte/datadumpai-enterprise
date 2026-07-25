import { UI_COPY } from '@/constants/ui';
import type { IntelligenceSource } from '@/types/intelligence';

const KIND_LABEL: Record<IntelligenceSource['kind'], string> = {
  document: 'Document',
  meeting: 'Meeting',
  report: 'Report',
  knowledge: 'Knowledge',
  web: 'Web',
};

export function SourceCard({
  source,
  onOpen,
}: {
  source: IntelligenceSource;
  onOpen: (source: IntelligenceSource) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onOpen(source)}
      className="w-full rounded-lg border border-surface-border bg-white p-3 text-left transition-colors hover:border-brand-200 hover:bg-brand-50/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
    >
      <div className="text-caption font-medium uppercase tracking-wide text-ink-faint">
        {KIND_LABEL[source.kind]}
      </div>
      <div className="mt-1 text-small font-medium text-ink">{source.title}</div>
      {source.excerpt ? (
        <p className="mt-1 line-clamp-3 text-caption text-ink-muted">
          {source.excerpt}
        </p>
      ) : null}
      <span className="mt-2 inline-block text-caption font-medium text-brand-600">
        {UI_COPY.studioOpenPreview} →
      </span>
    </button>
  );
}
