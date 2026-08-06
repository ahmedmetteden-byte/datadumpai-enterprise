import { useEffect, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { Button } from '@/components/ui/Button';
import { Drawer } from '@/components/drawers/Drawer';
import { EmptyState } from '@/components/ui/EmptyState';
import { EyebrowBadge } from '@/components/ui/EyebrowBadge';
import { KnowledgeFilters } from '@/pages/Knowledge/KnowledgeFilters';
import { KnowledgeLibrary } from '@/pages/Knowledge/KnowledgeLibrary';
import { KnowledgePreview } from '@/pages/Knowledge/KnowledgePreview';
import { KnowledgeUploadDialog } from '@/pages/Knowledge/KnowledgeUploadDialog';
import { ReportDetailPanel } from '@/pages/Reports/ReportDetailPanel';
import { ReportsListPanel } from '@/pages/Reports/ReportsListPanel';
import { ROUTES, UI_COPY } from '@/constants/ui';
import { useRequestFeedback } from '@/context/RequestFeedbackContext';
import { useDisclosure } from '@/hooks/useDisclosure';
import { useOrganisationalMemory } from '@/hooks/useOrganisationalMemory';
import { useWorkspace } from '@/context/WorkspaceContext';
import { useWorkspaceList } from '@/hooks/useWorkspaceList';
import { cn } from '@/lib/cn';

type LibraryTab = 'documents' | 'reports';

export function KnowledgePage() {
  const { id: routeId } = useParams<{ id?: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const feedback = useRequestFeedback();
  const { activeWorkspaceId, setActiveWorkspaceId, bumpRevision } =
    useWorkspace();
  const { workspaces } = useWorkspaceList();
  const [selectedId, setSelectedId] = useState<string | null>(routeId ?? null);
  const memory = useOrganisationalMemory(selectedId);
  const uploadDialog = useDisclosure(false);
  const filtersDrawer = useDisclosure(false);
  const previewDrawer = useDisclosure(false);
  const [tab, setTab] = useState<LibraryTab>('documents');
  const [selectedReportId, setSelectedReportId] = useState<string | null>(
    null,
  );
  const [reportsRefreshKey, setReportsRefreshKey] = useState(0);

  useEffect(() => {
    if (!activeWorkspaceId && workspaces[0]) {
      setActiveWorkspaceId(workspaces[0].id);
    }
  }, [activeWorkspaceId, workspaces, setActiveWorkspaceId]);

  useEffect(() => {
    if (searchParams.get('upload') === '1') {
      uploadDialog.open();
      const next = new URLSearchParams(searchParams);
      next.delete('upload');
      setSearchParams(next, { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  useEffect(() => {
    setSelectedId(routeId ?? null);
    if (routeId) {
      previewDrawer.open();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [routeId]);

  function selectItem(id: string) {
    setSelectedId(id);
    navigate(`${ROUTES.library}/${id}`, { replace: !routeId });
    previewDrawer.open();
  }

  function clearSelectionNav() {
    setSelectedId(null);
    navigate(ROUTES.library, { replace: true });
  }

  function runAction(action: () => Promise<unknown>, successMessage?: string) {
    void feedback
      .run(action, {
        loading: UI_COPY.requestLoading,
        success: successMessage ?? UI_COPY.requestSuccess,
        error: UI_COPY.requestError,
      })
      .catch(() => {
        /* Error toast includes Retry */
      });
  }

  if (!memory.activeWorkspaceId) {
    return (
      <EmptyState
        className="min-h-[50vh]"
        title={UI_COPY.knowledgeTitle}
        description={UI_COPY.knowledgeSelectWorkspace}
        actionLabel={UI_COPY.workspacesTitle}
        actionHref={ROUTES.workspaces}
      />
    );
  }

  const hasQuery =
    Boolean(memory.q.trim()) ||
    memory.filters.types.length > 0 ||
    memory.filters.tagIds.length > 0 ||
    Boolean(memory.filters.authorId) ||
    Boolean(memory.filters.projectId) ||
    Boolean(memory.filters.collectionId) ||
    memory.filters.status.length > 0 ||
    Boolean(memory.filters.dateFrom) ||
    Boolean(memory.filters.dateTo);

  return (
    <div className="space-y-4 pb-16">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <EyebrowBadge>{UI_COPY.libraryEyebrow}</EyebrowBadge>
          <h1 className="mt-2 text-page-title text-ink">
            {UI_COPY.knowledgeTitle}
          </h1>
        </div>
        {tab === 'documents' ? (
          <Button onClick={uploadDialog.open}>{UI_COPY.knowledgeUpload}</Button>
        ) : null}
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => setTab('documents')}
            className={cn(
              'rounded-full px-4 py-1.5 text-small font-medium transition-colors',
              tab === 'documents'
                ? 'bg-brand-500 text-white'
                : 'bg-surface-alt text-ink-muted hover:text-ink',
            )}
          >
            {UI_COPY.libraryTabDocuments}
          </button>
          <button
            type="button"
            onClick={() => setTab('reports')}
            className={cn(
              'rounded-full px-4 py-1.5 text-small font-medium transition-colors',
              tab === 'reports'
                ? 'bg-brand-500 text-white'
                : 'bg-surface-alt text-ink-muted hover:text-ink',
            )}
          >
            {UI_COPY.libraryTabReports}
          </button>
        </div>
        {tab === 'documents' ? (
          <Button variant="secondary" size="sm" onClick={filtersDrawer.open}>
            {UI_COPY.knowledgeFilters}
          </Button>
        ) : null}
      </div>

      {tab === 'reports' ? (
        <ReportsListPanel
          workspaceId={memory.activeWorkspaceId}
          refreshKey={reportsRefreshKey}
          onSelect={setSelectedReportId}
        />
      ) : null}

      {tab === 'documents' ? (
        <KnowledgeLibrary
          items={memory.items}
          total={memory.total}
          loading={memory.loading}
          error={memory.error}
          hasQuery={hasQuery}
          selectedId={selectedId}
          selectedIds={memory.selectedIds}
          viewMode={memory.viewMode}
          q={memory.q}
          sort={memory.sort}
          semantic={memory.filters.semantic}
          page={memory.page}
          pageCount={memory.pageCount}
          onQueryChange={memory.setQ}
          onSemanticChange={(value) =>
            memory.setFilters({ ...memory.filters, semantic: value })
          }
          onSortChange={memory.setSort}
          onViewModeChange={memory.setViewMode}
          onSelect={selectItem}
          onToggleCheck={memory.toggleSelect}
          onToggleAll={memory.toggleSelectAll}
          onClearSelection={memory.clearSelection}
          onDeleteSelected={() => {
            if (!window.confirm(UI_COPY.knowledgeBulkDeleteConfirm)) return;
            const removingSelected =
              selectedId != null && memory.selectedIds.includes(selectedId);
            runAction(async () => {
              await memory.removeSelected();
              if (removingSelected) clearSelectionNav();
            });
          }}
          onPageChange={(page) =>
            memory.setOffset((page - 1) * memory.pageSize)
          }
          onUpload={uploadDialog.open}
          onClearSearch={() => {
            memory.setQ('');
            memory.resetFilters();
          }}
          onRetry={() => void memory.reload()}
          onView={selectItem}
          onDelete={(id) => {
            if (!window.confirm(UI_COPY.knowledgeBulkDeleteConfirm)) return;
            runAction(async () => {
              await memory.remove(id);
              if (selectedId === id) clearSelectionNav();
            });
          }}
          onReindex={(id) => runAction(() => memory.reindex(id))}
          onDownload={(id) => {
            const item = memory.items.find((row) => row.id === id);
            runAction(() =>
              memory.download(id, item?.filename || item?.title),
            );
          }}
        />
      ) : null}

      <Drawer
        open={filtersDrawer.isOpen}
        onClose={filtersDrawer.close}
        title={UI_COPY.knowledgeFilters}
        widthClassName="max-w-sm"
      >
        <KnowledgeFilters
          filters={memory.filters}
          options={memory.filterOptions}
          onChange={memory.setFilters}
          onReset={memory.resetFilters}
        />
      </Drawer>

      <Drawer
        open={previewDrawer.isOpen}
        onClose={() => {
          previewDrawer.close();
        }}
        title={UI_COPY.knowledgePreview}
        widthClassName="max-w-md"
      >
        <KnowledgePreview
          detail={memory.detail}
          preview={memory.preview}
          processing={memory.processing}
          loading={memory.detailLoading}
          onOpenRelated={selectItem}
          onReindex={() => {
            if (!selectedId) return;
            runAction(() => memory.reindex(selectedId));
          }}
          onDownload={() => {
            if (!selectedId) return;
            runAction(() =>
              memory.download(
                selectedId,
                memory.detail?.filename || memory.detail?.title,
              ),
            );
          }}
          onDelete={() => {
            if (!selectedId) return;
            if (!window.confirm(UI_COPY.knowledgeBulkDeleteConfirm)) return;
            runAction(async () => {
              await memory.remove(selectedId);
              clearSelectionNav();
            });
          }}
        />
      </Drawer>

      <KnowledgeUploadDialog
        open={uploadDialog.isOpen}
        onClose={uploadDialog.close}
        workspaceId={memory.activeWorkspaceId}
        onUploaded={(item) => {
          bumpRevision();
          feedback.notifySuccess(UI_COPY.knowledgeUploadSuccessToast);
          selectItem(item.id);
        }}
      />

      <Drawer
        open={Boolean(selectedReportId)}
        onClose={() => setSelectedReportId(null)}
        title={UI_COPY.reportsTitle}
        widthClassName="max-w-2xl"
      >
        {selectedReportId && memory.activeWorkspaceId ? (
          <ReportDetailPanel
            workspaceId={memory.activeWorkspaceId}
            reportId={selectedReportId}
            onSaved={() => setReportsRefreshKey((value) => value + 1)}
            onRegenerated={(next) => {
              setSelectedReportId(next.id);
              setReportsRefreshKey((value) => value + 1);
            }}
          />
        ) : null}
      </Drawer>
    </div>
  );
}

export { KnowledgePage as KnowledgeLibraryPage };
