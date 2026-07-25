import { ProcessingBadge } from '@/pages/Knowledge/ProcessingBadge';
import { KnowledgeMetadata } from '@/pages/Knowledge/KnowledgeMetadata';
import { KnowledgeRelationships } from '@/pages/Knowledge/KnowledgeRelationships';
import { KnowledgeTimeline } from '@/pages/Knowledge/KnowledgeTimeline';
import { UI_COPY } from '@/constants/ui';
import { KNOWLEDGE_TYPE_SINGULAR } from '@/lib/knowledgeLabels';
import type {
  KnowledgeDetail,
  KnowledgeProcessingStatus,
} from '@/types/knowledge';

export function KnowledgePreview({
  detail,
  processing,
  loading,
  onOpenRelated,
}: {
  detail: KnowledgeDetail | null;
  processing: KnowledgeProcessingStatus | null;
  loading: boolean;
  onOpenRelated: (id: string) => void;
}) {
  if (loading) {
    return (
      <div
        className="rounded-xl border border-surface-border bg-white p-6 text-small text-ink-muted"
        role="status"
      >
        {UI_COPY.knowledgeLoadingPreview}
      </div>
    );
  }

  if (!detail) {
    return (
      <div className="rounded-xl border border-dashed border-surface-border bg-white/70 p-6 text-center">
        <p className="text-section text-ink">{UI_COPY.knowledgePreviewEmptyTitle}</p>
        <p className="mt-1 text-small text-ink-muted">
          {UI_COPY.knowledgePreviewEmptyDescription}
        </p>
      </div>
    );
  }

  return (
    <aside
      className="space-y-6 rounded-xl border border-surface-border bg-white p-5"
      aria-label={UI_COPY.knowledgePreview}
    >
      <header className="space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-caption font-medium uppercase tracking-wide text-ink-muted">
            {KNOWLEDGE_TYPE_SINGULAR[detail.type]}
          </span>
          <ProcessingBadge status={detail.status} />
        </div>
        <h2 className="text-section text-ink">{detail.title}</h2>
        {detail.summary ? (
          <p className="text-small text-ink-muted">{detail.summary}</p>
        ) : null}
        {processing ? (
          <div className="rounded-lg bg-surface-alt/70 px-3 py-2">
            <p className="text-caption font-medium text-ink">
              {processing.stage}
            </p>
            {typeof processing.progressPercent === 'number' ? (
              <div
                className="mt-2 h-1.5 overflow-hidden rounded-full bg-white"
                role="progressbar"
                aria-valuenow={processing.progressPercent}
                aria-valuemin={0}
                aria-valuemax={100}
              >
                <div
                  className="h-full rounded-full bg-brand-500 transition-all duration-500"
                  style={{ width: `${processing.progressPercent}%` }}
                />
              </div>
            ) : null}
          </div>
        ) : null}
      </header>

      <section aria-label={UI_COPY.knowledgePreviewContent}>
        <h3 className="text-caption font-semibold uppercase tracking-wide text-ink-muted">
          {UI_COPY.knowledgePreviewContent}
        </h3>
        <p className="mt-2 rounded-lg bg-surface-alt/50 p-3 text-small leading-relaxed text-ink">
          {detail.summary ?? UI_COPY.knowledgePreviewFallback}
        </p>
      </section>

      <KnowledgeMetadata detail={detail} />
      <KnowledgeRelationships detail={detail} onOpen={onOpenRelated} />
      <KnowledgeTimeline events={detail.timeline} />

      <section aria-label={UI_COPY.knowledgeVersions}>
        <h3 className="text-caption font-semibold uppercase tracking-wide text-ink-muted">
          {UI_COPY.knowledgeVersions}
        </h3>
        <p className="mt-2 text-small text-ink-muted">
          {detail.versionsPlaceholder}
        </p>
      </section>
    </aside>
  );
}
