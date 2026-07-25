import { useCallback, useEffect, useMemo, useState } from 'react';
import { services } from '@/api/services';
import { useWorkspace } from '@/context/WorkspaceContext';
import type {
  KnowledgeDetail,
  KnowledgeEntityType,
  KnowledgeFilterOptions,
  KnowledgeListItem,
  KnowledgeListQuery,
  KnowledgeProcessingStatus,
  KnowledgeProcessingStatusValue,
  KnowledgeUploadInput,
} from '@/types/knowledge';

const PAGE_SIZE = 12;

export type KnowledgeViewMode = 'grid' | 'table';

export interface KnowledgeFiltersState {
  types: KnowledgeEntityType[];
  tagIds: string[];
  authorId: string | null;
  projectId: string | null;
  collectionId: string | null;
  status: KnowledgeProcessingStatusValue[];
  dateFrom: string;
  dateTo: string;
  semantic: boolean;
}

const emptyFilters: KnowledgeFiltersState = {
  types: [],
  tagIds: [],
  authorId: null,
  projectId: null,
  collectionId: null,
  status: [],
  dateFrom: '',
  dateTo: '',
  semantic: false,
};

export function useOrganisationalMemory(selectedId: string | null) {
  const { activeWorkspaceId, revision, bumpRevision } = useWorkspace();
  const [items, setItems] = useState<KnowledgeListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [q, setQ] = useState('');
  const [sort, setSort] =
    useState<KnowledgeListQuery['sort']>('updated_at');
  const [filters, setFilters] = useState<KnowledgeFiltersState>(emptyFilters);
  const [filterOptions, setFilterOptions] =
    useState<KnowledgeFilterOptions | null>(null);
  const [viewMode, setViewMode] = useState<KnowledgeViewMode>('grid');
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [detail, setDetail] = useState<KnowledgeDetail | null>(null);
  const [processing, setProcessing] =
    useState<KnowledgeProcessingStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasEverLoaded, setHasEverLoaded] = useState(false);

  const query = useMemo<KnowledgeListQuery>(() => {
    return {
      q: q.trim() || undefined,
      semantic: filters.semantic || undefined,
      types: filters.types.length ? filters.types : undefined,
      tagIds: filters.tagIds.length ? filters.tagIds : undefined,
      authorId: filters.authorId ?? undefined,
      projectId: filters.projectId ?? undefined,
      collectionId: filters.collectionId ?? undefined,
      status: filters.status.length ? filters.status : undefined,
      dateFrom: filters.dateFrom || undefined,
      dateTo: filters.dateTo || undefined,
      sort,
      limit: PAGE_SIZE,
      offset,
    };
  }, [q, filters, sort, offset]);

  const reload = useCallback(async () => {
    if (!activeWorkspaceId) {
      setItems([]);
      setTotal(0);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const [list, options] = await Promise.all([
        services.knowledge.search(activeWorkspaceId, query),
        services.knowledge.getFilterOptions(activeWorkspaceId),
      ]);
      setItems(list.items);
      setTotal(list.total);
      setFilterOptions(options);
      setHasEverLoaded(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load knowledge');
    } finally {
      setLoading(false);
    }
  }, [activeWorkspaceId, query]);

  useEffect(() => {
    void reload();
  }, [reload, revision]);

  useEffect(() => {
    setOffset(0);
  }, [
    q,
    filters,
    sort,
    activeWorkspaceId,
  ]);

  useEffect(() => {
    if (!activeWorkspaceId || !selectedId) {
      setDetail(null);
      setProcessing(null);
      return;
    }
    let cancelled = false;
    setDetailLoading(true);
    void (async () => {
      try {
        const [nextDetail, nextProcessing] = await Promise.all([
          services.knowledge.getKnowledge(activeWorkspaceId, selectedId),
          services.knowledge.processingStatus(activeWorkspaceId, selectedId),
        ]);
        if (!cancelled) {
          setDetail(nextDetail);
          setProcessing(nextProcessing);
        }
      } catch {
        if (!cancelled) {
          setDetail(null);
          setProcessing(null);
        }
      } finally {
        if (!cancelled) setDetailLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [activeWorkspaceId, selectedId, revision]);

  // Poll processing for in-flight items
  useEffect(() => {
    if (!activeWorkspaceId || !selectedId || !processing) return;
    const inFlight = ['uploaded', 'extracting', 'processing', 'indexed', 'linked'];
    const done =
      processing.status === 'verified' ||
      processing.status === 'failed' ||
      processing.status === 'archived' ||
      processing.progressPercent === 100;
    if (done || !inFlight.includes(processing.status)) return;

    const timer = window.setInterval(() => {
      void services.knowledge
        .processingStatus(activeWorkspaceId, selectedId)
        .then((status) => {
          setProcessing(status);
          if (
            status.progressPercent === 100 ||
            status.status === 'verified'
          ) {
            bumpRevision();
          }
        });
    }, 700);
    return () => window.clearInterval(timer);
  }, [activeWorkspaceId, selectedId, processing, bumpRevision]);

  const upload = useCallback(
    async (input: KnowledgeUploadInput) => {
      if (!activeWorkspaceId) return null;
      const created = await services.knowledge.upload(activeWorkspaceId, input);
      bumpRevision();
      return created;
    },
    [activeWorkspaceId, bumpRevision],
  );

  const remove = useCallback(
    async (knowledgeId: string) => {
      if (!activeWorkspaceId) return;
      await services.knowledge.delete(activeWorkspaceId, knowledgeId);
      setSelectedIds((prev) => prev.filter((id) => id !== knowledgeId));
      bumpRevision();
    },
    [activeWorkspaceId, bumpRevision],
  );

  const removeSelected = useCallback(async () => {
    if (!activeWorkspaceId || selectedIds.length === 0) return;
    await Promise.all(
      selectedIds.map((id) => services.knowledge.delete(activeWorkspaceId, id)),
    );
    setSelectedIds([]);
    bumpRevision();
  }, [activeWorkspaceId, selectedIds, bumpRevision]);

  const toggleSelect = useCallback((id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id],
    );
  }, []);

  const toggleSelectAll = useCallback(() => {
    setSelectedIds((prev) =>
      prev.length === items.length ? [] : items.map((item) => item.id),
    );
  }, [items]);

  const page = Math.floor(offset / PAGE_SIZE) + 1;
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return {
    activeWorkspaceId,
    items,
    total,
    offset,
    setOffset,
    page,
    pageCount,
    pageSize: PAGE_SIZE,
    q,
    setQ,
    sort,
    setSort,
    filters,
    setFilters,
    resetFilters: () => setFilters(emptyFilters),
    filterOptions,
    viewMode,
    setViewMode,
    selectedIds,
    toggleSelect,
    toggleSelectAll,
    clearSelection: () => setSelectedIds([]),
    detail,
    detailLoading,
    processing,
    loading,
    error,
    hasEverLoaded,
    upload,
    remove,
    removeSelected,
    reload,
  };
}
