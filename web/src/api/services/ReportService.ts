import { apiRequest } from '@/api/client';
import { mockLatency, type ServiceAuth } from '@/api/config';
import type { ReportService } from '@/api/services/contracts';
import { mockQuickActions, mockReports } from '@/api/mock/data';
import type { ReportSummary } from '@/types/api';
import type { QuickAction } from '@/types/home';

export class MockReportService implements ReportService {
  async listReports(workspaceId: string) {
    await mockLatency(80);
    void workspaceId;
    return mockReports;
  }

  async listAwaitingReview(workspaceId: string) {
    await mockLatency(80);
    void workspaceId;
    return mockReports.filter((report) => report.status === 'awaiting_review');
  }

  async getQuickActions(workspaceId: string) {
    await mockLatency(60);
    void workspaceId;
    return mockQuickActions;
  }
}

export class HttpReportService implements ReportService {
  async listReports(workspaceId: string, auth?: ServiceAuth) {
    return apiRequest<ReportSummary[]>(
      `/api/v1/workspaces/${workspaceId}/reports`,
      { token: auth?.accessToken },
    );
  }

  async listAwaitingReview(workspaceId: string, auth?: ServiceAuth) {
    return apiRequest<ReportSummary[]>(
      `/api/v1/workspaces/${workspaceId}/reports?status=awaiting_review`,
      { token: auth?.accessToken },
    );
  }

  async getQuickActions(workspaceId: string, auth?: ServiceAuth) {
    return apiRequest<QuickAction[]>(
      `/api/v1/workspaces/${workspaceId}/quick-actions`,
      { token: auth?.accessToken },
    );
  }
}
