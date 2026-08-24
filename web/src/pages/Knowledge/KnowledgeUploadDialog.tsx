import { useEffect, useRef, useState } from 'react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Modal } from '@/components/ui/Modal';
import { ProgressRing } from '@/components/ui/ProgressRing';
import { StatusTimeline } from '@/components/ui/StatusTimeline';
import {
  INDEX_PIPELINE_STEPS,
  IndexingProgress,
  pipelineStepActive,
} from '@/pages/Knowledge/IndexingProgress';
import { EmptyKnowledge } from '@/pages/Knowledge/EmptyKnowledge';
import { services } from '@/api/services';
import { useAuth } from '@/context/AuthContext';
import { UI_COPY } from '@/constants/ui';
import type {
  KnowledgeListItem,
  KnowledgeProcessingStatus,
} from '@/types/knowledge';

const ALLOWED_EXTENSIONS = new Set([
  '.pdf',
  '.docx',
  '.xlsx',
  '.pptx',
  '.txt',
]);

const ACCEPT =
  '.pdf,.docx,.xlsx,.pptx,.txt,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.openxmlformats-officedocument.presentationml.presentation,text/plain';

function extensionOf(name: string): string {
  const match = /\.[^.]+$/.exec(name.toLowerCase());
  return match?.[0] ?? '';
}

function isTerminal(status: KnowledgeProcessingStatus['status']): boolean {
  return (
    status === 'indexed' ||
    status === 'verified' ||
    status === 'failed' ||
    status === 'archived'
  );
}

type Phase = 'pick' | 'transferring' | 'indexing' | 'done' | 'failed';

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
  const { accessToken } = useAuth();
  const fileRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [periodDate, setPeriodDate] = useState('');
  const [phase, setPhase] = useState<Phase>('pick');
  const [transferPercent, setTransferPercent] = useState(0);
  const [created, setCreated] = useState<KnowledgeListItem | null>(null);
  const [status, setStatus] = useState<KnowledgeProcessingStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) {
      setFile(null);
      setTitle('');
      setPeriodDate('');
      setPhase('pick');
      setTransferPercent(0);
      setCreated(null);
      setStatus(null);
      setError(null);
    }
  }, [open]);

  useEffect(() => {
    if (!created || !workspaceId) return;
    if (phase === 'done' || phase === 'failed') return;

    let cancelled = false;
    const timer = window.setInterval(() => {
      void services.knowledge
        .processingStatus(workspaceId, created.id, { accessToken })
        .then((next) => {
          if (cancelled) return;
          setStatus(next);
          if (next.status === 'failed') {
            setPhase('failed');
            return;
          }
          if (isTerminal(next.status)) {
            setPhase('done');
            return;
          }
          setPhase('indexing');
        })
        .catch(() => {
          /* keep polling */
        });
    }, 600);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [created, workspaceId, accessToken, phase]);

  function chooseFile(next: File | null) {
    setError(null);
    if (!next) {
      setFile(null);
      return;
    }
    const ext = extensionOf(next.name);
    if (!ALLOWED_EXTENSIONS.has(ext)) {
      setFile(null);
      setError(UI_COPY.knowledgeUploadTypeError);
      return;
    }
    setFile(next);
    if (!title) {
      setTitle(next.name.replace(/\.[^.]+$/, ''));
    }
  }

  async function handleUpload() {
    if (!workspaceId || !file) {
      setError(UI_COPY.knowledgeUploadNeedFile);
      return;
    }

    setPhase('transferring');
    setTransferPercent(0);
    setError(null);

    try {
      const item = await services.knowledge.upload(
        workspaceId,
        {
          file,
          title: title.trim() || undefined,
          periodDate: periodDate.trim() || undefined,
          onProgress: (percent) => setTransferPercent(percent),
        },
        { accessToken },
      );
      setCreated(item);
      setTransferPercent(100);
      setPhase('indexing');
      setStatus({
        knowledgeId: item.id,
        status: 'uploaded',
        stage: UI_COPY.knowledgeIndexIndexing,
        progressPercent: item.progressPercent ?? 8,
        updatedAt: item.updatedAt,
      });
      onUploaded(item);
    } catch (err) {
      setPhase('pick');
      setError(
        err instanceof Error ? err.message : UI_COPY.knowledgeUploadError,
      );
    }
  }

  const indexStage =
    status?.indexStage ||
    (status?.status === 'indexed'
      ? 'indexed'
      : status?.status === 'extracting'
        ? 'extracting'
        : 'queued');

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
            <Button
              variant="ghost"
              onClick={onClose}
              disabled={phase === 'transferring'}
            >
              {UI_COPY.cancel}
            </Button>
            <Button
              onClick={() => void handleUpload()}
              disabled={phase === 'transferring' || !workspaceId || !file}
            >
              {phase === 'transferring'
                ? UI_COPY.knowledgeUploading
                : UI_COPY.knowledgeUploadStart}
            </Button>
          </>
        )
      }
    >
      {phase === 'pick' ? (
        <div className="space-y-4">
          <p className="text-small text-ink-muted">
            {UI_COPY.knowledgeUploadBody}
          </p>
          <p className="text-caption text-ink-faint">
            {UI_COPY.knowledgeUploadFormats}
          </p>
          <div>
            <label className="mb-1 block text-caption font-medium text-ink-muted">
              {UI_COPY.knowledgeUploadFile}
            </label>
            <input
              ref={fileRef}
              type="file"
              accept={ACCEPT}
              className="sr-only"
              onChange={(event) => {
                chooseFile(event.target.files?.[0] ?? null);
              }}
            />
            <Button
              variant="secondary"
              className="w-full"
              onClick={() => fileRef.current?.click()}
            >
              {file?.name || UI_COPY.knowledgeChooseFile}
            </Button>
            {file ? (
              <p className="mt-2 text-caption text-ink-muted">
                {(file.size / 1024).toFixed(1)} KB ·{' '}
                {extensionOf(file.name).replace('.', '').toUpperCase()}
              </p>
            ) : null}
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
          <div>
            <label
              htmlFor="knowledge-upload-period"
              className="mb-1 block text-caption font-medium text-ink-muted"
            >
              {UI_COPY.knowledgeUploadPeriodField}
            </label>
            <Input
              id="knowledge-upload-period"
              type="date"
              value={periodDate}
              onChange={(event) => setPeriodDate(event.target.value)}
            />
            <p className="mt-1 text-caption text-ink-faint">
              {UI_COPY.knowledgeUploadPeriodHint}
            </p>
          </div>
          {!file ? <EmptyKnowledge variant="uploads" /> : null}
          {error ? (
            <p className="text-small text-danger" role="alert">
              {error}
            </p>
          ) : null}
        </div>
      ) : (
        <div className="space-y-4" aria-live="polite">
          {phase === 'done' ? (
            <div
              className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-small text-success"
              role="status"
            >
              {UI_COPY.knowledgeUploadSuccessDetail.replace(
                '{name}',
                created?.filename || created?.title || 'Document',
              )}
            </div>
          ) : null}

          <p className="text-small text-ink">
            <span className="font-medium">
              {created?.title || file?.name}
            </span>
          </p>

          {phase === 'transferring' ? (
            <div className="flex flex-col items-center gap-2 py-2">
              <ProgressRing
                value={transferPercent}
                size={64}
                strokeWidth={5}
                label={`${transferPercent}% uploaded`}
              />
              <span className="text-small font-medium text-ink">
                {UI_COPY.knowledgeIndexStepUpload}
              </span>
            </div>
          ) : status ? (
            <IndexingProgress
              status={
                phase === 'done'
                  ? 'indexed'
                  : phase === 'failed'
                    ? 'failed'
                    : status.status
              }
              progressPercent={
                phase === 'done' ? 100 : status.progressPercent
              }
              stage={status.stage}
              indexStage={indexStage}
            />
          ) : null}

          <StatusTimeline
            steps={INDEX_PIPELINE_STEPS.map((step) => {
              const state =
                phase === 'transferring'
                  ? step.key === 'upload'
                    ? 'active'
                    : 'pending'
                  : pipelineStepActive(
                      step.key,
                      phase === 'done' ? 'indexed' : indexStage,
                      phase === 'done'
                        ? 'indexed'
                        : phase === 'failed'
                          ? 'failed'
                          : status?.status,
                    );
              return {
                id: step.key,
                label: UI_COPY[step.labelKey],
                state,
              };
            })}
          />

          {phase === 'failed' && status?.errorMessage ? (
            <p className="text-small text-danger" role="alert">
              {status.errorMessage}
            </p>
          ) : null}
        </div>
      )}
    </Modal>
  );
}
