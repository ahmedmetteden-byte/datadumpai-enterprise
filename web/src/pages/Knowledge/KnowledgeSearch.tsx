import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { UI_COPY } from '@/constants/ui';
import type { KnowledgeListQuery } from '@/types/knowledge';
import type { KnowledgeViewMode } from '@/hooks/useOrganisationalMemory';

export function KnowledgeSearch({
  q,
  onQueryChange,
  semantic,
  onSemanticChange,
  sort,
  onSortChange,
  viewMode,
  onViewModeChange,
}: {
  q: string;
  onQueryChange: (value: string) => void;
  semantic: boolean;
  onSemanticChange: (value: boolean) => void;
  sort: KnowledgeListQuery['sort'];
  onSortChange: (value: KnowledgeListQuery['sort']) => void;
  viewMode: KnowledgeViewMode;
  onViewModeChange: (mode: KnowledgeViewMode) => void;
}) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div className="min-w-0 flex-1 space-y-2">
        <label className="block text-caption font-medium text-ink-muted">
          {UI_COPY.knowledgeSearchLabel}
        </label>
        <Input
          value={q}
          onChange={(event) => onQueryChange(event.target.value)}
          placeholder={UI_COPY.knowledgeSearchPlaceholder}
          aria-label={UI_COPY.knowledgeSearchLabel}
        />
        <label className="inline-flex items-center gap-2 text-small text-ink-muted">
          <input
            type="checkbox"
            checked={semantic}
            onChange={(event) => onSemanticChange(event.target.checked)}
            className="h-4 w-4 rounded border-surface-border text-brand-500 focus:ring-brand-500"
          />
          {UI_COPY.knowledgeSemanticSearch}
        </label>
      </div>
      <div className="flex flex-wrap items-end gap-2">
        <div>
          <label
            htmlFor="knowledge-sort"
            className="mb-1 block text-caption font-medium text-ink-muted"
          >
            {UI_COPY.knowledgeSort}
          </label>
          <Select
            id="knowledge-sort"
            value={sort ?? 'updated_at'}
            onChange={(event) =>
              onSortChange(event.target.value as KnowledgeListQuery['sort'])
            }
          >
            <option value="updated_at">{UI_COPY.knowledgeSortUpdated}</option>
            <option value="created_at">{UI_COPY.knowledgeSortCreated}</option>
            <option value="title">{UI_COPY.knowledgeSortTitle}</option>
            <option value="relevance">{UI_COPY.knowledgeSortRelevance}</option>
          </Select>
        </div>
        <div
          role="group"
          aria-label={UI_COPY.knowledgeViewMode}
          className="flex rounded-md border border-surface-border bg-white p-0.5"
        >
          <button
            type="button"
            aria-pressed={viewMode === 'grid'}
            onClick={() => onViewModeChange('grid')}
            className={`rounded px-3 py-1.5 text-small font-medium ${
              viewMode === 'grid'
                ? 'bg-brand-50 text-brand-700'
                : 'text-ink-muted hover:text-ink'
            }`}
          >
            {UI_COPY.knowledgeViewGrid}
          </button>
          <button
            type="button"
            aria-pressed={viewMode === 'table'}
            onClick={() => onViewModeChange('table')}
            className={`rounded px-3 py-1.5 text-small font-medium ${
              viewMode === 'table'
                ? 'bg-brand-50 text-brand-700'
                : 'text-ink-muted hover:text-ink'
            }`}
          >
            {UI_COPY.knowledgeViewTable}
          </button>
        </div>
      </div>
    </div>
  );
}
