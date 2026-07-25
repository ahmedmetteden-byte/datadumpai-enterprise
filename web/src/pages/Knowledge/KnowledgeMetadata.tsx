import { UI_COPY } from '@/constants/ui';
import {
  formatKnowledgeDate,
  KNOWLEDGE_TYPE_SINGULAR,
  PROCESSING_STATUS_LABELS,
} from '@/lib/knowledgeLabels';
import type { KnowledgeDetail } from '@/types/knowledge';

export function KnowledgeMetadata({ detail }: { detail: KnowledgeDetail }) {
  const rows: Array<{ label: string; value: string }> = [
    { label: UI_COPY.knowledgeMetaType, value: KNOWLEDGE_TYPE_SINGULAR[detail.type] },
    {
      label: UI_COPY.knowledgeMetaStatus,
      value: PROCESSING_STATUS_LABELS[detail.status],
    },
    {
      label: UI_COPY.knowledgeMetaAuthor,
      value: detail.authorName ?? '—',
    },
    {
      label: UI_COPY.knowledgeMetaProject,
      value: detail.projectName ?? '—',
    },
    {
      label: UI_COPY.knowledgeMetaUpdated,
      value: formatKnowledgeDate(detail.updatedAt),
    },
    {
      label: UI_COPY.knowledgeMetaCreated,
      value: formatKnowledgeDate(detail.createdAt),
    },
  ];

  if (detail.filename) {
    rows.push({ label: UI_COPY.knowledgeMetaFilename, value: detail.filename });
  }
  if (detail.mimeType) {
    rows.push({ label: UI_COPY.knowledgeMetaMime, value: detail.mimeType });
  }
  if (typeof detail.sizeBytes === 'number') {
    rows.push({
      label: UI_COPY.knowledgeMetaSize,
      value: `${(detail.sizeBytes / 1_000_000).toFixed(1)} MB`,
    });
  }

  return (
    <section aria-label={UI_COPY.knowledgeMetadata}>
      <h3 className="text-caption font-semibold uppercase tracking-wide text-ink-muted">
        {UI_COPY.knowledgeMetadata}
      </h3>
      <dl className="mt-3 space-y-2">
        {rows.map((row) => (
          <div
            key={row.label}
            className="flex items-start justify-between gap-3 text-small"
          >
            <dt className="text-ink-muted">{row.label}</dt>
            <dd className="text-right font-medium text-ink">{row.value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
