import { Button } from '@/components/ui/Button';
import { EmptyKnowledge } from '@/pages/Knowledge/EmptyKnowledge';
import { KnowledgeCard } from '@/pages/Knowledge/KnowledgeCard';
import { KnowledgeSearch } from '@/pages/Knowledge/KnowledgeSearch';
import { KnowledgeTable } from '@/pages/Knowledge/KnowledgeTable';
import { UI_COPY } from '@/constants/ui';
import type { KnowledgeListItem, KnowledgeListQuery } from '@/types/knowledge';
import type {
  KnowledgeFiltersState,
  KnowledgeViewMode,
} from '@/hooks/useOrganisationalMemory';

export function KnowledgeLibrary({
  items,
  total,
  loading,
  error,
  hasQuery,
  selectedId,
  selectedIds,
  viewMode,
  q,
  sort,
  semantic,
  page,
  pageCount,
  onQueryChange,
  onSemanticChange,
  onSortChange,
  onViewModeChange,
  onSelect,
  onToggleCheck,
  onToggleAll,
  onClearSelection,
  onDeleteSelected,
  onPageChange,
  onUpload,
  onClearSearch,
  onRetry,
}: {
  items: KnowledgeListItem[];
  total: number;
  loading: boolean;
  error: string | null;
  hasQuery: boolean;
  selectedId: string | null;
  selectedIds: string[];
  viewMode: KnowledgeViewMode;
  q: string;
  sort: KnowledgeListQuery['sort'];
  semantic: boolean;
  page: number;
  pageCount: number;
  onQueryChange: (value: string) => void;
  onSemanticChange: (value: boolean) => void;
  onSortChange: (value: KnowledgeListQuery['sort']) => void;
  onViewModeChange: (mode: KnowledgeViewMode) => void;
  onSelect: (id: string) => void;
  onToggleCheck: (id: string) => void;
  onToggleAll: () => void;
  onClearSelection: () => void;
  onDeleteSelected: () => void;
  onPageChange: (page: number) => void;
  onUpload: () => void;
  onClearSearch: () => void;
  onRetry: () => void;
  filters?: KnowledgeFiltersState;
}) {
  return (
    <section
      className="flex min-w-0 flex-1 flex-col gap-4"
      aria-label={UI_COPY.knowledgeLibrary}
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-page-title text-ink">{UI_COPY.knowledgeTitle}</h1>
          <p className="mt-1 text-small text-ink-muted">
            {UI_COPY.knowledgeSubtitle}
          </p>
        </div>
        <Button onClick={onUpload}>{UI_COPY.knowledgeUpload}</Button>
      </div>

      <KnowledgeSearch
        q={q}
        onQueryChange={onQueryChange}
        semantic={semantic}
        onSemanticChange={onSemanticChange}
        sort={sort}
        onSortChange={onSortChange}
        viewMode={viewMode}
        onViewModeChange={onViewModeChange}
      />

      {selectedIds.length > 0 ? (
        <div
          className="flex flex-wrap items-center gap-2 rounded-lg border border-surface-border bg-white px-3 py-2"
          role="status"
        >
          <span className="text-small text-ink">
            {UI_COPY.knowledgeSelectedCount.replace(
              '{count}',
              String(selectedIds.length),
            )}
          </span>
          <Button size="sm" variant="danger" onClick={onDeleteSelected}>
            {UI_COPY.knowledgeBulkDelete}
          </Button>
          <Button size="sm" variant="ghost" onClick={onClearSelection}>
            {UI_COPY.knowledgeClearSelection}
          </Button>
        </div>
      ) : null}

      {error ? (
        <div className="rounded-xl border border-dashed border-surface-border bg-white px-6 py-10 text-center">
          <p className="text-section text-ink">{UI_COPY.knowledgeLoadError}</p>
          <p className="mt-1 text-small text-ink-muted">{error}</p>
          <Button className="mt-4" onClick={onRetry}>
            {UI_COPY.retry}
          </Button>
        </div>
      ) : loading ? (
        <div
          className="rounded-xl border border-surface-border bg-white px-6 py-16 text-center text-small text-ink-muted"
          role="status"
        >
          {UI_COPY.knowledgeLoading}
        </div>
      ) : items.length === 0 ? (
        <EmptyKnowledge
          variant={hasQuery ? 'search' : 'none'}
          onUpload={onUpload}
          onClearSearch={onClearSearch}
        />
      ) : viewMode === 'grid' ? (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-2 2xl:grid-cols-3">
          {items.map((item) => (
            <KnowledgeCard
              key={item.id}
              item={item}
              selected={selectedId === item.id}
              checked={selectedIds.includes(item.id)}
              onSelect={() => onSelect(item.id)}
              onToggleCheck={() => onToggleCheck(item.id)}
            />
          ))}
        </div>
      ) : (
        <KnowledgeTable
          items={items}
          selectedId={selectedId}
          selectedIds={selectedIds}
          onSelect={onSelect}
          onToggleCheck={onToggleCheck}
          onToggleAll={onToggleAll}
        />
      )}

      {!loading && !error && total > 0 ? (
        <div className="flex flex-wrap items-center justify-between gap-2 text-small text-ink-muted">
          <span>
            {UI_COPY.knowledgeResultCount
              .replace('{count}', String(total))
              .replace('{page}', String(page))
              .replace('{pages}', String(pageCount))}
          </span>
          <div className="flex gap-2">
            <Button
              size="sm"
              variant="secondary"
              disabled={page <= 1}
              onClick={() => onPageChange(page - 1)}
            >
              {UI_COPY.knowledgePrevPage}
            </Button>
            <Button
              size="sm"
              variant="secondary"
              disabled={page >= pageCount}
              onClick={() => onPageChange(page + 1)}
            >
              {UI_COPY.knowledgeNextPage}
            </Button>
          </div>
        </div>
      ) : null}
    </section>
  );
}
