import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type DragEvent,
} from 'react';
import { InlineRequestStatus } from '@/components/feedback';
import { Button } from '@/components/ui/Button';
import { Collapsible } from '@/components/ui/Collapsible';
import { Drawer } from '@/components/drawers/Drawer';
import { Select } from '@/components/ui/Select';
import { services } from '@/api/services';
import { useAuth } from '@/context/AuthContext';
import { useWorkspace } from '@/context/WorkspaceContext';
import { useDisclosure } from '@/hooks/useDisclosure';
import { useEnsureWorkspace, GENERAL_WORKSPACE_NAME } from '@/hooks/useEnsureWorkspace';
import { useIntelligenceStudio } from '@/hooks/useIntelligenceStudio';
import { useWorkspaceList } from '@/hooks/useWorkspaceList';
import { UI_COPY } from '@/constants/ui';
import { cn } from '@/lib/cn';
import { EyebrowBadge } from '@/components/ui/EyebrowBadge';
import { ProgressRing } from '@/components/ui/ProgressRing';
import { ConversationList } from '@/pages/IntelligenceStudio/ConversationList';
import { ConversationMessage } from '@/pages/IntelligenceStudio/ConversationMessage';
import { NameWorkspacePrompt } from '@/pages/Home/NameWorkspacePrompt';
import {
  WorkspaceDestinationDialog,
  type WorkspaceDestination,
} from '@/pages/Home/WorkspaceDestinationDialog';
import { ReportDetailPanel } from '@/pages/Reports/ReportDetailPanel';
import type { IntelligenceMessage } from '@/types/intelligence';
import type { ReportPeriod, ReportTemplate } from '@/types/reports';

const ALLOWED_EXTENSIONS = new Set([
  '.pdf',
  '.docx',
  '.xlsx',
  '.pptx',
  '.txt',
]);

const ACCEPT =
  '.pdf,.docx,.xlsx,.pptx,.txt,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.openxmlformats-officedocument.presentationml.presentation,text/plain';

const DEFAULT_TEMPLATE_ID = 'executive_summary';
const DEFAULT_PERIOD_ID = 'custom';

type Mode = 'report' | 'ask';
type AttachmentStatus = 'uploading' | 'uploaded' | 'error';

interface Attachment {
  id: string;
  name: string;
  sizeLabel: string;
  status: AttachmentStatus;
  progress: number;
  error?: string;
}

function extensionOf(name: string): string {
  const match = /\.[^.]+$/.exec(name.toLowerCase());
  return match?.[0] ?? '';
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function HomeComposer() {
  const { accessToken } = useAuth();
  const auth = useMemo(() => ({ accessToken }), [accessToken]);
  const { ready, workspaceId, error: workspaceError } = useEnsureWorkspace();
  const { setActiveWorkspaceId, bumpRevision } = useWorkspace();
  const { workspaces, reload: reloadWorkspaces } = useWorkspaceList();
  const studio = useIntelligenceStudio();

  const [mode, setMode] = useState<Mode>('report');
  const [text, setText] = useState('');
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [dragActive, setDragActive] = useState(false);
  const [templates, setTemplates] = useState<ReportTemplate[]>([]);
  const [periods, setPeriods] = useState<ReportPeriod[]>([]);
  const [templateId, setTemplateId] = useState(DEFAULT_TEMPLATE_ID);
  const [periodId, setPeriodId] = useState(DEFAULT_PERIOD_ID);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [generatedReportId, setGeneratedReportId] = useState<string | null>(
    null,
  );
  const fileInputRef = useRef<HTMLInputElement>(null);
  const uploadQueueRef = useRef<Promise<void>>(Promise.resolve());

  const [temporaryChat, setTemporaryChat] = useState(false);
  const [tempMessages, setTempMessages] = useState<IntelligenceMessage[]>([]);
  const historyDrawer = useDisclosure(false);

  const destinationDialog = useDisclosure(false);
  const [pendingFiles, setPendingFiles] = useState<File[] | null>(null);
  const [resolvingDestination, setResolvingDestination] = useState(false);
  const [destinationError, setDestinationError] = useState<string | null>(
    null,
  );

  useEffect(() => {
    if (!workspaceId) return;
    let cancelled = false;
    void Promise.all([
      services.report.listTemplates(workspaceId, auth),
      services.report.listPeriods(workspaceId, auth),
    ]).then(([nextTemplates, nextPeriods]) => {
      if (cancelled) return;
      setTemplates(nextTemplates);
      setPeriods(nextPeriods);
      if (nextTemplates.some((item) => item.id === DEFAULT_TEMPLATE_ID)) {
        setTemplateId(DEFAULT_TEMPLATE_ID);
      } else if (nextTemplates[0]) {
        setTemplateId(nextTemplates[0].id);
      }
      if (nextPeriods.some((item) => item.id === DEFAULT_PERIOD_ID)) {
        setPeriodId(DEFAULT_PERIOD_ID);
      } else if (nextPeriods[0]) {
        setPeriodId(nextPeriods[0].id);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [workspaceId, auth]);

  function updateAttachment(id: string, patch: Partial<Attachment>) {
    setAttachments((current) =>
      current.map((item) => (item.id === id ? { ...item, ...patch } : item)),
    );
  }

  function selectFiles(fileList: FileList | File[]) {
    const files = Array.from(fileList);
    if (files.length === 0) return;
    setPendingFiles(files);
    setDestinationError(null);
    destinationDialog.open();
  }

  async function resolveDestinationWorkspaceId(
    destination: WorkspaceDestination,
  ): Promise<string> {
    if (destination.type === 'existing') {
      return destination.workspaceId;
    }
    if (destination.type === 'new') {
      const created = await services.workspace.createWorkspace(
        { name: destination.name },
        auth,
      );
      return created.id;
    }
    const existingGeneral = workspaces.find(
      (item) => item.name === GENERAL_WORKSPACE_NAME,
    );
    if (existingGeneral) return existingGeneral.id;
    const created = await services.workspace.createWorkspace(
      { name: GENERAL_WORKSPACE_NAME },
      auth,
    );
    return created.id;
  }

  async function handleDestinationConfirm(destination: WorkspaceDestination) {
    const files = pendingFiles;
    if (!files) return;
    setResolvingDestination(true);
    setDestinationError(null);
    try {
      const targetWorkspaceId = await resolveDestinationWorkspaceId(destination);
      if (targetWorkspaceId !== workspaceId) {
        setActiveWorkspaceId(targetWorkspaceId);
        bumpRevision();
        reloadWorkspaces();
      }
      attachFiles(files, targetWorkspaceId);
      setPendingFiles(null);
      destinationDialog.close();
    } catch (err) {
      setDestinationError(
        err instanceof Error ? err.message : UI_COPY.destinationError,
      );
    } finally {
      setResolvingDestination(false);
    }
  }

  function attachFiles(fileList: FileList | File[], targetWorkspaceId: string) {
    const files = Array.from(fileList);
    for (const file of files) {
      const ext = extensionOf(file.name);
      const id = `${file.name}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
      if (!ALLOWED_EXTENSIONS.has(ext)) {
        setAttachments((current) => [
          ...current,
          {
            id,
            name: file.name,
            sizeLabel: formatSize(file.size),
            status: 'error',
            progress: 0,
            error: UI_COPY.homeComposerFileTypeError,
          },
        ]);
        continue;
      }

      setAttachments((current) => [
        ...current,
        {
          id,
          name: file.name,
          sizeLabel: formatSize(file.size),
          status: 'uploading',
          progress: 0,
        },
      ]);

      // Uploads are chained one-at-a-time (not fired in parallel): the backend
      // saves a workspace's whole document list on every upload, so concurrent
      // uploads race and can silently delete each other's newly-added documents.
      uploadQueueRef.current = uploadQueueRef.current.then(() =>
        services.knowledge
          .upload(
            targetWorkspaceId,
            {
              file,
              onProgress: (percent) => updateAttachment(id, { progress: percent }),
            },
            auth,
          )
          .then(() => updateAttachment(id, { status: 'uploaded', progress: 100 }))
          .catch((err) =>
            updateAttachment(id, {
              status: 'error',
              error:
                err instanceof Error
                  ? err.message
                  : UI_COPY.homeComposerUploadError,
            }),
          ),
      );
    }
  }

  function removeAttachment(id: string) {
    setAttachments((current) => current.filter((item) => item.id !== id));
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragActive(false);
    if (event.dataTransfer.files.length) {
      selectFiles(event.dataTransfer.files);
    }
  }

  const uploading = attachments.some((item) => item.status === 'uploading');
  const hasUploadedAttachment = attachments.some(
    (item) => item.status === 'uploaded',
  );
  const hasContent =
    mode === 'ask'
      ? text.trim().length > 0
      : text.trim().length > 0 || hasUploadedAttachment;
  const canSubmit =
    ready && Boolean(workspaceId) && hasContent && !uploading && !submitting;

  async function askQuestion(question: string) {
    if (!workspaceId) return;

    if (!temporaryChat) {
      void studio.sendMessage(question);
      return;
    }

    const userMessage: IntelligenceMessage = {
      id: `tmp_user_${Date.now()}`,
      conversationId: 'temporary',
      role: 'user',
      content: question,
      status: 'complete',
      createdAt: new Date().toISOString(),
      mode: 'ask',
    };
    const pendingId = `tmp_assistant_${Date.now()}`;
    const pendingMessage: IntelligenceMessage = {
      id: pendingId,
      conversationId: 'temporary',
      role: 'assistant',
      content: '',
      status: 'streaming',
      createdAt: new Date().toISOString(),
      mode: 'ask',
    };
    setTempMessages((current) => [...current, userMessage, pendingMessage]);

    try {
      const assistant = await services.intelligence.askTemporary(
        workspaceId,
        { content: question, mode: 'ask' },
        auth,
      );
      setTempMessages((current) =>
        current.map((item) => (item.id === pendingId ? assistant : item)),
      );
    } catch (err) {
      setTempMessages((current) =>
        current.map((item) =>
          item.id === pendingId
            ? {
                ...pendingMessage,
                status: 'error',
                answer:
                  err instanceof Error
                    ? err.message
                    : 'Something went wrong while analysing this workspace.',
              }
            : item,
        ),
      );
    }
  }

  function startNewChat() {
    studio.setActiveConversationId(null);
    setTempMessages([]);
  }

  async function handleSubmit() {
    if (!canSubmit || !workspaceId) return;

    if (mode === 'ask') {
      const question = text.trim();
      setText('');
      void askQuestion(question);
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      const created = await services.report.generate(
        workspaceId,
        {
          templateId,
          periodId,
          instructions: text.trim(),
        },
        auth,
      );
      const saved = await services.report.save(workspaceId, created.id, 'ready', auth);
      setGeneratedReportId(saved.id);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : UI_COPY.homeComposerGenerateError,
      );
    } finally {
      setSubmitting(false);
    }
  }

  function startNewReport() {
    setGeneratedReportId(null);
    setText('');
    setAttachments([]);
  }

  return (
    <section className="animate-slide-up mx-auto w-full max-w-2xl space-y-6 pt-6 text-center sm:pt-10">
      <div>
        <img
          src="/datadumpai-wordmark.png"
          alt="DataDumpAI"
          className="mx-auto h-10 w-auto sm:h-12"
        />
        <div className="mt-4">
          <EyebrowBadge>{UI_COPY.homeComposerEyebrow}</EyebrowBadge>
        </div>
        <h1 className="mt-3 text-hero text-ink">{UI_COPY.homeComposerTitle}</h1>
        <p className="mx-auto mt-2 max-w-lg text-body text-ink-muted">
          {UI_COPY.homeComposerSubtitle}
        </p>
      </div>

      <div className="flex justify-center gap-2">
        <button
          type="button"
          onClick={() => setMode('report')}
          className={cn(
            'rounded-full px-4 py-1.5 text-small font-medium transition-colors',
            mode === 'report'
              ? 'bg-brand-500 text-white'
              : 'bg-surface-alt text-ink-muted hover:text-ink',
          )}
        >
          {UI_COPY.homeComposerReportTab}
        </button>
        <button
          type="button"
          onClick={() => setMode('ask')}
          className={cn(
            'rounded-full px-4 py-1.5 text-small font-medium transition-colors',
            mode === 'ask'
              ? 'bg-brand-500 text-white'
              : 'bg-surface-alt text-ink-muted hover:text-ink',
          )}
        >
          {UI_COPY.homeComposerAskTab}
        </button>
      </div>

      {mode === 'ask' ? (
        <div className="flex flex-wrap items-center justify-center gap-x-4 gap-y-2 text-caption">
          <button
            type="button"
            onClick={historyDrawer.open}
            className="font-medium text-ink-muted hover:text-ink"
          >
            {UI_COPY.homeComposerHistory}
          </button>
          <button
            type="button"
            onClick={startNewChat}
            className="font-medium text-ink-muted hover:text-ink"
          >
            {UI_COPY.homeComposerNewChat}
          </button>
          <label className="inline-flex items-center gap-1.5 font-medium text-ink-muted">
            <input
              type="checkbox"
              checked={temporaryChat}
              onChange={(event) => setTemporaryChat(event.target.checked)}
              className="h-3.5 w-3.5 rounded border-surface-border text-brand-500 focus:ring-brand-500"
            />
            {UI_COPY.homeComposerTemporaryChat}
          </label>
        </div>
      ) : null}

      {mode === 'ask' && temporaryChat ? (
        <p className="text-caption text-ink-faint">
          {UI_COPY.homeComposerTemporaryChatNotice}
        </p>
      ) : null}

      <div className="rounded-xl border border-surface-border bg-white p-4 text-left shadow-card sm:p-5">
        <label
          htmlFor="home-composer-text"
          className="mb-1.5 block text-small font-semibold text-ink"
        >
          {mode === 'report'
            ? UI_COPY.homeComposerReportInputLabel
            : UI_COPY.homeComposerAskInputLabel}
        </label>
        <textarea
          id="home-composer-text"
          rows={3}
          value={text}
          onChange={(event) => setText(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault();
              void handleSubmit();
            }
          }}
          placeholder={
            mode === 'report'
              ? UI_COPY.homeComposerReportPlaceholder
              : UI_COPY.homeComposerAskPlaceholder
          }
          className="min-h-[4.5rem] w-full resize-none rounded-lg border border-surface-border bg-surface-alt/50 px-3 py-2.5 text-body text-ink placeholder:text-ink-faint focus-visible:border-brand-500 focus-visible:bg-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
        />

        {mode === 'report' ? (
          <div
            onDragOver={(event) => {
              event.preventDefault();
              setDragActive(true);
            }}
            onDragLeave={() => setDragActive(false)}
            onDrop={handleDrop}
            className={cn(
              'mt-3 rounded-lg border-2 border-dashed px-4 py-4 text-center transition-colors',
              dragActive
                ? 'border-brand-500 bg-brand-50/60'
                : 'border-surface-border bg-surface-alt/40',
            )}
          >
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept={ACCEPT}
              className="sr-only"
              onChange={(event) => {
                if (event.target.files?.length) {
                  selectFiles(event.target.files);
                }
                event.target.value = '';
              }}
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="text-small font-medium text-brand-600 hover:text-brand-700"
            >
              {UI_COPY.homeComposerAttach}
            </button>
            <p className="mt-1 text-caption text-ink-faint">
              {UI_COPY.homeComposerDropHint}
            </p>
          </div>
        ) : null}

        {attachments.length > 0 ? (
          <ul className="mt-3 space-y-1.5">
            {attachments.map((item) => (
              <li
                key={item.id}
                className="flex items-center justify-between gap-2 rounded-md bg-surface-alt px-3 py-1.5 text-caption"
              >
                <span className="min-w-0 truncate text-ink">
                  {item.name}{' '}
                  <span className="text-ink-faint">· {item.sizeLabel}</span>
                </span>
                <span className="flex shrink-0 items-center gap-2">
                  {item.status === 'uploading' ? (
                    <span className="flex items-center gap-1.5">
                      <ProgressRing
                        value={item.progress}
                        size={20}
                        strokeWidth={2.5}
                        showLabel={false}
                        label={`${item.progress}% uploaded`}
                      />
                      <span className="tabular-nums text-ink-muted">
                        {item.progress}%
                      </span>
                    </span>
                  ) : item.status === 'error' ? (
                    <span className="text-danger">{item.error}</span>
                  ) : (
                    <span className="text-success">✓</span>
                  )}
                  <button
                    type="button"
                    onClick={() => removeAttachment(item.id)}
                    className="text-ink-faint hover:text-ink"
                    aria-label={`${UI_COPY.homeComposerRemoveFile} ${item.name}`}
                  >
                    ×
                  </button>
                </span>
              </li>
            ))}
          </ul>
        ) : null}

        <div className="mt-4 flex items-center justify-end gap-3">
          {!hasContent && ready ? (
            <p className="text-caption text-ink-faint">
              {mode === 'ask'
                ? UI_COPY.homeComposerNeedText
                : UI_COPY.homeComposerNeedTextOrFile}
            </p>
          ) : null}
          <Button onClick={() => void handleSubmit()} disabled={!canSubmit}>
            {mode === 'ask'
              ? UI_COPY.homeComposerAsk
              : submitting
                ? UI_COPY.homeComposerGenerating
                : UI_COPY.homeComposerGenerate}
          </Button>
        </div>
      </div>

      {mode === 'report' ? (
        <Collapsible title={UI_COPY.homeComposerAdvanced} defaultOpen={false}>
          <div className="grid gap-3 text-left sm:grid-cols-2">
            <label className="block">
              <span className="mb-1 block text-caption font-medium text-ink-muted">
                {UI_COPY.homeComposerTemplateLabel}
              </span>
              <Select
                value={templateId}
                onChange={(event) => setTemplateId(event.target.value)}
                className="w-full"
              >
                {templates.map((template) => (
                  <option
                    key={template.id}
                    value={template.id}
                    disabled={template.locked}
                  >
                    {template.name}
                    {template.locked ? ` ${UI_COPY.homeComposerTemplateLocked}` : ''}
                  </option>
                ))}
              </Select>
            </label>
            <label className="block">
              <span className="mb-1 block text-caption font-medium text-ink-muted">
                {UI_COPY.homeComposerPeriodLabel}
              </span>
              <Select
                value={periodId}
                onChange={(event) => setPeriodId(event.target.value)}
                className="w-full"
              >
                {periods.map((period) => (
                  <option key={period.id} value={period.id}>
                    {period.name}
                  </option>
                ))}
              </Select>
            </label>
          </div>
        </Collapsible>
      ) : null}

      {error ? (
        <InlineRequestStatus kind="error" message={error} />
      ) : null}
      {workspaceError ? (
        <InlineRequestStatus
          kind="error"
          message={UI_COPY.homeComposerWorkspaceError}
        />
      ) : null}

      {mode === 'report' && generatedReportId && workspaceId ? (
        <div className="space-y-4 text-left">
          <NameWorkspacePrompt workspaceId={workspaceId} />
          <div className="rounded-xl border border-surface-border bg-white p-4 shadow-card sm:p-5">
            <div className="mb-3 flex items-center justify-between gap-3">
              <h2 className="text-section text-ink">
                {UI_COPY.homeComposerReportReadyTitle}
              </h2>
              <Button variant="ghost" size="sm" onClick={startNewReport}>
                {UI_COPY.homeComposerGenerateAnother}
              </Button>
            </div>
            <ReportDetailPanel
              workspaceId={workspaceId}
              reportId={generatedReportId}
              onRegenerated={(next) => setGeneratedReportId(next.id)}
            />
          </div>
        </div>
      ) : null}

      {mode === 'ask' && temporaryChat && tempMessages.length > 0 ? (
        <div className="space-y-4 text-left">
          {tempMessages.map((message) => (
            <ConversationMessage
              key={message.id}
              message={message}
              onFollowUp={(prompt) => void askQuestion(prompt)}
            />
          ))}
        </div>
      ) : null}

      {mode === 'ask' &&
      !temporaryChat &&
      studio.conversation &&
      studio.conversation.messages.length > 0 ? (
        <div className="space-y-4 text-left">
          {studio.conversation.messages.map((message) => (
            <ConversationMessage
              key={message.id}
              message={message}
              onFollowUp={(prompt) => void askQuestion(prompt)}
            />
          ))}
        </div>
      ) : null}
      {mode === 'ask' && !temporaryChat && studio.error ? (
        <InlineRequestStatus kind="error" message={studio.error} />
      ) : null}

      <Drawer
        open={historyDrawer.isOpen}
        onClose={historyDrawer.close}
        title={UI_COPY.homeComposerHistory}
        widthClassName="max-w-sm"
      >
        <div className="h-[70vh]">
          <ConversationList
            pinned={studio.filteredConversations.pinned}
            recent={studio.filteredConversations.recent}
            activeId={temporaryChat ? null : studio.activeConversationId}
            query={studio.listQuery}
            loading={studio.listLoading}
            onQueryChange={studio.setListQuery}
            onSelect={(id) => {
              setTemporaryChat(false);
              studio.setActiveConversationId(id);
              historyDrawer.close();
            }}
            onNew={() => {
              startNewChat();
              historyDrawer.close();
            }}
            onRename={(id) => {
              const current = studio.conversations.find((item) => item.id === id);
              const next = window.prompt(
                UI_COPY.studioRenamePrompt,
                current?.title ?? '',
              );
              if (next && next.trim()) {
                void studio.renameConversation(id, next.trim());
              }
            }}
            onDelete={(id) => {
              if (window.confirm(UI_COPY.studioDeleteConfirm)) {
                void studio.deleteConversation(id);
              }
            }}
            onTogglePin={(id) => void studio.togglePin(id)}
          />
        </div>
      </Drawer>

      <WorkspaceDestinationDialog
        open={destinationDialog.isOpen}
        onClose={() => {
          if (resolvingDestination) return;
          setPendingFiles(null);
          setDestinationError(null);
          destinationDialog.close();
        }}
        workspaces={workspaces}
        activeWorkspaceId={workspaceId}
        fileCount={pendingFiles?.length ?? 0}
        submitting={resolvingDestination}
        error={destinationError}
        onConfirm={(destination) => void handleDestinationConfirm(destination)}
      />
    </section>
  );
}
