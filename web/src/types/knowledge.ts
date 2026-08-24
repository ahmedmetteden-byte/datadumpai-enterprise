import type { IsoDateTime, Paginated } from './api';

export type KnowledgeEntityType =
  | 'document'
  | 'meeting'
  | 'report'
  | 'policy'
  | 'project'
  | 'decision'
  | 'action_item';

/** Phase 4 processing / lifecycle badges */
export type KnowledgeProcessingStatusValue =
  | 'uploaded'
  | 'extracting'
  | 'processing'
  | 'indexed'
  | 'linked'
  | 'verified'
  | 'archived'
  | 'failed';

export interface KnowledgeTag {
  id: string;
  workspaceId: string;
  label: string;
  color?: string;
}

export interface KnowledgeListItem {
  id: string;
  workspaceId: string;
  type: KnowledgeEntityType;
  title: string;
  summary?: string;
  status: KnowledgeProcessingStatusValue;
  tagIds: string[];
  /** Display labels for tags */
  tags?: string[];
  projectId?: string | null;
  projectName?: string | null;
  authorId?: string;
  authorName?: string;
  updatedAt: IsoDateTime;
  createdAt: IsoDateTime;
  collectionIds?: string[];
  collectionName?: string | null;
  filename?: string;
  mimeType?: string;
  sizeBytes?: number;
  indexedAt?: IsoDateTime | null;
  /** 0–100 while indexing */
  progressPercent?: number;
  /** Pipeline stage key: queued | extracting | chunking | embedding | upserting | indexed */
  indexStage?: string | null;
}

export interface KnowledgeRelationship {
  id: string;
  workspaceId: string;
  fromId: string;
  toId: string;
  fromType: KnowledgeEntityType;
  toType: KnowledgeEntityType;
  predicate:
    | 'cites'
    | 'derived_from'
    | 'decides'
    | 'assigns'
    | 'mentions'
    | 'supersedes'
    | 'related_to';
  label?: string;
}

export interface KnowledgeTimelineEvent {
  id: string;
  at: IsoDateTime;
  label: string;
  detail?: string;
}

export interface KnowledgeDetail extends KnowledgeListItem {
  metadata: Record<string, string | number | boolean | null>;
  storagePath?: string;
  filename?: string;
  mimeType?: string;
  sizeBytes?: number;
  relationships: KnowledgeRelationship[];
  related: KnowledgeListItem[];
  referencedBy: KnowledgeListItem[];
  timeline: KnowledgeTimelineEvent[];
  versionsPlaceholder: string;
}

export interface KnowledgePreview {
  knowledgeId: string;
  kind: 'text' | 'pdf' | 'html' | 'unsupported';
  textExcerpt?: string;
  url?: string;
}

export interface KnowledgeProcessingStatus {
  knowledgeId: string;
  status: KnowledgeProcessingStatusValue;
  stage: string;
  /** Pipeline stage key from the API */
  indexStage?: string | null;
  progressPercent?: number;
  errorMessage?: string;
  updatedAt: IsoDateTime;
}

export interface KnowledgeListQuery {
  q?: string;
  semantic?: boolean;
  types?: KnowledgeEntityType[];
  tagIds?: string[];
  authorId?: string;
  projectId?: string;
  collectionId?: string;
  dateFrom?: string;
  dateTo?: string;
  status?: KnowledgeProcessingStatusValue[];
  limit?: number;
  offset?: number;
  sort?: 'updated_at' | 'created_at' | 'title' | 'relevance';
}

export interface KnowledgeUploadInput {
  file: File;
  title?: string;
  /** ISO date (YYYY-MM-DD) the document's content covers, for period-scoped reports */
  periodDate?: string;
  /** Transfer progress 0–100 while posting to the API */
  onProgress?: (percent: number) => void;
}

export interface KnowledgeFilterOptions {
  tags: KnowledgeTag[];
  projects: Array<{ id: string; name: string }>;
  authors: Array<{ id: string; name: string }>;
  collections: Array<{ id: string; name: string }>;
  types: KnowledgeEntityType[];
}

export type KnowledgeListResult = Paginated<KnowledgeListItem>;
