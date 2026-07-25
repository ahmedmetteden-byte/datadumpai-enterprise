import { useEffect, useRef, useState } from 'react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Modal } from '@/components/ui/Modal';
import { ProcessingBadge } from '@/pages/Knowledge/ProcessingBadge';
import { EmptyKnowledge } from '@/pages/Knowledge/EmptyKnowledge';
import { services } from '@/api/services';
import { UI_COPY } from '@/constants/ui';
import type {
  KnowledgeListItem,
  KnowledgeProcessingStatus,
} from '@/types/knowledge';

const PIPELINE: Array<{
  status: KnowledgeProcessingStatus['status'];
  stage: string;
  progress: number;
}> = [
  { status: 'uploaded', stage: 'Upload complete', progress: 10 },
  { status: 'extracting', stage: 'Extracting text and tables', progress: 35 },
  { status: 'processing', stage: 'Processing structure', progress: 55 },
  { status: 'indexed', stage: 'Building search index', progress: 78 },
  { status: 'linked', stage: 'Linking related knowledge', progress: 92 },
  { status: 'verified', stage: 'Verified and available to AI', progress: 100 },
];

export function KnowledgeUploadDialog({
  open,
  onClose,
  workspaceId,
  onUploaded,
}: {
  open: boolean;
  onClose: () => void;
  workspaceId: string | null;
  onUploaded: (item: KnowledgeListItem) => void;
}) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [fileName, setFileName] = useState('');
  const [title, setTitle] = useState('');
  const [busy, setBusy] = useState(false);
  const [created, setCreated] = useState<KnowledgeListItem | null>(null);
  const [status, setStatus] = useState<KnowledgeProcessingStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [stepIndex, setStepIndex] = useState(0);

  useEffect(() => {
    if (!open) {
      setFileName('');
      setTitle('');
      setBusy(false);
      setCreated(null);
      setStatus(null);
      setError(null);
      setStepIndex(0);
    }
  }, [open]);

  useEffect(() => {
    if (!created || !workspaceId) return;
    let cancelled = false;
    const timer = window.setInterval(() => {
      void services.knowledge
        .processingStatus(workspaceId, created.id)
        .then((next) => {
          if (!cancelled) setStatus(next);
        });
    }, 500);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [created, workspaceId]);

  // Animated UI pipeline for feedback even before poll catches up
  useEffect(() => {
    if (!created) return;
    if (stepIndex >= PIPELINE.length - 1) return;
    const timer = window.setTimeout(() => {
      setStepIndex((index) => Math.min(index + 1, PIPELINE.length - 1));
    }, 650);
    return () => window.clearTimeout(timer);
  }, [created, stepIndex]);

  async function handleUpload() {
    if (!workspaceId || !fileName.trim()) {
      setError(UI_COPY.knowledgeUploadNeedFile);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const item = await services.knowledge.upload(workspaceId, {
        fileName: fileName.trim(),
        mimeType: 'application/pdf',
        sizeBytes: 1_200_000,
        title: title.trim() || undefined,
      });
      setCreated(item);
      setStatus({
        knowledgeId: item.id,
        status: 'uploaded',
        stage: 'Upload complete',
        progressPercent: 8,
        updatedAt: item.updatedAt,
      });
      onUploaded(item);
    } catch (err) {
      setError(err instanceof Error ? err.message : UI_COPY.knowledgeUploadError);
    } finally {
      setBusy(false);
    }
  }

  const animated = PIPELINE[stepIndex]!;
  const displayStatus = status ?? {
    knowledgeId: created?.id ?? '',
    status: animated.status,
    stage: animated.stage,
    progressPercent: animated.progress,
    updatedAt: new Date().toISOString(),
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={UI_COPY.knowledgeUploadTitle}
      footer={
        created ? (
          <Button onClick={onClose}>{UI_COPY.knowledgeUploadDone}</Button>
        ) : (
          <>
            <Button variant="ghost" onClick={onClose} disabled={busy}>
              {UI_COPY.cancel}
            </Button>
            <Button onClick={() => void handleUpload()} disabled={busy || !workspaceId}>
              {busy ? UI_COPY.knowledgeUploading : UI_COPY.knowledgeUploadStart}
            </Button>
          </>
        )
      }
    >
      {!created ? (
        <div className="space-y-4">
          <p className="text-small text-ink-muted">
            {UI_COPY.knowledgeUploadBody}
          </p>
          <div>
            <label className="mb-1 block text-caption font-medium text-ink-muted">
              {UI_COPY.knowledgeUploadFile}
            </label>
            <input
              ref={fileRef}
              type="file"
              className="sr-only"
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) {
                  setFileName(file.name);
                  if (!title) setTitle(file.name.replace(/\.[^.]+$/, ''));
                }
              }}
            />
            <Button
              variant="secondary"
              className="w-full"
              onClick={() => fileRef.current?.click()}
            >
              {fileName || UI_COPY.knowledgeChooseFile}
            </Button>
          </div>
          <div>
            <label
              htmlFor="knowledge-upload-title"
              className="mb-1 block text-caption font-medium text-ink-muted"
            >
              {UI_COPY.knowledgeUploadTitleField}
            </label>
            <Input
              id="knowledge-upload-title"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder={UI_COPY.knowledgeUploadTitlePlaceholder}
            />
          </div>
          {!fileName ? <EmptyKnowledge variant="uploads" /> : null}
          {error ? (
            <p className="text-small text-danger" role="alert">
              {error}
            </p>
          ) : null}
        </div>
      ) : (
        <div className="space-y-4" aria-live="polite">
          <p className="text-small text-ink">
            <span className="font-medium">{created.title}</span>
          </p>
          <div className="flex items-center gap-2">
            <ProcessingBadge status={displayStatus.status} pulse />
            <span className="text-small text-ink-muted">{displayStatus.stage}</span>
          </div>
          <div
            className="h-2 overflow-hidden rounded-full bg-surface-alt"
            role="progressbar"
            aria-valuenow={displayStatus.progressPercent ?? animated.progress}
            aria-valuemin={0}
            aria-valuemax={100}
          >
            <div
              className="h-full rounded-full bg-brand-500 transition-all duration-500"
              style={{
                width: `${displayStatus.progressPercent ?? animated.progress}%`,
              }}
            />
          </div>
          <ol className="space-y-1.5">
            {PIPELINE.map((step, index) => (
              <li
                key={step.status}
                className={`text-small ${
                  index <= stepIndex ? 'text-ink' : 'text-ink-muted'
                }`}
              >
                {index <= stepIndex ? '●' : '○'} {step.stage}
              </li>
            ))}
          </ol>
        </div>
      )}
    </Modal>
  );
}
