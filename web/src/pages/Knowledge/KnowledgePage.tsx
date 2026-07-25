import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Button } from '@/components/ui/Button';
import { Drawer } from '@/components/drawers/Drawer';
import { EmptyState } from '@/components/ui/EmptyState';
import { KnowledgeFilters } from '@/pages/Knowledge/KnowledgeFilters';
import { KnowledgeLibrary } from '@/pages/Knowledge/KnowledgeLibrary';
import { KnowledgePreview } from '@/pages/Knowledge/KnowledgePreview';
import { KnowledgeUploadDialog } from '@/pages/Knowledge/KnowledgeUploadDialog';
import { ROUTES, UI_COPY } from '@/constants/ui';
import { useDisclosure } from '@/hooks/useDisclosure';
import { useOrganisationalMemory } from '@/hooks/useOrganisationalMemory';
import { useWorkspace } from '@/context/WorkspaceContext';
import { useWorkspaceList } from '@/hooks/useWorkspaceList';

export function KnowledgePage() {
  const { id: routeId } = useParams<{ id?: string }>();
  const navigate = useNavigate();
  const { activeWorkspaceId, setActiveWorkspaceId } = useWorkspace();
  const { workspaces } = useWorkspaceList();
  const [selectedId, setSelectedId] = useState<string | null>(routeId ?? null);
  const memory = useOrganisationalMemory(selectedId);
  const uploadDialog = useDisclosure(false);
  const filtersDrawer = useDisclosure(false);
  const previewDrawer = useDisclosure(false);

  useEffect(() => {
    if (!activeWorkspaceId && workspaces[0]) {
      setActiveWorkspaceId(workspaces[0].id);
    }
  }, [activeWorkspaceId, workspaces, setActiveWorkspaceId]);

  useEffect(() => {
    setSelectedId(routeId ?? null);
    if (
      routeId &&
      typeof window !== 'undefined' &&
      window.matchMedia('(max-width: 1023px)').matches
    ) {
      previewDrawer.open();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [routeId]);

  function selectItem(id: string) {
    setSelectedId(id);
    navigate(`${ROUTES.knowledge}/${id}`, { replace: !routeId });
    if (
      typeof window !== 'undefined' &&
      window.matchMedia('(max-width: 1023px)').matches
    ) {
      previewDrawer.open();
    }
  }

  function clearSelectionNav() {
    setSelectedId(null);
    navigate(ROUTES.knowledge, { replace: true });
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

  const previewPanel = (
    <KnowledgePreview
      detail={memory.detail}
      processing={memory.processing}
      loading={memory.detailLoading}
      onOpenRelated={selectItem}
    />
  );

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2 lg:hidden">
        <Button variant="secondary" size="sm" onClick={filtersDrawer.open}>
          {UI_COPY.knowledgeFilters}
        </Button>
        {selectedId ? (
          <Button variant="secondary" size="sm" onClick={previewDrawer.open}>
            {UI_COPY.knowledgePreview}
          </Button>
        ) : null}
      </div>

      <div className="grid gap-4 lg:grid-cols-[240px_minmax(0,1fr)_320px] xl:grid-cols-[260px_minmax(0,1fr)_360px]">
        <div className="hidden lg:block">
          <KnowledgeFilters
            filters={memory.filters}
            options={memory.filterOptions}
            onChange={memory.setFilters}
            onReset={memory.resetFilters}
          />
        </div>

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
            void memory.removeSelected().then(() => {
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
        />

        <div className="hidden lg:block">{previewPanel}</div>
      </div>

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
        {previewPanel}
      </Drawer>

      <KnowledgeUploadDialog
        open={uploadDialog.isOpen}
        onClose={uploadDialog.close}
        workspaceId={memory.activeWorkspaceId}
        onUploaded={(item) => {
          selectItem(item.id);
        }}
      />
    </div>
  );
}

export { KnowledgePage as KnowledgeLibraryPage };
