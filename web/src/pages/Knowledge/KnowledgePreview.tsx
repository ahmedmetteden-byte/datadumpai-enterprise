import { Button } from '@/components/ui/Button';
import { ProcessingBadge } from '@/pages/Knowledge/ProcessingBadge';
import {
  INDEX_PIPELINE_STEPS,
  IndexingProgress,
  pipelineStepActive,
} from '@/pages/Knowledge/IndexingProgress';
import { KnowledgeMetadata } from '@/pages/Knowledge/KnowledgeMetadata';
import { KnowledgeRelationships } from '@/pages/Knowledge/KnowledgeRelationships';
import { KnowledgeTimeline } from '@/pages/Knowledge/KnowledgeTimeline';
import { UI_COPY } from '@/constants/ui';
import { KNOWLEDGE_TYPE_SINGULAR } from '@/lib/knowledgeLabels';
import type {
  KnowledgeDetail,
  KnowledgePreview as KnowledgePreviewData,
  KnowledgeProcessingStatus,
} from '@/types/knowledge';

export function KnowledgePreview({
  detail,
  preview,
  processing,
  loading,
  onOpenRelated,
  onReindex,
  onDownload,
  onDelete,
}: {
  detail: KnowledgeDetail | null;
  preview: KnowledgePreviewData | null;
  processing: KnowledgeProcessingStatus | null;
  loading: boolean;
  onOpenRelated: (id: string) => void;
  onReindex: () => void;
  onDownload: () => void;
  onDelete: () => void;
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
        {detail.filename ? (
          <p className="text-small text-ink-muted">{detail.filename}</p>
        ) : null}
        {processing ? (
          <div className="rounded-lg bg-surface-alt/70 px-3 py-2">
            <IndexingProgress
              status={processing.status}
              progressPercent={processing.progressPercent}
              stage={processing.stage}
              indexStage={
                processing.indexStage ||
                (typeof detail.metadata?.indexStage === 'string'
                  ? detail.metadata.indexStage
                  : undefined)
              }
            />
            {processing.errorMessage ? (
              <p className="mt-2 text-small text-danger">
                {processing.errorMessage}
              </p>
            ) : null}
            <ol className="mt-3 space-y-1 text-caption">
              {INDEX_PIPELINE_STEPS.map((step) => {
                const stageKey =
                  processing.indexStage ||
                  (typeof detail.metadata?.indexStage === 'string'
                    ? detail.metadata.indexStage
                    : processing.status === 'indexed'
                      ? 'indexed'
                      : undefined);
                const state = pipelineStepActive(
                  step.key,
                  stageKey,
                  processing.status,
                );
                return (
                  <li
                    key={step.key}
                    className={
                      state === 'pending'
                        ? 'text-ink-faint'
                        : state === 'active'
                          ? 'font-medium text-ink'
                          : 'text-ink-muted'
                    }
                  >
                    {state === 'done' ? '●' : state === 'active' ? '◉' : '○'}{' '}
                    {UI_COPY[step.labelKey]}
                  </li>
                );
              })}
            </ol>
          </div>
        ) : null}
        <div className="flex flex-wrap gap-2 pt-1">
          <Button size="sm" variant="secondary" onClick={onReindex}>
            {UI_COPY.knowledgeActionReindex}
          </Button>
          <Button size="sm" variant="secondary" onClick={onDownload}>
            {UI_COPY.knowledgeActionDownload}
          </Button>
          <Button size="sm" variant="danger" onClick={onDelete}>
            {UI_COPY.knowledgeActionDelete}
          </Button>
        </div>
      </header>

      <section aria-label={UI_COPY.knowledgePreviewContent}>
        <h3 className="text-caption font-semibold uppercase tracking-wide text-ink-muted">
          {UI_COPY.knowledgePreviewContent}
        </h3>
        <pre className="mt-2 max-h-80 overflow-auto whitespace-pre-wrap rounded-lg bg-surface-alt/50 p-3 text-small leading-relaxed text-ink">
          {preview?.textExcerpt ||
            detail.summary ||
            UI_COPY.knowledgePreviewFallback}
        </pre>
      </section>

      <KnowledgeMetadata detail={detail} />
      <KnowledgeRelationships detail={detail} onOpen={onOpenRelated} />
      <KnowledgeTimeline events={detail.timeline} />
    </aside>
  );
}
