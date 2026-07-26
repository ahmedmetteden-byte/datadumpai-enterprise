/**
 * Mutable in-memory Organisational Memory store for MockKnowledgeService.
 */

import type {
  KnowledgeDetail,
  KnowledgeFilterOptions,
  KnowledgeListItem,
  KnowledgeListQuery,
  KnowledgeListResult,
  KnowledgePreview,
  KnowledgeProcessingStatus,
  KnowledgeProcessingStatusValue,
  KnowledgeRelationship,
  KnowledgeTag,
  KnowledgeTimelineEvent,
  KnowledgeUploadInput,
} from '@/types/knowledge';
import { ApiError } from '@/api/client';

const DEFAULT_WORKSPACE = 'ws_local';

const tags: KnowledgeTag[] = [];

const projects: Array<{ id: string; name: string }> = [];

const authors: Array<{ id: string; name: string }> = [];

const collections: Array<{ id: string; name: string }> = [
  { id: 'col_core', name: 'Library' },
];

/** Live library items come from the product API; mock mode starts empty. */
let items: KnowledgeListItem[] = [];

const relationships: KnowledgeRelationship[] = [];

const timelines: Record<string, KnowledgeTimelineEvent[]> = {};

const processing: Record<string, KnowledgeProcessingStatus> = {};

function resolveTags(tagIds: string[]): string[] {
  return tagIds
    .map((id) => tags.find((tag) => tag.id === id)?.label)
    .filter((label): label is string => Boolean(label));
}

function resolveCollectionName(collectionIds?: string[]): string {
  const first = collectionIds?.[0];
  if (!first) return 'Library';
  return collections.find((c) => c.id === first)?.name ?? 'Library';
}

function cloneItem(entry: KnowledgeListItem): KnowledgeListItem {
  const filename = entry.filename || entry.title;
  const terminal =
    entry.status === 'indexed' ||
    entry.status === 'verified' ||
    entry.status === 'linked';
  return {
    ...entry,
    tagIds: [...entry.tagIds],
    tags: entry.tags ?? resolveTags(entry.tagIds),
    collectionIds: entry.collectionIds ? [...entry.collectionIds] : undefined,
    collectionName:
      entry.collectionName ?? resolveCollectionName(entry.collectionIds),
    filename,
    sizeBytes:
      typeof entry.sizeBytes === 'number'
        ? entry.sizeBytes
        : Math.max(12_000, filename.length * 4200),
    indexedAt:
      entry.indexedAt ??
      (terminal ? entry.updatedAt : null),
    progressPercent:
      typeof entry.progressPercent === 'number'
        ? entry.progressPercent
        : terminal
          ? 100
          : entry.status === 'extracting'
            ? 22
            : entry.status === 'processing'
              ? 58
              : entry.status === 'uploaded'
                ? 8
                : 0,
    indexStage:
      entry.indexStage ??
      (terminal
        ? 'indexed'
        : entry.status === 'extracting'
          ? 'extracting'
          : entry.status === 'processing'
            ? 'embedding'
            : entry.status === 'uploaded'
              ? 'queued'
              : null),
  };
}

function forWorkspace(workspaceId: string): KnowledgeListItem[] {
  return items
    .filter(
      (entry) =>
        entry.workspaceId === workspaceId || entry.workspaceId === DEFAULT_WORKSPACE,
    )
    .map((entry) => ({ ...cloneItem(entry), workspaceId }));
}

export function mockFilterOptions(workspaceId: string): KnowledgeFilterOptions {
  void workspaceId;
  return {
    tags: tags.map((tag) => ({ ...tag })),
    projects: projects.map((project) => ({ ...project })),
    authors: authors.map((author) => ({ ...author })),
    collections: collections.map((collection) => ({ ...collection })),
    types: [
      'document',
      'meeting',
      'report',
      'policy',
      'project',
      'decision',
      'action_item',
    ],
  };
}

export function mockListKnowledge(
  workspaceId: string,
  query: KnowledgeListQuery = {},
): KnowledgeListResult {
  let result = forWorkspace(workspaceId);

  if (query.types?.length) {
    result = result.filter((entry) => query.types!.includes(entry.type));
  }
  if (query.tagIds?.length) {
    result = result.filter((entry) =>
      query.tagIds!.some((tagId) => entry.tagIds.includes(tagId)),
    );
  }
  if (query.authorId) {
    result = result.filter((entry) => entry.authorId === query.authorId);
  }
  if (query.projectId) {
    result = result.filter((entry) => entry.projectId === query.projectId);
  }
  if (query.collectionId) {
    result = result.filter((entry) =>
      entry.collectionIds?.includes(query.collectionId!),
    );
  }
  if (query.status?.length) {
    result = result.filter((entry) => query.status!.includes(entry.status));
  }
  if (query.dateFrom) {
    result = result.filter((entry) => entry.updatedAt >= query.dateFrom!);
  }
  if (query.dateTo) {
    result = result.filter((entry) => entry.updatedAt <= query.dateTo!);
  }
  if (query.q?.trim()) {
    const q = query.q.trim().toLowerCase();
    result = result.filter(
      (entry) =>
        entry.title.toLowerCase().includes(q) ||
        entry.summary?.toLowerCase().includes(q),
    );
  }

  const sort = query.sort ?? 'updated_at';
  result = result.slice().sort((a, b) => {
    if (sort === 'title') return a.title.localeCompare(b.title);
    if (sort === 'created_at') return b.createdAt.localeCompare(a.createdAt);
    return b.updatedAt.localeCompare(a.updatedAt);
  });

  const limit = query.limit ?? 20;
  const offset = query.offset ?? 0;
  const page = result.slice(offset, offset + limit);

  return {
    items: page,
    total: result.length,
    limit,
    offset,
  };
}

export function mockGetKnowledge(
  workspaceId: string,
  knowledgeId: string,
): KnowledgeDetail {
  const entry = forWorkspace(workspaceId).find((row) => row.id === knowledgeId);
  if (!entry) {
    throw new ApiError('Knowledge item not found', 404, {
      detail: 'Knowledge item not found',
      code: 'knowledge_not_found',
    });
  }

  const rels = relationships
    .filter(
      (rel) =>
        (rel.fromId === knowledgeId || rel.toId === knowledgeId) &&
        (rel.workspaceId === workspaceId || rel.workspaceId === DEFAULT_WORKSPACE),
    )
    .map((rel) => ({ ...rel }));

  const relatedIds = new Set(
    rels.map((rel) => (rel.fromId === knowledgeId ? rel.toId : rel.fromId)),
  );
  const related = forWorkspace(workspaceId).filter((row) => relatedIds.has(row.id));
  const referencedBy = forWorkspace(workspaceId).filter((row) =>
    relationships.some(
      (rel) => rel.toId === knowledgeId && rel.fromId === row.id,
    ),
  );

  return {
    ...cloneItem(entry),
    metadata: {
      type: entry.type,
      status: entry.status,
      author: entry.authorName ?? null,
      project: entry.projectName ?? null,
      tags: entry.tagIds.length,
      collections: entry.collectionIds?.length ?? 0,
      mimeType: entry.type === 'document' ? 'application/pdf' : null,
      sizeBytes: entry.type === 'document' ? 2_480_000 : null,
    },
    filename: entry.type === 'document' ? entry.title : undefined,
    mimeType: entry.type === 'document' ? 'application/pdf' : undefined,
    sizeBytes: entry.type === 'document' ? 2_480_000 : undefined,
    storagePath: `/knowledge/${knowledgeId}`,
    relationships: rels,
    related,
    referencedBy,
    timeline: (
      timelines[knowledgeId] ?? [
        { id: 't0', at: entry.createdAt, label: 'Created' },
        { id: 't1', at: entry.updatedAt, label: 'Updated' },
      ]
    ).map((event) => ({ ...event })),
    versionsPlaceholder: 'Version history will appear here in a later phase.',
  };
}

export function mockPreview(
  workspaceId: string,
  knowledgeId: string,
): KnowledgePreview {
  const detail = mockGetKnowledge(workspaceId, knowledgeId);
  return {
    knowledgeId,
    kind: 'text',
    textExcerpt:
      detail.summary ??
      'Preview excerpt will render extracted text when the indexing pipeline is connected.',
    url: detail.storagePath,
  };
}

export function mockProcessingStatus(
  workspaceId: string,
  knowledgeId: string,
): KnowledgeProcessingStatus {
  void workspaceId;
  if (processing[knowledgeId]) {
    return { ...processing[knowledgeId]! };
  }
  const entry = items.find((row) => row.id === knowledgeId);
  const status: KnowledgeProcessingStatusValue = entry?.status ?? 'indexed';
  const terminal = status === 'verified' || status === 'indexed' || status === 'linked';
  return {
    knowledgeId,
    status,
    stage: statusLabel(status),
    indexStage: terminal
      ? 'indexed'
      : status === 'extracting'
        ? 'extracting'
        : status === 'processing'
          ? 'embedding'
          : 'queued',
    progressPercent: terminal ? 100 : (entry?.progressPercent ?? 50),
    updatedAt: entry?.updatedAt ?? new Date().toISOString(),
  };
}

export function mockUpload(
  workspaceId: string,
  input: KnowledgeUploadInput,
): KnowledgeListItem {
  const id = `kn_up_${Date.now().toString(36)}`;
  const now = new Date().toISOString();
  const fileName = input.file.name;
  const created: KnowledgeListItem = {
    id,
    workspaceId,
    type: 'document',
    title: input.title?.trim() || fileName.replace(/\.[^.]+$/, ''),
    summary: 'Upload accepted — indexing started.',
    status: 'uploaded',
    tagIds: [],
    tags: [],
    authorId: 'usr_local',
    authorName: 'You',
    createdAt: now,
    updatedAt: now,
    collectionIds: ['col_core'],
    collectionName: 'Library',
    filename: fileName,
    mimeType: input.file.type || 'application/octet-stream',
    sizeBytes: input.file.size,
    indexedAt: null,
    progressPercent: 8,
    indexStage: 'queued',
  };
  items = [created, ...items];
  processing[id] = {
    knowledgeId: id,
    status: 'uploaded',
    stage: 'Indexing...',
    indexStage: 'queued',
    progressPercent: 8,
    updatedAt: now,
  };

  // Upload → Extract text → Chunk → Embeddings → Qdrant → Indexed
  scheduleAdvance(id, 'extracting', 22, 'Extract text', 'extracting', 700);
  scheduleAdvance(id, 'processing', 34, 'Chunk', 'chunking', 1400);
  scheduleAdvance(id, 'processing', 58, 'Embeddings', 'embedding', 2200);
  scheduleAdvance(id, 'processing', 82, 'Qdrant', 'upserting', 3000);
  scheduleAdvance(id, 'indexed', 100, 'Done', 'indexed', 3800);

  return cloneItem(created);
}

export function mockReindex(
  workspaceId: string,
  knowledgeId: string,
): KnowledgeProcessingStatus {
  const entry = items.find((row) => row.id === knowledgeId);
  if (
    !entry ||
    !forWorkspace(workspaceId).some((row) => row.id === knowledgeId)
  ) {
    throw new ApiError('Knowledge item not found', 404, {
      detail: 'Knowledge item not found',
    });
  }
  const now = new Date().toISOString();
  entry.status = 'uploaded';
  entry.progressPercent = 8;
  entry.indexStage = 'queued';
  entry.indexedAt = null;
  entry.updatedAt = now;
  processing[knowledgeId] = {
    knowledgeId,
    status: 'uploaded',
    stage: 'Indexing...',
    indexStage: 'queued',
    progressPercent: 8,
    updatedAt: now,
  };
  scheduleAdvance(knowledgeId, 'extracting', 22, 'Extract text', 'extracting', 700);
  scheduleAdvance(knowledgeId, 'processing', 34, 'Chunk', 'chunking', 1400);
  scheduleAdvance(knowledgeId, 'processing', 58, 'Embeddings', 'embedding', 2200);
  scheduleAdvance(knowledgeId, 'processing', 82, 'Qdrant', 'upserting', 3000);
  scheduleAdvance(knowledgeId, 'indexed', 100, 'Done', 'indexed', 3800);
  return { ...processing[knowledgeId]! };
}

function scheduleAdvance(
  id: string,
  status: KnowledgeProcessingStatusValue,
  progressPercent: number,
  stage: string,
  indexStage: string,
  delayMs: number,
) {
  if (typeof window === 'undefined') return;
  window.setTimeout(() => {
    const entry = items.find((row) => row.id === id);
    if (!entry) return;
    entry.status = status;
    entry.progressPercent = progressPercent;
    entry.indexStage = indexStage;
    entry.updatedAt = new Date().toISOString();
    if (status === 'indexed') {
      entry.indexedAt = entry.updatedAt;
      entry.summary = 'Indexed and available to Intelligence Studio.';
    }
    processing[id] = {
      knowledgeId: id,
      status,
      stage,
      indexStage,
      progressPercent,
      updatedAt: entry.updatedAt,
    };
  }, delayMs);
}

export function mockDelete(workspaceId: string, knowledgeId: string): void {
  const exists = forWorkspace(workspaceId).some((row) => row.id === knowledgeId);
  if (!exists) {
    throw new ApiError('Knowledge item not found', 404, {
      detail: 'Knowledge item not found',
    });
  }
  items = items.filter((row) => row.id !== knowledgeId);
  delete processing[knowledgeId];
}

export function mockTag(
  workspaceId: string,
  knowledgeId: string,
  tagIds: string[],
): KnowledgeListItem {
  const entry = items.find((row) => row.id === knowledgeId);
  if (
    !entry ||
    !forWorkspace(workspaceId).some((row) => row.id === knowledgeId)
  ) {
    throw new ApiError('Knowledge item not found', 404, {
      detail: 'Knowledge item not found',
    });
  }
  entry.tagIds = [...tagIds];
  entry.updatedAt = new Date().toISOString();
  return cloneItem({ ...entry, workspaceId });
}

export function mockRelated(
  workspaceId: string,
  knowledgeId: string,
): KnowledgeRelationship[] {
  mockGetKnowledge(workspaceId, knowledgeId);
  return relationships
    .filter((rel) => rel.fromId === knowledgeId || rel.toId === knowledgeId)
    .map((rel) => ({ ...rel }));
}

function statusLabel(status: KnowledgeProcessingStatusValue): string {
  const map: Record<KnowledgeProcessingStatusValue, string> = {
    uploaded: 'Indexing...',
    extracting: 'Extract text',
    processing: 'Chunk',
    indexed: 'Done',
    linked: 'Done',
    verified: 'Done',
    archived: 'Archived',
    failed: 'Indexing failed',
  };
  return map[status];
}
