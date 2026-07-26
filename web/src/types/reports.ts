import type { IsoDateTime } from './api';

export type ReportStatus = 'draft' | 'ready' | 'awaiting_review' | 'archived';

export type ReportExportFormat = 'docx' | 'pdf' | 'pptx';

export interface ReportTemplate {
  id: string;
  name: string;
  description: string;
}

export interface ReportPeriod {
  id: string;
  name: string;
}

export interface ReportDetail {
  id: string;
  filename: string;
  name: string;
  path: string;
  size: number;
  createdAt: IsoDateTime;
  updatedAt?: IsoDateTime | null;
  reportType?: string | null;
  templateId?: string | null;
  periodId?: string | null;
  periodName?: string | null;
  status: ReportStatus;
  content?: string | null;
  sourceDocuments?: string[];
}

export interface GenerateReportInput {
  templateId: string;
  periodId: string;
  title?: string;
}
