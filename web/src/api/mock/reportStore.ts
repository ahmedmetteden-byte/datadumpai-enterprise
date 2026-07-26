/**
 * In-memory reports store for MockReportService.
 */

import type {
  GenerateReportInput,
  ReportDetail,
  ReportExportFormat,
  ReportPeriod,
  ReportStatus,
  ReportTemplate,
} from '@/types/reports';
import { ApiError } from '@/api/client';

const TEMPLATES: ReportTemplate[] = [
  {
    id: 'executive_summary',
    name: 'Executive Summary',
    description: 'Concise leadership brief with key findings and actions.',
  },
  {
    id: 'board_report',
    name: 'Board Report',
    description: 'Board-ready narrative with risks, KPIs, and recommendations.',
  },
  {
    id: 'management_report',
    name: 'Management Report',
    description: 'Operating review covering performance, issues, and next steps.',
  },
  {
    id: 'financial_analysis',
    name: 'Financial Analysis',
    description: 'Margin, revenue, and variance analysis from workspace evidence.',
  },
  {
    id: 'risk_assessment',
    name: 'Risk Assessment Report',
    description: 'Risk register style summary with mitigations.',
  },
  {
    id: 'full_report',
    name: 'Full Report',
    description: 'Comprehensive multi-section report across the corpus.',
  },
];

const PERIODS: ReportPeriod[] = [
  { id: 'weekly', name: 'Weekly Report' },
  { id: 'monthly', name: 'Monthly Report' },
  { id: 'quarterly', name: 'Quarterly Report' },
  { id: 'annual', name: 'Annual Report' },
  { id: 'custom', name: 'Custom / Ad hoc' },
];

const store = new Map<string, ReportDetail[]>();

function nowIso() {
  return new Date().toISOString();
}

function seed(workspaceId: string): ReportDetail[] {
  if (store.has(workspaceId)) return store.get(workspaceId)!;
  const seeded: ReportDetail[] = [];
  store.set(workspaceId, seeded);
  return seeded;
}

export function mockReportTemplates(): ReportTemplate[] {
  return TEMPLATES.map((item) => ({ ...item }));
}

export function mockReportPeriods(): ReportPeriod[] {
  return PERIODS.map((item) => ({ ...item }));
}

export function mockListReports(workspaceId: string): ReportDetail[] {
  return seed(workspaceId).map((item) => ({ ...item }));
}

export function mockGetReport(
  workspaceId: string,
  reportId: string,
): ReportDetail {
  const match = seed(workspaceId).find((item) => item.id === reportId);
  if (!match) {
    throw new ApiError('Report not found', 404, { detail: 'Report not found' });
  }
  return { ...match };
}

export function mockGenerateReport(
  workspaceId: string,
  input: GenerateReportInput,
): ReportDetail {
  const template =
    TEMPLATES.find((item) => item.id === input.templateId) ?? TEMPLATES[0]!;
  const period =
    PERIODS.find((item) => item.id === input.periodId) ?? PERIODS[2]!;
  const name =
    input.title?.trim() || `${template.name} — ${period.name}`;
  const content = `# ${name}

**Template:** ${template.name}  
**Period:** ${period.name}

## Executive Summary

Generated from the active workspace library for ${period.name.toLowerCase()}.

## Key Findings

- Margin and retention themes remain the strongest signals in indexed sources.
- Open actions from recent meetings should be confirmed before board circulation.

## Recommendations

1. Validate findings with owners.
2. Export Word, PDF, or PowerPoint for distribution.
`;
  const created: ReportDetail = {
    id: `rpt_${Date.now().toString(36)}`,
    filename: `${name.toLowerCase().replace(/\s+/g, '-')}.md`,
    name,
    path: `/reports/${name.toLowerCase().replace(/\s+/g, '-')}.md`,
    size: content.length,
    createdAt: nowIso(),
    updatedAt: nowIso(),
    reportType: template.name,
    templateId: template.id,
    periodId: period.id,
    periodName: period.name,
    status: 'draft',
    content,
    sourceDocuments: ['Library corpus'],
  };
  const list = seed(workspaceId);
  list.unshift(created);
  store.set(workspaceId, list);
  return { ...created };
}

export function mockSaveReport(
  workspaceId: string,
  reportId: string,
  status: ReportStatus = 'ready',
): ReportDetail {
  const list = seed(workspaceId);
  const match = list.find((item) => item.id === reportId);
  if (!match) {
    throw new ApiError('Report not found', 404, { detail: 'Report not found' });
  }
  match.status = status;
  match.updatedAt = nowIso();
  return { ...match };
}

export function mockExportReport(
  workspaceId: string,
  reportId: string,
  format: ReportExportFormat,
): Blob {
  const report = mockGetReport(workspaceId, reportId);
  const body = `${report.name}\n\n${report.content ?? ''}\n\nExported as ${format.toUpperCase()}`;
  const type =
    format === 'pdf'
      ? 'application/pdf'
      : format === 'pptx'
        ? 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
        : 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
  return new Blob([body], { type });
}
