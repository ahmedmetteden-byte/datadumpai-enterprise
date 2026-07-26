import { apiRequest } from '@/api/client';
import { mockLatency, type ServiceAuth } from '@/api/config';
import type { WorkspaceService } from '@/api/services/contracts';
import {
  mockActivity,
  mockContinueWorking,
  mockHealth,
  mockInsightsOverview,
  mockOrgIntelligence,
} from '@/api/mock/data';
import {
  archiveWorkspaceRecord,
  createWorkspaceRecord,
  getActiveWorkspace,
  getMembershipForCurrentUser,
  getTeamForWorkspace,
  listActiveWorkspaces,
  updateWorkspaceRecord,
} from '@/api/mock/workspaceStore';
import type { ActivityLog, Project } from '@/types/api';
import type {
  ContinueWorkingItem,
  OrgIntelligenceSignal,
  TeamMember,
  WorkspaceHealthSummary,
  WorkspaceInsightsOverview,
} from '@/types/home';
import type {
  CreateWorkspaceInput,
  UpdateWorkspaceInput,
  WorkspaceMembership,
} from '@/types/workspace';

export class MockWorkspaceService implements WorkspaceService {
  async listWorkspaces(): Promise<Project[]> {
    await mockLatency();
    return listActiveWorkspaces();
  }

  async getWorkspace(workspaceId: string): Promise<Project> {
    await mockLatency(80);
    return getActiveWorkspace(workspaceId);
  }

  async createWorkspace(input: CreateWorkspaceInput): Promise<Project> {
    await mockLatency(120);
    if (!input.name.trim()) {
      throw new Error('Workspace name is required');
    }
    return createWorkspaceRecord(input);
  }

  async updateWorkspace(
    workspaceId: string,
    input: UpdateWorkspaceInput,
  ): Promise<Project> {
    await mockLatency(120);
    return updateWorkspaceRecord(workspaceId, input);
  }

  async archiveWorkspace(workspaceId: string): Promise<void> {
    await mockLatency(120);
    archiveWorkspaceRecord(workspaceId);
  }

  async deleteWorkspace(workspaceId: string): Promise<void> {
    await mockLatency(120);
    archiveWorkspaceRecord(workspaceId);
  }

  async getMyMembership(
    workspaceId: string,
  ): Promise<WorkspaceMembership | null> {
    await mockLatency(60);
    return getMembershipForCurrentUser(workspaceId);
  }

  async getHealth(workspaceId: string) {
    await mockLatency(80);
    getActiveWorkspace(workspaceId);
    return mockHealth;
  }

  async getInsightsOverview(workspaceId: string) {
    await mockLatency(80);
    getActiveWorkspace(workspaceId);
    return mockInsightsOverview;
  }

  async getTeam(workspaceId: string) {
    await mockLatency(80);
    return getTeamForWorkspace(workspaceId);
  }

  async getOrganizationalIntelligence(workspaceId: string) {
    await mockLatency(80);
    getActiveWorkspace(workspaceId);
    return mockOrgIntelligence;
  }

  async getRecentActivity(workspaceId: string, limit = 20) {
    await mockLatency(80);
    getActiveWorkspace(workspaceId);
    return mockActivity.slice(0, limit);
  }

  async getContinueWorking(workspaceId: string) {
    await mockLatency(80);
    getActiveWorkspace(workspaceId);
    return mockContinueWorking;
  }
}

export class HttpWorkspaceService implements WorkspaceService {
  async listWorkspaces(auth?: ServiceAuth) {
    return apiRequest<Project[]>('/api/v1/workspaces', {
      token: auth?.accessToken,
    });
  }

  async getWorkspace(workspaceId: string, auth?: ServiceAuth) {
    return apiRequest<Project>(`/api/v1/workspaces/${workspaceId}`, {
      token: auth?.accessToken,
    });
  }

  async createWorkspace(input: CreateWorkspaceInput, auth?: ServiceAuth) {
    return apiRequest<Project>('/api/v1/workspaces', {
      method: 'POST',
      body: input,
      token: auth?.accessToken,
    });
  }

  async updateWorkspace(
    workspaceId: string,
    input: UpdateWorkspaceInput,
    auth?: ServiceAuth,
  ) {
    return apiRequest<Project>(`/api/v1/workspaces/${workspaceId}`, {
      method: 'PATCH',
      body: input,
      token: auth?.accessToken,
    });
  }

  async archiveWorkspace(workspaceId: string, auth?: ServiceAuth) {
    await apiRequest<void>(`/api/v1/workspaces/${workspaceId}/archive`, {
      method: 'POST',
      token: auth?.accessToken,
    });
  }

  async deleteWorkspace(workspaceId: string, auth?: ServiceAuth) {
    await apiRequest<void>(`/api/v1/workspaces/${workspaceId}`, {
      method: 'DELETE',
      token: auth?.accessToken,
    });
  }

  async getMyMembership(workspaceId: string, auth?: ServiceAuth) {
    return apiRequest<WorkspaceMembership | null>(
      `/api/v1/workspaces/${workspaceId}/memberships/me`,
      { token: auth?.accessToken },
    );
  }

  async getHealth(workspaceId: string, auth?: ServiceAuth) {
    return apiRequest<WorkspaceHealthSummary>(
      `/api/v1/workspaces/${workspaceId}/health`,
      { token: auth?.accessToken },
    );
  }

  async getInsightsOverview(workspaceId: string, auth?: ServiceAuth) {
    return apiRequest<WorkspaceInsightsOverview>(
      `/api/v1/workspaces/${workspaceId}/insights/overview`,
      { token: auth?.accessToken },
    );
  }

  async getTeam(workspaceId: string, auth?: ServiceAuth) {
    return apiRequest<TeamMember[]>(`/api/v1/workspaces/${workspaceId}/team`, {
      token: auth?.accessToken,
    });
  }

  async getOrganizationalIntelligence(workspaceId: string, auth?: ServiceAuth) {
    return apiRequest<OrgIntelligenceSignal[]>(
      `/api/v1/workspaces/${workspaceId}/organizational-intelligence`,
      { token: auth?.accessToken },
    );
  }

  async getRecentActivity(
    workspaceId: string,
    limit = 20,
    auth?: ServiceAuth,
  ) {
    return apiRequest<ActivityLog[]>(
      `/api/v1/workspaces/${workspaceId}/activity?limit=${limit}`,
      { token: auth?.accessToken },
    );
  }

  async getContinueWorking(workspaceId: string, auth?: ServiceAuth) {
    return apiRequest<ContinueWorkingItem[]>(
      `/api/v1/workspaces/${workspaceId}/continue-working`,
      { token: auth?.accessToken },
    );
  }
}
