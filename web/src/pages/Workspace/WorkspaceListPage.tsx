import { useNavigate } from 'react-router-dom';
import { PageRequestState } from '@/components/feedback';
import { Button } from '@/components/ui/Button';
import { EmptyState } from '@/components/ui/EmptyState';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { UI_COPY } from '@/constants/ui';
import { useWorkspace } from '@/context/WorkspaceContext';
import { useDisclosure } from '@/hooks/useDisclosure';
import { useWorkspaceList } from '@/hooks/useWorkspaceList';
import { formatRelativeTime } from '@/lib/format';
import { formatStorageBytes } from '@/lib/workspacePermissions';
import { WORKSPACE_ROUTES } from '@/lib/workspaceRoutes';
import { CreateWorkspaceDialog } from './dialogs/CreateWorkspaceDialog';

export function WorkspaceListPage() {
  const navigate = useNavigate();
  const { setActiveWorkspaceId } = useWorkspace();
  const { workspaces, loading, error, reload } = useWorkspaceList();
  const createDialog = useDisclosure(false);

  function openWorkspace(id: string) {
    setActiveWorkspaceId(id);
    navigate(WORKSPACE_ROUTES.section(id, 'overview'));
  }

  return (
    <PageRequestState
      loading={loading && workspaces.length === 0}
      error={error && workspaces.length === 0 ? error : null}
      onRetry={reload}
      loadingMessage={UI_COPY.loadingWorkspaces}
      errorTitle={UI_COPY.workspacesLoadError}
    >
      <div className="space-y-8 pb-16">
        <SectionHeader
          title={UI_COPY.workspacesTitle}
          description={UI_COPY.workspacesSubtitle}
          action={
            workspaces.length > 0 ? (
              <Button onClick={createDialog.open}>
                {UI_COPY.createWorkspace}
              </Button>
            ) : undefined
          }
        />

        {workspaces.length === 0 ? (
          <EmptyState
            icon="◈"
            title={UI_COPY.emptyWorkspacesTitle}
            description={UI_COPY.emptyWorkspacesDescription}
            actionLabel={UI_COPY.createWorkspace}
            onAction={createDialog.open}
          />
        ) : (
          <ul className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {workspaces.map((workspace) => (
              <li key={workspace.id}>
                <button
                  type="button"
                  onClick={() => openWorkspace(workspace.id)}
                  className="flex h-full w-full flex-col rounded-xl border border-surface-border bg-white p-5 text-left transition-all duration-200 hover:-translate-y-0.5 hover:border-brand-200 hover:shadow-card focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
                >
                  <h3 className="text-card text-ink">{workspace.name}</h3>
                  <p className="mt-2 line-clamp-2 flex-1 text-small text-ink-muted">
                    {workspace.description || '—'}
                  </p>
                  <div className="mt-4 flex items-center justify-between gap-2 text-caption text-ink-faint">
                    <span>
                      {UI_COPY.lastUpdated}{' '}
                      {formatRelativeTime(workspace.lastActivity)}
                    </span>
                    <span>{formatStorageBytes(workspace.storageUsed)}</span>
                  </div>
                  <span className="mt-4 text-small font-medium text-brand-600">
                    {UI_COPY.openWorkspace} →
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}

        <CreateWorkspaceDialog
          open={createDialog.isOpen}
          onClose={createDialog.close}
          onCreated={(id) => openWorkspace(id)}
        />
      </div>
    </PageRequestState>
  );
}
