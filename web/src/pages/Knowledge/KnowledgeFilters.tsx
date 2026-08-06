import type { ReactNode } from 'react';
import { Button } from '@/components/ui/Button';
import { UI_COPY } from '@/constants/ui';
import {
  KNOWLEDGE_TYPE_LABELS,
  PROCESSING_STATUS_LABELS,
} from '@/lib/knowledgeLabels';
import type { KnowledgeFilterOptions, KnowledgeEntityType, KnowledgeProcessingStatusValue } from '@/types/knowledge';
import type { KnowledgeFiltersState } from '@/hooks/useOrganisationalMemory';

function FilterSection({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <section className="space-y-2 border-b border-surface-border pb-4 last:border-0">
      <h3 className="text-caption font-semibold uppercase tracking-wide text-ink-muted">
        {title}
      </h3>
      {children}
    </section>
  );
}

export function KnowledgeFilters({
  filters,
  options,
  onChange,
  onReset,
}: {
  filters: KnowledgeFiltersState;
  options: KnowledgeFilterOptions | null;
  onChange: (next: KnowledgeFiltersState) => void;
  onReset: () => void;
}) {
  function toggleType(type: KnowledgeEntityType) {
    const types = filters.types.includes(type)
      ? filters.types.filter((value) => value !== type)
      : [...filters.types, type];
    onChange({ ...filters, types });
  }

  function toggleTag(tagId: string) {
    const tagIds = filters.tagIds.includes(tagId)
      ? filters.tagIds.filter((value) => value !== tagId)
      : [...filters.tagIds, tagId];
    onChange({ ...filters, tagIds });
  }

  function toggleStatus(status: KnowledgeProcessingStatusValue) {
    const next = filters.status.includes(status)
      ? filters.status.filter((value) => value !== status)
      : [...filters.status, status];
    onChange({ ...filters, status: next });
  }

  const hasCollections = Boolean(options?.collections?.length);
  const hasTags = Boolean(options?.tags?.length);
  const hasProjects = Boolean(options?.projects?.length);
  const hasAuthors = Boolean(options?.authors?.length);

  return (
    <div className="space-y-4" aria-label={UI_COPY.knowledgeFilters}>
      <div className="flex items-center justify-between gap-2">
        <p className="text-small text-ink-muted">
          {UI_COPY.knowledgeFilterWorkspaceHint}
        </p>
        <Button variant="ghost" size="sm" onClick={onReset}>
          {UI_COPY.knowledgeResetFilters}
        </Button>
      </div>

      <FilterSection title={UI_COPY.knowledgeFilterType}>
        <div className="space-y-1.5">
          {(options?.types ?? []).map((type) => (
            <label
              key={type}
              className="flex items-center gap-2 text-small text-ink"
            >
              <input
                type="checkbox"
                checked={filters.types.includes(type)}
                onChange={() => toggleType(type)}
                className="h-4 w-4 rounded border-surface-border text-brand-500 focus:ring-brand-500"
              />
              {KNOWLEDGE_TYPE_LABELS[type]}
            </label>
          ))}
        </div>
      </FilterSection>

      <FilterSection title={UI_COPY.knowledgeFilterStatus}>
        <div className="space-y-1.5">
          {(
            Object.keys(PROCESSING_STATUS_LABELS) as KnowledgeProcessingStatusValue[]
          ).map((status) => (
            <label
              key={status}
              className="flex items-center gap-2 text-small text-ink"
            >
              <input
                type="checkbox"
                checked={filters.status.includes(status)}
                onChange={() => toggleStatus(status)}
                className="h-4 w-4 rounded border-surface-border text-brand-500 focus:ring-brand-500"
              />
              {PROCESSING_STATUS_LABELS[status]}
            </label>
          ))}
        </div>
      </FilterSection>

      <FilterSection title={UI_COPY.knowledgeFilterDate}>
        <div className="grid grid-cols-1 gap-2">
          <label className="text-caption text-ink-muted">
            {UI_COPY.knowledgeDateFrom}
            <input
              type="date"
              value={filters.dateFrom}
              onChange={(event) =>
                onChange({ ...filters, dateFrom: event.target.value })
              }
              className="mt-1 w-full rounded-md border border-surface-border px-3 py-2 text-small"
            />
          </label>
          <label className="text-caption text-ink-muted">
            {UI_COPY.knowledgeDateTo}
            <input
              type="date"
              value={filters.dateTo}
              onChange={(event) =>
                onChange({ ...filters, dateTo: event.target.value })
              }
              className="mt-1 w-full rounded-md border border-surface-border px-3 py-2 text-small"
            />
          </label>
        </div>
      </FilterSection>

      {hasCollections ? (
        <FilterSection title={UI_COPY.knowledgeFilterCollections}>
          <div className="space-y-1.5">
            {(options?.collections ?? []).map((collection) => (
              <label
                key={collection.id}
                className="flex items-center gap-2 text-small text-ink"
              >
                <input
                  type="radio"
                  name="collection"
                  checked={filters.collectionId === collection.id}
                  onChange={() =>
                    onChange({ ...filters, collectionId: collection.id })
                  }
                  className="h-4 w-4 border-surface-border text-brand-500 focus:ring-brand-500"
                />
                {collection.name}
              </label>
            ))}
            <button
              type="button"
              className="text-caption text-brand-600 hover:underline"
              onClick={() => onChange({ ...filters, collectionId: null })}
            >
              {UI_COPY.knowledgeAnyCollection}
            </button>
          </div>
        </FilterSection>
      ) : null}

      {hasTags ? (
        <FilterSection title={UI_COPY.knowledgeFilterTags}>
          <div className="flex flex-wrap gap-2">
            {(options?.tags ?? []).map((tag) => {
              const active = filters.tagIds.includes(tag.id);
              return (
                <button
                  key={tag.id}
                  type="button"
                  aria-pressed={active}
                  onClick={() => toggleTag(tag.id)}
                  className={`rounded-full px-2.5 py-1 text-caption font-medium ${
                    active
                      ? 'bg-brand-500 text-white'
                      : 'bg-surface-alt text-ink-muted hover:bg-brand-50'
                  }`}
                >
                  {tag.label}
                </button>
              );
            })}
          </div>
        </FilterSection>
      ) : null}

      {hasProjects ? (
        <FilterSection title={UI_COPY.knowledgeFilterProjects}>
          <select
            className="w-full rounded-md border border-surface-border bg-white px-3 py-2 text-small text-ink focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
            value={filters.projectId ?? ''}
            onChange={(event) =>
              onChange({
                ...filters,
                projectId: event.target.value || null,
              })
            }
            aria-label={UI_COPY.knowledgeFilterProjects}
          >
            <option value="">{UI_COPY.knowledgeAnyProject}</option>
            {(options?.projects ?? []).map((project) => (
              <option key={project.id} value={project.id}>
                {project.name}
              </option>
            ))}
          </select>
        </FilterSection>
      ) : null}

      {hasAuthors ? (
        <FilterSection title={UI_COPY.knowledgeFilterAuthors}>
          <select
            className="w-full rounded-md border border-surface-border bg-white px-3 py-2 text-small text-ink focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
            value={filters.authorId ?? ''}
            onChange={(event) =>
              onChange({
                ...filters,
                authorId: event.target.value || null,
              })
            }
            aria-label={UI_COPY.knowledgeFilterAuthors}
          >
            <option value="">{UI_COPY.knowledgeAnyAuthor}</option>
            {(options?.authors ?? []).map((author) => (
              <option key={author.id} value={author.id}>
                {author.name}
              </option>
            ))}
          </select>
        </FilterSection>
      ) : null}
    </div>
  );
}
