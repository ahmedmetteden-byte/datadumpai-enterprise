import { apiRequest, apiUpload } from '@/api/client';
import { mockLatency, type ServiceAuth } from '@/api/config';
import type { KnowledgeService } from '@/api/services/contracts';
import { mockSearchSuggestions } from '@/api/mock/data';
import {
  mockDelete,
  mockFilterOptions,
  mockGetKnowledge,
  mockListKnowledge,
  mockPreview,
  mockProcessingStatus,
  mockReindex,
  mockRelated,
  mockTag,
  mockUpload,
} from '@/api/mock/knowledgeStore';
import type { UniversalSearchPayload } from '@/types/home';
import type {
  KnowledgeDetail,
  KnowledgeFilterOptions,
  KnowledgeListItem,
  KnowledgeListQuery,
  KnowledgeListResult,
  KnowledgePreview,
  KnowledgeProcessingStatus,
  KnowledgeRelationship,
  KnowledgeUploadInput,
} from '@/types/knowledge';

function toQueryString(query: KnowledgeListQuery = {}): string {
  const params = new URLSearchParams();
  if (query.q) params.set('q', query.q);
  if (query.semantic) params.set('semantic', '1');
  if (query.types?.length) params.set('types', query.types.join(','));
  if (query.tagIds?.length) params.set('tagIds', query.tagIds.join(','));
  if (query.authorId) params.set('authorId', query.authorId);
  if (query.projectId) params.set('projectId', query.projectId);
  if (query.collectionId) params.set('collectionId', query.collectionId);
  if (query.dateFrom) params.set('dateFrom', query.dateFrom);
  if (query.dateTo) params.set('dateTo', query.dateTo);
  if (query.status?.length) params.set('status', query.status.join(','));
  if (query.limit != null) params.set('limit', String(query.limit));
  if (query.offset != null) params.set('offset', String(query.offset));
  if (query.sort) params.set('sort', query.sort);
  const qs = params.toString();
  return qs ? `?${qs}` : '';
}

export class MockKnowledgeService implements KnowledgeService {
  async getSearchSuggestions(workspaceId: string) {
    await mockLatency(80);
    void workspaceId;
    return mockSearchSuggestions;
  }

  async search(workspaceId: string, query: KnowledgeListQuery) {
    await mockLatency(120);
    return mockListKnowledge(workspaceId, {
      ...query,
      sort: query.sort ?? (query.q ? 'relevance' : 'updated_at'),
    });
  }

  async listKnowledge(workspaceId: string, query: KnowledgeListQuery = {}) {
    await mockLatency(100);
    return mockListKnowledge(workspaceId, query);
  }

  async getKnowledge(workspaceId: string, knowledgeId: string) {
    await mockLatency(90);
    return mockGetKnowledge(workspaceId, knowledgeId);
  }

  async upload(workspaceId: string, input: KnowledgeUploadInput) {
    await mockLatency(180);
    input.onProgress?.(35);
    await mockLatency(80);
    input.onProgress?.(70);
    await mockLatency(60);
    input.onProgress?.(100);
    return mockUpload(workspaceId, input);
  }

  async delete(workspaceId: string, knowledgeId: string) {
    await mockLatency(80);
    mockDelete(workspaceId, knowledgeId);
  }

  async tag(workspaceId: string, knowledgeId: string, tagIds: string[]) {
    await mockLatency(80);
    return mockTag(workspaceId, knowledgeId, tagIds);
  }

  async related(workspaceId: string, knowledgeId: string) {
    await mockLatency(80);
    return mockRelated(workspaceId, knowledgeId);
  }

  async preview(workspaceId: string, knowledgeId: string) {
    await mockLatency(70);
    return mockPreview(workspaceId, knowledgeId);
  }

  async processingStatus(workspaceId: string, knowledgeId: string) {
    await mockLatency(40);
    return mockProcessingStatus(workspaceId, knowledgeId);
  }

  async reindex(workspaceId: string, knowledgeId: string) {
    await mockLatency(80);
    return mockReindex(workspaceId, knowledgeId);
  }

  async download(workspaceId: string, knowledgeId: string) {
    await mockLatency(60);
    void workspaceId;
    void knowledgeId;
    return new Blob(['mock file contents'], { type: 'text/plain' });
  }

  async getFilterOptions(workspaceId: string) {
    await mockLatency(60);
    return mockFilterOptions(workspaceId);
  }
}

export class HttpKnowledgeService implements KnowledgeService {
  async getSearchSuggestions(workspaceId: string, auth?: ServiceAuth) {
    return apiRequest<UniversalSearchPayload>(
      `/api/v1/workspaces/${workspaceId}/search/suggestions`,
      { token: auth?.accessToken },
    );
  }

  async search(
    workspaceId: string,
    query: KnowledgeListQuery,
    auth?: ServiceAuth,
  ) {
    return apiRequest<KnowledgeListResult>(
      `/api/v1/workspaces/${workspaceId}/knowledge/search${toQueryString(query)}`,
      { token: auth?.accessToken },
    );
  }

  async listKnowledge(
    workspaceId: string,
    query: KnowledgeListQuery = {},
    auth?: ServiceAuth,
  ) {
    return apiRequest<KnowledgeListResult>(
      `/api/v1/workspaces/${workspaceId}/knowledge${toQueryString(query)}`,
      { token: auth?.accessToken },
    );
  }

  async getKnowledge(
    workspaceId: string,
    knowledgeId: string,
    auth?: ServiceAuth,
  ) {
    return apiRequest<KnowledgeDetail>(
      `/api/v1/workspaces/${workspaceId}/knowledge/${knowledgeId}`,
      { token: auth?.accessToken },
    );
  }

  async upload(
    workspaceId: string,
    input: KnowledgeUploadInput,
    auth?: ServiceAuth,
  ) {
    const form = new FormData();
    form.append('file', input.file, input.file.name);
    if (input.title?.trim()) {
      form.append('title', input.title.trim());
    }
    return apiUpload<KnowledgeListItem>(
      `/api/v1/workspaces/${workspaceId}/knowledge/upload`,
      form,
      { token: auth?.accessToken, onProgress: input.onProgress },
    );
  }

  async delete(
    workspaceId: string,
    knowledgeId: string,
    auth?: ServiceAuth,
  ) {
    await apiRequest<void>(
      `/api/v1/workspaces/${workspaceId}/knowledge/${knowledgeId}`,
      { method: 'DELETE', token: auth?.accessToken },
    );
  }

  async tag(
    workspaceId: string,
    knowledgeId: string,
    tagIds: string[],
    auth?: ServiceAuth,
  ) {
    return apiRequest<KnowledgeListItem>(
      `/api/v1/workspaces/${workspaceId}/knowledge/${knowledgeId}/tags`,
      {
        method: 'PUT',
        body: { tagIds },
        token: auth?.accessToken,
      },
    );
  }

  async related(
    workspaceId: string,
    knowledgeId: string,
    auth?: ServiceAuth,
  ) {
    return apiRequest<KnowledgeRelationship[]>(
      `/api/v1/workspaces/${workspaceId}/knowledge/${knowledgeId}/related`,
      { token: auth?.accessToken },
    );
  }

  async preview(
    workspaceId: string,
    knowledgeId: string,
    auth?: ServiceAuth,
  ) {
    return apiRequest<KnowledgePreview>(
      `/api/v1/workspaces/${workspaceId}/knowledge/${knowledgeId}/preview`,
      { token: auth?.accessToken },
    );
  }

  async processingStatus(
    workspaceId: string,
    knowledgeId: string,
    auth?: ServiceAuth,
  ) {
    return apiRequest<KnowledgeProcessingStatus>(
      `/api/v1/workspaces/${workspaceId}/knowledge/${knowledgeId}/processing`,
      { token: auth?.accessToken },
    );
  }

  async reindex(
    workspaceId: string,
    knowledgeId: string,
    auth?: ServiceAuth,
  ) {
    return apiRequest<KnowledgeProcessingStatus>(
      `/api/v1/workspaces/${workspaceId}/knowledge/${knowledgeId}/reindex`,
      { method: 'POST', token: auth?.accessToken },
    );
  }

  async download(
    workspaceId: string,
    knowledgeId: string,
    auth?: ServiceAuth,
  ) {
    const base = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(
      /\/$/,
      '',
    ) ?? '';
    const response = await fetch(
      `${base}/api/v1/workspaces/${workspaceId}/knowledge/${knowledgeId}/download`,
      {
        headers: {
          ...(auth?.accessToken
            ? { Authorization: `Bearer ${auth.accessToken}` }
            : {}),
        },
      },
    );
    if (!response.ok) {
      throw new Error(`Download failed (${response.status})`);
    }
    return response.blob();
  }

  async getFilterOptions(workspaceId: string, auth?: ServiceAuth) {
    return apiRequest<KnowledgeFilterOptions>(
      `/api/v1/workspaces/${workspaceId}/knowledge/filters`,
      { token: auth?.accessToken },
    );
  }
}
