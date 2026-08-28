import { apiRequest } from '@/api/client';
import { mockLatency, type ServiceAuth } from '@/api/config';
import type { ReportService } from '@/api/services/contracts';
import { mockQuickActions, mockReports } from '@/api/mock/data';
import {
  mockExportReport,
  mockGenerateReport,
  mockGetReport,
  mockListReports,
  mockReportPeriods,
  mockReportTemplates,
  mockSaveReport,
} from '@/api/mock/reportStore';
import type { ReportSummary } from '@/types/api';
import type { QuickAction } from '@/types/home';
import type {
  GenerateReportInput,
  ReportDetail,
  ReportExportFormat,
  ReportPeriod,
  ReportStatus,
  ReportTemplate,
} from '@/types/reports';

function toSummary(report: ReportDetail): ReportSummary {
  return {
    filename: report.filename,
    name: report.name,
    path: report.path,
    size: report.size,
    createdAt: report.createdAt,
    reportType: report.reportType ?? undefined,
    status: report.status,
  };
}

export class MockReportService implements ReportService {
  async listReports(workspaceId: string) {
    await mockLatency(80);
    return mockListReports(workspaceId).map(toSummary);
  }

  async listAwaitingReview(workspaceId: string) {
    await mockLatency(80);
    return mockListReports(workspaceId)
      .filter((report) => report.status === 'awaiting_review')
      .map(toSummary);
  }

  async getQuickActions(workspaceId: string) {
    await mockLatency(60);
    void workspaceId;
    return mockQuickActions;
  }

  async listTemplates(workspaceId: string) {
    await mockLatency(40);
    void workspaceId;
    return mockReportTemplates();
  }

  async listPeriods(workspaceId: string) {
    await mockLatency(40);
    void workspaceId;
    return mockReportPeriods();
  }

  async listReportDetails(workspaceId: string) {
    await mockLatency(80);
    return mockListReports(workspaceId);
  }

  async getReport(workspaceId: string, reportId: string) {
    await mockLatency(60);
    return mockGetReport(workspaceId, reportId);
  }

  async generate(workspaceId: string, input: GenerateReportInput) {
    await mockLatency(900);
    return mockGenerateReport(workspaceId, input);
  }

  async save(
    workspaceId: string,
    reportId: string,
    status: ReportStatus = 'ready',
  ) {
    await mockLatency(80);
    return mockSaveReport(workspaceId, reportId, status);
  }

  async export(
    workspaceId: string,
    reportId: string,
    format: ReportExportFormat,
  ) {
    await mockLatency(200);
    return mockExportReport(workspaceId, reportId, format);
  }
}

export class HttpReportService implements ReportService {
  async listReports(workspaceId: string, auth?: ServiceAuth) {
    const details = await apiRequest<ReportDetail[]>(
      `/api/v1/workspaces/${workspaceId}/reports`,
      { token: auth?.accessToken },
    );
    return details.map(toSummary);
  }

  async listAwaitingReview(workspaceId: string, auth?: ServiceAuth) {
    const details = await apiRequest<ReportDetail[]>(
      `/api/v1/workspaces/${workspaceId}/reports?status=awaiting_review`,
      { token: auth?.accessToken },
    );
    return details.map(toSummary);
  }

  async getQuickActions(workspaceId: string, auth?: ServiceAuth) {
    return apiRequest<QuickAction[]>(
      `/api/v1/workspaces/${workspaceId}/quick-actions`,
      { token: auth?.accessToken },
    );
  }

  async listTemplates(workspaceId: string, auth?: ServiceAuth) {
    return apiRequest<ReportTemplate[]>(
      `/api/v1/workspaces/${workspaceId}/report-templates`,
      { token: auth?.accessToken },
    );
  }

  async listPeriods(workspaceId: string, auth?: ServiceAuth) {
    return apiRequest<ReportPeriod[]>(
      `/api/v1/workspaces/${workspaceId}/report-periods`,
      { token: auth?.accessToken },
    );
  }

  async listReportDetails(workspaceId: string, auth?: ServiceAuth) {
    return apiRequest<ReportDetail[]>(
      `/api/v1/workspaces/${workspaceId}/reports`,
      { token: auth?.accessToken },
    );
  }

  async getReport(workspaceId: string, reportId: string, auth?: ServiceAuth) {
    return apiRequest<ReportDetail>(
      `/api/v1/workspaces/${workspaceId}/reports/${reportId}`,
      { token: auth?.accessToken },
    );
  }

  async generate(
    workspaceId: string,
    input: GenerateReportInput,
    auth?: ServiceAuth,
  ) {
    return apiRequest<ReportDetail>(
      `/api/v1/workspaces/${workspaceId}/reports/generate`,
      {
        method: 'POST',
        body: input,
        token: auth?.accessToken,
      },
    );
  }

  async save(
    workspaceId: string,
    reportId: string,
    status: ReportStatus = 'ready',
    auth?: ServiceAuth,
  ) {
    return apiRequest<ReportDetail>(
      `/api/v1/workspaces/${workspaceId}/reports/${reportId}/save`,
      {
        method: 'POST',
        body: { status },
        token: auth?.accessToken,
      },
    );
  }

  async export(
    workspaceId: string,
    reportId: string,
    format: ReportExportFormat,
    auth?: ServiceAuth,
    preparedBy?: string,
  ) {
    const base = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(
      /\/$/,
      '',
    ) ?? '';
    const preparedByParam = preparedBy?.trim()
      ? `&prepared_by=${encodeURIComponent(preparedBy.trim())}`
      : '';
    const response = await fetch(
      `${base}/api/v1/workspaces/${workspaceId}/reports/${reportId}/export?format=${format}${preparedByParam}`,
      {
        headers: auth?.accessToken
          ? { Authorization: `Bearer ${auth.accessToken}` }
          : undefined,
      },
    );
    if (!response.ok) {
      const raw = await response.text();
      let detail = raw;
      try {
        const parsed = JSON.parse(raw) as { detail?: unknown };
        if (typeof parsed.detail === 'string' && parsed.detail.trim()) {
          detail = parsed.detail;
        }
      } catch {
        /* not JSON — fall back to raw text below */
      }
      throw new Error(detail || `Export failed (${response.status})`);
    }
    return response.blob();
  }
}

// Keep mockReports import used for any legacy callers via re-export shape
void mockReports;
