import { cn } from '@/lib/cn';
import { UI_COPY } from '@/constants/ui';
import type { KnowledgeProcessingStatusValue } from '@/types/knowledge';

const IN_FLIGHT: KnowledgeProcessingStatusValue[] = [
  'uploaded',
  'extracting',
  'processing',
];

const STAGE_LABELS: Record<string, string> = {
  queued: UI_COPY.knowledgeIndexStageQueued,
  extracting: UI_COPY.knowledgeIndexStageExtract,
  chunking: UI_COPY.knowledgeIndexStageChunk,
  embedding: UI_COPY.knowledgeIndexStageEmbed,
  upserting: UI_COPY.knowledgeIndexStageQdrant,
  indexed: UI_COPY.knowledgeIndexDone,
  failed: UI_COPY.knowledgeUploadIndexFailed,
};

export function isIndexingInFlight(
  status: KnowledgeProcessingStatusValue,
): boolean {
  return IN_FLIGHT.includes(status);
}

export function indexingHeadline({
  status,
}: {
  status: KnowledgeProcessingStatusValue;
  progressPercent?: number | null;
  stage?: string | null;
  indexStage?: string | null;
}): string {
  if (status === 'failed') {
    return UI_COPY.knowledgeUploadIndexFailed;
  }
  if (
    status === 'indexed' ||
    status === 'verified' ||
    status === 'linked' ||
    status === 'archived'
  ) {
    return status === 'archived'
      ? 'Archived'
      : UI_COPY.knowledgeIndexDone;
  }
  return UI_COPY.knowledgeIndexIndexing;
}

export function IndexingProgress({
  status,
  progressPercent,
  stage,
  indexStage,
  showBar = true,
  compact = false,
  className,
}: {
  status: KnowledgeProcessingStatusValue;
  progressPercent?: number | null;
  stage?: string | null;
  indexStage?: string | null;
  showBar?: boolean;
  compact?: boolean;
  className?: string;
}) {
  const inFlight = isIndexingInFlight(status);
  const percent =
    typeof progressPercent === 'number'
      ? Math.min(100, Math.max(0, Math.round(progressPercent)))
      : status === 'indexed' || status === 'verified'
        ? 100
        : 0;
  const label = indexingHeadline({ status, progressPercent: percent || undefined });
  const stageLabel =
    (indexStage && STAGE_LABELS[indexStage]) ||
    (stage?.trim() ? stage : null);

  return (
    <div className={cn('min-w-[7.5rem]', className)}>
      <div className="flex items-baseline justify-between gap-2">
        <span
          className={cn(
            'font-medium',
            compact ? 'text-caption' : 'text-small',
            status === 'failed'
              ? 'text-danger'
              : inFlight
                ? 'animate-pulse text-ink'
                : 'text-success',
          )}
        >
          {label}
        </span>
        {inFlight && percent > 0 ? (
          <span className="text-caption tabular-nums font-semibold text-ink">
            {percent}%
          </span>
        ) : null}
      </div>
      {inFlight && stageLabel ? (
        <p className="mt-0.5 text-caption text-ink-muted">{stageLabel}</p>
      ) : null}
      {showBar && inFlight ? (
        <div
          className={cn(
            'mt-1.5 overflow-hidden rounded-full bg-surface-alt',
            compact ? 'h-1' : 'h-1.5',
          )}
          role="progressbar"
          aria-valuenow={percent}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={label}
        >
          <div
            className={cn(
              'h-full rounded-full bg-brand-500 transition-all duration-500',
              status === 'failed' && 'bg-danger',
            )}
            style={{ width: `${percent || 8}%` }}
          />
        </div>
      ) : null}
    </div>
  );
}

export const INDEX_PIPELINE_STEPS = [
  { key: 'upload', labelKey: 'knowledgeIndexStepUpload' as const },
  { key: 'extracting', labelKey: 'knowledgeIndexStageExtract' as const },
  { key: 'chunking', labelKey: 'knowledgeIndexStageChunk' as const },
  { key: 'embedding', labelKey: 'knowledgeIndexStageEmbed' as const },
  { key: 'upserting', labelKey: 'knowledgeIndexStageQdrant' as const },
  { key: 'indexed', labelKey: 'knowledgeIndexDone' as const },
] as const;

const STAGE_ORDER = [
  'queued',
  'extracting',
  'chunking',
  'embedding',
  'upserting',
  'indexed',
] as const;

export function pipelineStepActive(
  stepKey: string,
  indexStage?: string | null,
  status?: KnowledgeProcessingStatusValue,
): 'done' | 'active' | 'pending' {
  if (status === 'indexed' || status === 'verified' || status === 'linked') {
    return 'done';
  }
  if (status === 'failed') {
    return stepKey === 'indexed' ? 'pending' : 'done';
  }
  if (stepKey === 'upload') {
    return 'done';
  }
  const current = indexStage || 'queued';
  const currentIdx = STAGE_ORDER.indexOf(
    current as (typeof STAGE_ORDER)[number],
  );
  const stepIdx = STAGE_ORDER.indexOf(stepKey as (typeof STAGE_ORDER)[number]);
  if (stepIdx < 0) return 'pending';
  if (currentIdx < 0) return stepKey === 'queued' ? 'active' : 'pending';
  if (stepIdx < currentIdx) return 'done';
  if (stepIdx === currentIdx) return 'active';
  return 'pending';
}
