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

const DEFAULT_WORKSPACE = 'ws_ops';

const tags: KnowledgeTag[] = [
  { id: 'tag_finance', workspaceId: DEFAULT_WORKSPACE, label: 'Finance', color: '#2563EB' },
  { id: 'tag_risk', workspaceId: DEFAULT_WORKSPACE, label: 'Risk', color: '#D97706' },
  { id: 'tag_board', workspaceId: DEFAULT_WORKSPACE, label: 'Board', color: '#0F172A' },
  { id: 'tag_ops', workspaceId: DEFAULT_WORKSPACE, label: 'Operations', color: '#06B6D4' },
];

const projects = [
  { id: 'kp_growth', name: 'Growth FY26' },
  { id: 'kp_compliance', name: 'Compliance Uplift' },
  { id: 'kp_board', name: 'Board Pack 2026' },
];

const authors = [
  { id: 'usr_01', name: 'Alex Morgan' },
  { id: 'usr_02', name: 'Jordan Lee' },
  { id: 'usr_03', name: 'Sam Rivera' },
];

const collections = [
  { id: 'col_core', name: 'Core corpus' },
  { id: 'col_board', name: 'Board materials' },
  { id: 'col_risk', name: 'Risk & policy' },
];

let items: KnowledgeListItem[] = [
  {
    id: 'kn_doc_q2',
    workspaceId: DEFAULT_WORKSPACE,
    type: 'document',
    title: 'Q2 Operating Pack.pdf',
    summary: 'Margin bridges, EMEA variance, and KPI appendix.',
    status: 'verified',
    tagIds: ['tag_finance', 'tag_ops'],
    projectId: 'kp_growth',
    projectName: 'Growth FY26',
    authorId: 'usr_01',
    authorName: 'Alex Morgan',
    createdAt: '2026-07-10T09:00:00Z',
    updatedAt: '2026-07-22T14:00:00Z',
    collectionIds: ['col_core', 'col_board'],
  },
  {
    id: 'kn_doc_supplier',
    workspaceId: DEFAULT_WORKSPACE,
    type: 'document',
    title: 'Supplier Concentration Memo.docx',
    summary: 'Top vendor exposure and mitigation options.',
    status: 'indexed',
    tagIds: ['tag_risk'],
    projectId: 'kp_compliance',
    projectName: 'Compliance Uplift',
    authorId: 'usr_02',
    authorName: 'Jordan Lee',
    createdAt: '2026-07-12T11:20:00Z',
    updatedAt: '2026-07-20T08:10:00Z',
    collectionIds: ['col_risk'],
  },
  {
    id: 'kn_mtg_exec',
    workspaceId: DEFAULT_WORKSPACE,
    type: 'meeting',
    title: 'Executive Sync — 12 Jul',
    summary: 'Actions on margin, suppliers, and board narrative.',
    status: 'linked',
    tagIds: ['tag_ops', 'tag_board'],
    projectId: 'kp_board',
    projectName: 'Board Pack 2026',
    authorId: 'usr_01',
    authorName: 'Alex Morgan',
    createdAt: '2026-07-12T16:00:00Z',
    updatedAt: '2026-07-12T18:30:00Z',
    collectionIds: ['col_board'],
  },
  {
    id: 'kn_mtg_risk',
    workspaceId: DEFAULT_WORKSPACE,
    type: 'meeting',
    title: 'Risk Committee — 8 Jul',
    summary: 'Policy refresh cadence and open actions.',
    status: 'indexed',
    tagIds: ['tag_risk'],
    projectId: 'kp_compliance',
    projectName: 'Compliance Uplift',
    authorId: 'usr_03',
    authorName: 'Sam Rivera',
    createdAt: '2026-07-08T13:00:00Z',
    updatedAt: '2026-07-09T10:00:00Z',
    collectionIds: ['col_risk'],
  },
  {
    id: 'kn_rpt_q2',
    workspaceId: DEFAULT_WORKSPACE,
    type: 'report',
    title: 'Q2 Operating Review',
    summary: 'Executive narrative awaiting review.',
    status: 'verified',
    tagIds: ['tag_finance', 'tag_board'],
    projectId: 'kp_board',
    projectName: 'Board Pack 2026',
    authorId: 'usr_01',
    authorName: 'Alex Morgan',
    createdAt: '2026-07-18T12:00:00Z',
    updatedAt: '2026-07-24T12:00:00Z',
    collectionIds: ['col_board', 'col_core'],
  },
  {
    id: 'kn_rpt_retention',
    workspaceId: DEFAULT_WORKSPACE,
    type: 'report',
    title: 'Customer Retention Brief',
    summary: 'Enterprise cohort retention +3pts QoQ.',
    status: 'indexed',
    tagIds: ['tag_ops'],
    projectId: 'kp_growth',
    projectName: 'Growth FY26',
    authorId: 'usr_02',
    authorName: 'Jordan Lee',
    createdAt: '2026-07-15T09:30:00Z',
    updatedAt: '2026-07-22T09:30:00Z',
    collectionIds: ['col_core'],
  },
  {
    id: 'kn_pol_access',
    workspaceId: DEFAULT_WORKSPACE,
    type: 'policy',
    title: 'Data Access Policy v3',
    summary: 'Role-based access for knowledge and exports.',
    status: 'verified',
    tagIds: ['tag_risk'],
    projectId: 'kp_compliance',
    projectName: 'Compliance Uplift',
    authorId: 'usr_03',
    authorName: 'Sam Rivera',
    createdAt: '2026-05-01T08:00:00Z',
    updatedAt: '2026-06-15T08:00:00Z',
    collectionIds: ['col_risk'],
  },
  {
    id: 'kn_proj_growth',
    workspaceId: DEFAULT_WORKSPACE,
    type: 'project',
    title: 'Growth FY26',
    summary: 'Initiative linking operating and retention artefacts.',
    status: 'linked',
    tagIds: ['tag_ops', 'tag_finance'],
    projectId: 'kp_growth',
    projectName: 'Growth FY26',
    authorId: 'usr_01',
    authorName: 'Alex Morgan',
    createdAt: '2026-01-10T08:00:00Z',
    updatedAt: '2026-07-20T08:00:00Z',
    collectionIds: ['col_core'],
  },
  {
    id: 'kn_dec_margin',
    workspaceId: DEFAULT_WORKSPACE,
    type: 'decision',
    title: 'Refresh board KPI narrative',
    summary: 'Accepted decision from executive sync.',
    status: 'linked',
    tagIds: ['tag_board', 'tag_finance'],
    projectId: 'kp_board',
    projectName: 'Board Pack 2026',
    authorId: 'usr_01',
    authorName: 'Alex Morgan',
    createdAt: '2026-07-12T17:00:00Z',
    updatedAt: '2026-07-12T17:00:00Z',
    collectionIds: ['col_board'],
  },
  {
    id: 'kn_act_supplier',
    workspaceId: DEFAULT_WORKSPACE,
    type: 'action_item',
    title: 'Assign owner for supplier concentration',
    summary: 'Open action from 12 Jul sync.',
    status: 'processing',
    tagIds: ['tag_risk'],
    projectId: 'kp_compliance',
    projectName: 'Compliance Uplift',
    authorId: 'usr_02',
    authorName: 'Jordan Lee',
    createdAt: '2026-07-12T17:10:00Z',
    updatedAt: '2026-07-24T09:00:00Z',
    collectionIds: ['col_risk'],
  },
  {
    id: 'kn_doc_upload_demo',
    workspaceId: DEFAULT_WORKSPACE,
    type: 'document',
    title: 'Board Appendix Draft.pdf',
    summary: 'Recently uploaded — still indexing.',
    status: 'extracting',
    tagIds: ['tag_board'],
    projectId: 'kp_board',
    projectName: 'Board Pack 2026',
    authorId: 'usr_01',
    authorName: 'Alex Morgan',
    createdAt: '2026-07-24T18:00:00Z',
    updatedAt: '2026-07-24T18:05:00Z',
    collectionIds: ['col_board'],
  },
];

const relationships: KnowledgeRelationship[] = [
  {
    id: 'rel_1',
    workspaceId: DEFAULT_WORKSPACE,
    fromId: 'kn_rpt_q2',
    toId: 'kn_doc_q2',
    fromType: 'report',
    toType: 'document',
    predicate: 'derived_from',
    label: 'Derived from operating pack',
  },
  {
    id: 'rel_2',
    workspaceId: DEFAULT_WORKSPACE,
    fromId: 'kn_mtg_exec',
    toId: 'kn_dec_margin',
    fromType: 'meeting',
    toType: 'decision',
    predicate: 'decides',
    label: 'Produced decision',
  },
  {
    id: 'rel_3',
    workspaceId: DEFAULT_WORKSPACE,
    fromId: 'kn_mtg_exec',
    toId: 'kn_act_supplier',
    fromType: 'meeting',
    toType: 'action_item',
    predicate: 'assigns',
    label: 'Created action',
  },
  {
    id: 'rel_4',
    workspaceId: DEFAULT_WORKSPACE,
    fromId: 'kn_rpt_q2',
    toId: 'kn_mtg_exec',
    fromType: 'report',
    toType: 'meeting',
    predicate: 'mentions',
    label: 'References sync outcomes',
  },
  {
    id: 'rel_5',
    workspaceId: DEFAULT_WORKSPACE,
    fromId: 'kn_pol_access',
    toId: 'kn_doc_supplier',
    fromType: 'policy',
    toType: 'document',
    predicate: 'related_to',
    label: 'Governs handling',
  },
  {
    id: 'rel_6',
    workspaceId: DEFAULT_WORKSPACE,
    fromId: 'kn_proj_growth',
    toId: 'kn_rpt_retention',
    fromType: 'project',
    toType: 'report',
    predicate: 'related_to',
    label: 'Project deliverable',
  },
  {
    id: 'rel_7',
    workspaceId: DEFAULT_WORKSPACE,
    fromId: 'kn_rpt_q2',
    toId: 'kn_pol_access',
    fromType: 'report',
    toType: 'policy',
    predicate: 'cites',
    label: 'Cites access policy',
  },
];

const timelines: Record<string, KnowledgeTimelineEvent[]> = {
  kn_doc_q2: [
    { id: 't1', at: '2026-07-10T09:00:00Z', label: 'Uploaded' },
    { id: 't2', at: '2026-07-10T09:04:00Z', label: 'Extracted', detail: '48 pages' },
    { id: 't3', at: '2026-07-10T09:12:00Z', label: 'Indexed' },
    { id: 't4', at: '2026-07-22T14:00:00Z', label: 'Verified' },
  ],
  kn_doc_upload_demo: [
    { id: 't1', at: '2026-07-24T18:00:00Z', label: 'Uploaded' },
    { id: 't2', at: '2026-07-24T18:05:00Z', label: 'Extracting', detail: 'OCR in progress' },
  ],
};

const processing: Record<string, KnowledgeProcessingStatus> = {
  kn_doc_upload_demo: {
    knowledgeId: 'kn_doc_upload_demo',
    status: 'extracting',
    stage: 'Extracting text and tables',
    progressPercent: 42,
    updatedAt: '2026-07-24T18:05:00Z',
  },
  kn_act_supplier: {
    knowledgeId: 'kn_act_supplier',
    status: 'processing',
    stage: 'Linking to meetings and owners',
    progressPercent: 68,
    updatedAt: '2026-07-24T09:00:00Z',
  },
};

function cloneItem(entry: KnowledgeListItem): KnowledgeListItem {
  return {
    ...entry,
    tagIds: [...entry.tagIds],
    collectionIds: entry.collectionIds ? [...entry.collectionIds] : undefined,
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
  return {
    knowledgeId,
    status,
    stage: statusLabel(status),
    progressPercent: status === 'verified' || status === 'indexed' ? 100 : 50,
    updatedAt: entry?.updatedAt ?? new Date().toISOString(),
  };
}

export function mockUpload(
  workspaceId: string,
  input: KnowledgeUploadInput,
): KnowledgeListItem {
  const id = `kn_up_${Date.now().toString(36)}`;
  const now = new Date().toISOString();
  const created: KnowledgeListItem = {
    id,
    workspaceId,
    type: 'document',
    title: input.title?.trim() || input.fileName,
    summary: 'Upload accepted — processing started.',
    status: 'uploaded',
    tagIds: [],
    authorId: 'usr_01',
    authorName: 'Alex Morgan',
    createdAt: now,
    updatedAt: now,
    collectionIds: ['col_core'],
  };
  items = [created, ...items];
  processing[id] = {
    knowledgeId: id,
    status: 'uploaded',
    stage: 'Upload complete',
    progressPercent: 8,
    updatedAt: now,
  };

  scheduleAdvance(id, 'extracting', 35, 'Extracting text', 600);
  scheduleAdvance(id, 'processing', 55, 'Processing structure', 1400);
  scheduleAdvance(id, 'indexed', 82, 'Building search index', 2200);
  scheduleAdvance(id, 'linked', 94, 'Linking related knowledge', 3000);
  scheduleAdvance(id, 'verified', 100, 'Verified and available to AI', 3800);

  return cloneItem(created);
}

function scheduleAdvance(
  id: string,
  status: KnowledgeProcessingStatusValue,
  progressPercent: number,
  stage: string,
  delayMs: number,
) {
  if (typeof window === 'undefined') return;
  window.setTimeout(() => {
    const entry = items.find((row) => row.id === id);
    if (!entry) return;
    entry.status = status;
    entry.updatedAt = new Date().toISOString();
    if (status === 'verified') {
      entry.summary = 'Indexed and available to Intelligence Studio.';
    }
    processing[id] = {
      knowledgeId: id,
      status,
      stage,
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
    uploaded: 'Uploaded',
    extracting: 'Extracting',
    processing: 'Processing',
    indexed: 'Indexed',
    linked: 'Linked',
    verified: 'Verified',
    archived: 'Archived',
    failed: 'Failed',
  };
  return map[status];
}
