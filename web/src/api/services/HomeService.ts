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
import { mockListConversations } from '@/api/mock/intelligenceStore';
import { mockListKnowledge } from '@/api/mock/knowledgeStore';
import { mockListReports } from '@/api/mock/reportStore';
import {
  getActiveWorkspace,
  listActiveWorkspaces,
} from '@/api/mock/workspaceStore';
import type {
  DashboardMetric,
  DashboardRecentItem,
  HomeDashboard,
  HomePageData,
} from '@/types/home';
import type { NotificationItem, User } from '@/types/api';

function buildMockDashboard(workspaceIds: string[]): HomeDashboard {
  const uploads: DashboardRecentItem[] = [];
  const reports: DashboardRecentItem[] = [];
  const conversations: DashboardRecentItem[] = [];
  let documentCount = 0;
  let indexedCount = 0;
  let reportCount = 0;

  for (const workspaceId of workspaceIds) {
    const knowledge = mockListKnowledge(workspaceId, { limit: 200 });
    documentCount += knowledge.total;
    for (const item of knowledge.items) {
      if (
        item.status === 'indexed' ||
        item.status === 'verified' ||
        item.status === 'linked'
      ) {
        indexedCount += 1;
      }
      uploads.push({
        id: item.id,
        title: item.filename || item.title,
        subtitle: item.status,
        href: `/knowledge/${item.id}`,
        kind: 'document',
        at: item.createdAt,
        meta: item.status,
      });
    }

    const reportList = mockListReports(workspaceId);
    reportCount += reportList.length;
    for (const report of reportList) {
      reports.push({
        id: report.id,
        title: report.name,
        subtitle: report.periodName || report.reportType || 'Report',
        href: `/reports/${report.id}`,
        kind: 'report',
        at: report.updatedAt || report.createdAt,
        meta: report.status,
      });
    }

    for (const conversation of mockListConversations(workspaceId)) {
      conversations.push({
        id: conversation.id,
        title: conversation.title,
        subtitle: conversation.preview,
        href: '/copilot',
        kind: 'conversation',
        at: conversation.updatedAt,
        meta: workspaceId,
      });
    }
  }

  const indexedPercent =
    documentCount === 0
      ? 100
      : Math.round((indexedCount / documentCount) * 100);

  const metrics: DashboardMetric[] = [
    {
      id: 'workspaces',
      label: 'Workspaces',
      value: workspaceIds.length,
    },
    { id: 'documents', label: 'Documents', value: documentCount },
    { id: 'reports', label: 'Reports', value: reportCount },
    {
      id: 'indexed',
      label: 'Indexed',
      value: indexedPercent,
      unit: 'percent',
    },
  ];

  const byDateDesc = (a: DashboardRecentItem, b: DashboardRecentItem) =>
    b.at.localeCompare(a.at);

  return {
    metrics,
    recentUploads: uploads.sort(byDateDesc).slice(0, 6),
    recentReports: reports.sort(byDateDesc).slice(0, 6),
    recentConversations: conversations.sort(byDateDesc).slice(0, 6),
  };
}

/**
 * Home is a composition facade.
 * Mock mode assembles domain services; HTTP mode prefers GET /api/v1/home.
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
    const workspaces = await this.workspace.listWorkspaces();
    const dashboard = buildMockDashboard(workspaces.map((item) => item.id));

    const [
      greeting,
      notifications,
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

    const indexedMetric = dashboard.metrics.find((m) => m.id === 'indexed');
    const docsMetric = dashboard.metrics.find((m) => m.id === 'documents');

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
      insightsOverview: {
        ...insightsOverview,
        healthPercent: indexedMetric?.value ?? insightsOverview.healthPercent,
        newInsightCount: dashboard.recentConversations.length,
      },
      dashboard,
      reportsAwaitingReview: awaitingReview,
      insights: {
        brief: {
          ...brief,
          items: [
            {
              id: 'b_live',
              headline: `${docsMetric?.value ?? 0} documents across ${workspaces.length} workspaces`,
              detail: `${indexedMetric?.value ?? 0}% indexed and ready for Intelligence Studio.`,
              priority: 'high',
              href: '/knowledge',
            },
            ...brief.items.slice(0, 2),
          ],
        },
        recommendations,
        recentActivity,
        health: {
          ...health,
          overallPercent: indexedMetric?.value ?? health.overallPercent,
        },
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
