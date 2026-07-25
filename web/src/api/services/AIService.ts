import { apiRequest } from '@/api/client';
import { mockLatency, type ServiceAuth } from '@/api/config';
import type { AIService } from '@/api/services/contracts';
import {
  mockInsights,
  mockRecommendations,
  mockTodaysBrief,
} from '@/api/mock/data';
import type {
  AiRecommendation,
  TodaysBrief,
  WorkspaceInsight,
} from '@/types/home';

export class MockAIService implements AIService {
  async getTodaysBrief(workspaceId: string) {
    await mockLatency(80);
    void workspaceId;
    return mockTodaysBrief;
  }

  async getRecommendations(workspaceId: string) {
    await mockLatency(80);
    void workspaceId;
    return mockRecommendations;
  }

  async listInsights(workspaceId: string) {
    await mockLatency(80);
    void workspaceId;
    return mockInsights;
  }
}

export class HttpAIService implements AIService {
  async getTodaysBrief(workspaceId: string, auth?: ServiceAuth) {
    return apiRequest<TodaysBrief>(
      `/api/v1/workspaces/${workspaceId}/ai/brief`,
      { token: auth?.accessToken },
    );
  }

  async getRecommendations(workspaceId: string, auth?: ServiceAuth) {
    return apiRequest<AiRecommendation[]>(
      `/api/v1/workspaces/${workspaceId}/ai/recommendations`,
      { token: auth?.accessToken },
    );
  }

  async listInsights(workspaceId: string, auth?: ServiceAuth) {
    return apiRequest<WorkspaceInsight[]>(
      `/api/v1/workspaces/${workspaceId}/ai/insights`,
      { token: auth?.accessToken },
    );
  }
}
