import { useCallback, useEffect, useMemo, useState } from 'react';
import { services } from '@/api/services';
import { useAuth } from '@/context/AuthContext';
import { useWorkspace } from '@/context/WorkspaceContext';
import type {
  KnowledgeDetail,
  KnowledgeEntityType,
  KnowledgeFilterOptions,
  KnowledgeListItem,
  KnowledgeListQuery,
  KnowledgeProcessingStatus,
  KnowledgeProcessingStatusValue,
  KnowledgePreview,
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

function isTerminalStatus(status: KnowledgeProcessingStatusValue): boolean {
  return (
    status === 'indexed' ||
    status === 'verified' ||
    status === 'failed' ||
    status === 'archived'
  );
}

export function useOrganisationalMemory(selectedId: string | null) {
  const { activeWorkspaceId, revision, bumpRevision } = useWorkspace();
  const { accessToken } = useAuth();
  const auth = useMemo(() => ({ accessToken }), [accessToken]);
  const [items, setItems] = useState<KnowledgeListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [q, setQ] = useState('');
  const [sort, setSort] =
    useState<KnowledgeListQuery['sort']>('updated_at');
  const [filters, setFilters] = useState<KnowledgeFiltersState>(emptyFilters);
  const [filterOptions, setFilterOptions] =
    useState<KnowledgeFilterOptions | null>(null);
  const [viewMode, setViewMode] = useState<KnowledgeViewMode>('table');
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [detail, setDetail] = useState<KnowledgeDetail | null>(null);
  const [preview, setPreview] = useState<KnowledgePreview | null>(null);
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
        services.knowledge.search(activeWorkspaceId, query, auth),
        services.knowledge.getFilterOptions(activeWorkspaceId, auth),
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
  }, [activeWorkspaceId, query, auth]);

  useEffect(() => {
    void reload();
  }, [reload, revision]);

  useEffect(() => {
    setOffset(0);
  }, [q, filters, sort, activeWorkspaceId]);

  useEffect(() => {
    if (!activeWorkspaceId || !selectedId) {
      setDetail(null);
      setPreview(null);
      setProcessing(null);
      return;
    }
    let cancelled = false;
    setDetailLoading(true);
    void (async () => {
      try {
        const [nextDetail, nextProcessing, nextPreview] = await Promise.all([
          services.knowledge.getKnowledge(activeWorkspaceId, selectedId, auth),
          services.knowledge.processingStatus(
            activeWorkspaceId,
            selectedId,
            auth,
          ),
          services.knowledge.preview(activeWorkspaceId, selectedId, auth).catch(
            () => null,
          ),
        ]);
        if (!cancelled) {
          setDetail(nextDetail);
          setProcessing(nextProcessing);
          setPreview(nextPreview);
        }
      } catch {
        if (!cancelled) {
          setDetail(null);
          setProcessing(null);
          setPreview(null);
        }
      } finally {
        if (!cancelled) setDetailLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [activeWorkspaceId, selectedId, revision, auth]);

  useEffect(() => {
    if (!activeWorkspaceId || !selectedId || !processing) return;
    if (isTerminalStatus(processing.status)) return;

    const timer = window.setInterval(() => {
      void services.knowledge
        .processingStatus(activeWorkspaceId, selectedId, auth)
        .then((status) => {
          setProcessing(status);
          if (isTerminalStatus(status.status)) {
            bumpRevision();
          }
        });
    }, 700);
    return () => window.clearInterval(timer);
  }, [activeWorkspaceId, selectedId, processing, bumpRevision, auth]);

  // Keep the library list fresh while any row is still indexing
  useEffect(() => {
    if (!activeWorkspaceId) return;
    const inFlight = items.some(
      (item) =>
        item.status === 'uploaded' ||
        item.status === 'extracting' ||
        item.status === 'processing',
    );
    if (!inFlight) return;

    const timer = window.setInterval(() => {
      bumpRevision();
    }, 1200);
    return () => window.clearInterval(timer);
  }, [activeWorkspaceId, items, bumpRevision]);

  const upload = useCallback(
    async (input: KnowledgeUploadInput) => {
      if (!activeWorkspaceId) return null;
      const created = await services.knowledge.upload(
        activeWorkspaceId,
        input,
        auth,
      );
      bumpRevision();
      return created;
    },
    [activeWorkspaceId, bumpRevision, auth],
  );

  const remove = useCallback(
    async (knowledgeId: string) => {
      if (!activeWorkspaceId) return;
      await services.knowledge.delete(activeWorkspaceId, knowledgeId, auth);
      setSelectedIds((prev) => prev.filter((id) => id !== knowledgeId));
      bumpRevision();
    },
    [activeWorkspaceId, bumpRevision, auth],
  );

  const removeSelected = useCallback(async () => {
    if (!activeWorkspaceId || selectedIds.length === 0) return;
    await Promise.all(
      selectedIds.map((id) =>
        services.knowledge.delete(activeWorkspaceId, id, auth),
      ),
    );
    setSelectedIds([]);
    bumpRevision();
  }, [activeWorkspaceId, selectedIds, bumpRevision, auth]);

  const reindex = useCallback(
    async (knowledgeId: string) => {
      if (!activeWorkspaceId) return;
      const next = await services.knowledge.reindex(
        activeWorkspaceId,
        knowledgeId,
        auth,
      );
      setProcessing(next);
      bumpRevision();
    },
    [activeWorkspaceId, auth, bumpRevision],
  );

  const download = useCallback(
    async (knowledgeId: string, filename?: string) => {
      if (!activeWorkspaceId) return;
      const blob = await services.knowledge.download(
        activeWorkspaceId,
        knowledgeId,
        auth,
      );
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = filename || 'download';
      anchor.click();
      URL.revokeObjectURL(url);
    },
    [activeWorkspaceId, auth],
  );

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
    preview,
    detailLoading,
    processing,
    loading,
    error,
    hasEverLoaded,
    upload,
    remove,
    removeSelected,
    reindex,
    download,
    reload,
  };
}
