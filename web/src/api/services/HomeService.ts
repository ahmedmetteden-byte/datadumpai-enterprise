import { apiRequest } from '@/api/client';
import { mockLatency, type ServiceAuth } from '@/api/config';
import type {
  AIService,
  HomeService,
  KnowledgeService,
  ReportService,
  WorkspaceService,
} from '@/api/services/contracts';
import {
  mockGreeting,
  mockNotifications,
  mockUser,
} from '@/api/mock/data';
import { getActiveWorkspace, listActiveWorkspaces } from '@/api/mock/workspaceStore';
import type { HomePageData } from '@/types/home';
import type { NotificationItem, User } from '@/types/api';

/**
 * Home is a composition facade.
 * Mock mode assembles domain services; HTTP mode prefers GET /api/v1/home
 * (BFF) so the backend can optimize the aggregate in one round-trip.
 */
export class MockHomeService implements HomeService {
  private readonly workspace: WorkspaceService;
  private readonly knowledge: KnowledgeService;
  private readonly report: ReportService;
  private readonly ai: AIService;

  constructor(
    workspace: WorkspaceService,
    knowledge: KnowledgeService,
    report: ReportService,
    ai: AIService,
  ) {
    this.workspace = workspace;
    this.knowledge = knowledge;
    this.report = report;
    this.ai = ai;
  }

  async getGreeting(): Promise<{ greeting: string; user: User }> {
    await mockLatency(60);
    return { greeting: mockGreeting, user: mockUser };
  }

  async listNotifications(): Promise<{
    items: NotificationItem[];
    unreadCount: number;
  }> {
    await mockLatency(60);
    return {
      items: mockNotifications,
      unreadCount: mockNotifications.filter((item) => !item.read).length,
    };
  }

  async getHome(workspaceId?: string): Promise<HomePageData> {
    const active = workspaceId
      ? getActiveWorkspace(workspaceId)
      : (listActiveWorkspaces()[0] ?? null);
    if (!active) {
      throw new Error('No workspaces available');
    }
    const id = active.id;

    const [
      greeting,
      notifications,
      workspaces,
      search,
      quickActions,
      continueWorking,
      insightsOverview,
      awaitingReview,
      brief,
      recommendations,
      recentActivity,
      health,
      team,
      organizationalIntelligence,
      items,
    ] = await Promise.all([
      this.getGreeting(),
      this.listNotifications(),
      this.workspace.listWorkspaces(),
      this.knowledge.getSearchSuggestions(id),
      this.report.getQuickActions(id),
      this.workspace.getContinueWorking(id),
      this.workspace.getInsightsOverview(id),
      this.report.listAwaitingReview(id),
      this.ai.getTodaysBrief(id),
      this.ai.getRecommendations(id),
      this.workspace.getRecentActivity(id),
      this.workspace.getHealth(id),
      this.workspace.getTeam(id),
      this.workspace.getOrganizationalIntelligence(id),
      this.ai.listInsights(id),
    ]);

    return {
      user: greeting.user,
      greeting: greeting.greeting,
      activeWorkspace: active,
      workspaces,
      notifications: notifications.items,
      unreadNotificationCount: notifications.unreadCount,
      search,
      quickActions,
      continueWorking,
      insightsOverview,
      reportsAwaitingReview: awaitingReview,
      insights: {
        brief,
        recommendations,
        recentActivity,
        health,
        team,
        organizationalIntelligence,
        items,
      },
    };
  }
}

export class HttpHomeService implements HomeService {
  async getHome(workspaceId?: string, auth?: ServiceAuth) {
    const query = workspaceId
      ? `?workspace_id=${encodeURIComponent(workspaceId)}`
      : '';
    return apiRequest<HomePageData>(`/api/v1/home${query}`, {
      token: auth?.accessToken,
    });
  }

  async getGreeting(auth?: ServiceAuth) {
    return apiRequest<{ greeting: string; user: User }>('/api/v1/home/greeting', {
      token: auth?.accessToken,
    });
  }

  async listNotifications(auth?: ServiceAuth) {
    return apiRequest<{ items: NotificationItem[]; unreadCount: number }>(
      '/api/v1/notifications',
      { token: auth?.accessToken },
    );
  }
}
