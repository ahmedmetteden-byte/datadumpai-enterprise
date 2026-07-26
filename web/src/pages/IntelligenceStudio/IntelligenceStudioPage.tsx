import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { InlineRequestStatus } from '@/components/feedback';
import { Button } from '@/components/ui/Button';
import { Drawer } from '@/components/drawers/Drawer';
import { EmptyState } from '@/components/ui/EmptyState';
import { Modal } from '@/components/ui/Modal';
import { ROUTES, UI_COPY } from '@/constants/ui';
import { useWorkspace } from '@/context/WorkspaceContext';
import { useDisclosure } from '@/hooks/useDisclosure';
import { useIntelligenceStudio } from '@/hooks/useIntelligenceStudio';
import { useWorkspaceList } from '@/hooks/useWorkspaceList';
import { CitationPanel } from './CitationPanel';
import { ConversationList } from './ConversationList';
import { ConversationView } from './ConversationView';
import type {
  IntelligenceCitation,
  IntelligenceSource,
} from '@/types/intelligence';

export function IntelligenceStudioPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { activeWorkspaceId, setActiveWorkspaceId } = useWorkspace();
  const { workspaces } = useWorkspaceList();
  const studio = useIntelligenceStudio();
  const sourcesDrawer = useDisclosure(false);
  const conversationsDrawer = useDisclosure(false);
  const [preview, setPreview] = useState<IntelligenceSource | null>(null);
  const [panelCitations, setPanelCitations] = useState<IntelligenceCitation[]>(
    [],
  );

  const workspaceName =
    workspaces.find((item) => item.id === activeWorkspaceId)?.name ?? null;

  useEffect(() => {
    if (!activeWorkspaceId && workspaces[0]) {
      setActiveWorkspaceId(workspaces[0].id);
    }
  }, [activeWorkspaceId, workspaces, setActiveWorkspaceId]);

  useEffect(() => {
    const prefill = searchParams.get('q');
    if (prefill && activeWorkspaceId) {
      void studio.sendMessage(prefill);
      searchParams.delete('q');
      setSearchParams(searchParams, { replace: true });
    }
    // intentionally once per q param
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeWorkspaceId]);

  const latestAssistant = [...(studio.conversation?.messages ?? [])]
    .reverse()
    .find((message) => message.role === 'assistant' && message.status === 'complete');
  const latestConfidence = latestAssistant?.confidence;
  const evidenceCitations =
    panelCitations.length > 0
      ? panelCitations
      : (latestAssistant?.citations ?? []);

  function handleRename(id: string) {
    const current = studio.conversations.find((item) => item.id === id);
    const next = window.prompt(
      UI_COPY.studioRenamePrompt,
      current?.title ?? '',
    );
    if (next && next.trim()) {
      void studio.renameConversation(id, next.trim());
    }
  }

  function handleDelete(id: string) {
    if (window.confirm(UI_COPY.studioDeleteConfirm)) {
      void studio.deleteConversation(id);
    }
  }

  function openSource(source: IntelligenceSource) {
    setPreview(source);
  }

  if (!activeWorkspaceId) {
    return (
      <EmptyState
        className="min-h-[50vh]"
        title={UI_COPY.studioTitle}
        description={UI_COPY.studioSelectWorkspace}
        actionLabel={UI_COPY.workspacesTitle}
        actionHref={ROUTES.workspaces}
      />
    );
  }

  const askDisabled = Boolean(studio.readiness && !studio.readiness.canAsk);

  return (
    <div className="-mx-4 -mb-6 flex min-h-[calc(100vh-7.5rem)] flex-col sm:-mx-6 lg:-mx-10 lg:min-h-[calc(100vh-6.5rem)]">
      {studio.listLoading && !studio.error ? (
        <InlineRequestStatus
          kind="loading"
          message={UI_COPY.requestLoading}
          className="rounded-none border-x-0 border-t-0"
        />
      ) : null}
      {studio.error ? (
        <InlineRequestStatus
          kind="error"
          message={studio.error}
          onRetry={() => void studio.refreshList()}
          className="rounded-none border-x-0 border-t-0"
        />
      ) : null}
      {askDisabled ? (
        <div className="border-b border-warning/30 bg-amber-50 px-4 py-2 text-small text-warning">
          {UI_COPY.studioCannotAsk}
        </div>
      ) : null}

      <div className="grid min-h-0 flex-1 lg:grid-cols-[16.5rem_minmax(0,1fr)_19rem]">
        <div className="hidden min-h-0 lg:block">
          <ConversationList
            pinned={studio.filteredConversations.pinned}
            recent={studio.filteredConversations.recent}
            activeId={studio.activeConversationId}
            query={studio.listQuery}
            loading={studio.listLoading}
            onQueryChange={studio.setListQuery}
            onSelect={studio.setActiveConversationId}
            onNew={() => void studio.startNewConversation()}
            onRename={handleRename}
            onDelete={handleDelete}
            onTogglePin={(id) => void studio.togglePin(id)}
          />
        </div>

        <div className="relative flex min-h-0 min-w-0 flex-col">
          <div className="flex gap-2 border-b border-surface-border bg-white px-3 py-2 lg:hidden">
            <Button
              size="sm"
              variant="secondary"
              onClick={conversationsDrawer.open}
            >
              {UI_COPY.studioOpenConversations}
            </Button>
            <Button
              size="sm"
              variant="secondary"
              onClick={() => void studio.startNewConversation()}
            >
              {UI_COPY.studioNewConversation}
            </Button>
            <Button
              size="sm"
              variant="secondary"
              onClick={sourcesDrawer.open}
              className="ml-auto"
            >
              {UI_COPY.studioOpenSources}
            </Button>
          </div>

          <ConversationView
            workspaceName={workspaceName}
            readiness={studio.readiness}
            conversation={studio.conversation}
            suggestions={studio.suggestions}
            mode={studio.mode}
            sending={studio.sending}
            disabled={askDisabled}
            onModeChange={studio.setMode}
            onSend={(content) => void studio.sendMessage(content)}
            onSelectSources={(message) => {
              studio.setSelectedSources(
                message.linkedDocuments?.length
                  ? message.linkedDocuments
                  : (message.sources ?? []),
              );
              setPanelCitations(message.citations ?? []);
              sourcesDrawer.open();
            }}
          />
        </div>

        <div className="hidden min-h-0 lg:block">
          <CitationPanel
            sources={studio.selectedSources}
            citations={evidenceCitations}
            confidence={latestConfidence}
            onOpenSource={openSource}
          />
        </div>
      </div>

      <Drawer
        open={conversationsDrawer.isOpen}
        onClose={conversationsDrawer.close}
        title={UI_COPY.studioConversations}
        widthClassName="max-w-sm"
      >
        <div className="h-[70vh]">
          <ConversationList
            pinned={studio.filteredConversations.pinned}
            recent={studio.filteredConversations.recent}
            activeId={studio.activeConversationId}
            query={studio.listQuery}
            loading={studio.listLoading}
            onQueryChange={studio.setListQuery}
            onSelect={(id) => {
              studio.setActiveConversationId(id);
              conversationsDrawer.close();
            }}
            onNew={() => {
              void studio.startNewConversation();
              conversationsDrawer.close();
            }}
            onRename={handleRename}
            onDelete={handleDelete}
            onTogglePin={(id) => void studio.togglePin(id)}
          />
        </div>
      </Drawer>

      <Drawer
        open={sourcesDrawer.isOpen}
        onClose={sourcesDrawer.close}
        title={UI_COPY.studioEvidence}
        widthClassName="max-w-md"
      >
        <CitationPanel
          sources={studio.selectedSources}
          citations={evidenceCitations}
          confidence={latestConfidence}
          onOpenSource={openSource}
        />
      </Drawer>

      <Modal
        open={Boolean(preview)}
        onClose={() => setPreview(null)}
        title={preview?.title ?? UI_COPY.studioSourcePreview}
        footer={
          <Button variant="secondary" onClick={() => setPreview(null)}>
            {UI_COPY.cancel}
          </Button>
        }
      >
        {preview ? (
          <div className="space-y-3 text-small text-ink-muted">
            <p className="capitalize text-caption text-ink-faint">
              {preview.kind}
            </p>
            {preview.excerpt ? (
              <p className="text-body text-ink">{preview.excerpt}</p>
            ) : null}
            {preview.location ? (
              <p className="font-mono text-caption">{preview.location}</p>
            ) : null}
            <p className="text-caption">{UI_COPY.studioPreviewNote}</p>
          </div>
        ) : null}
      </Modal>
    </div>
  );
}
