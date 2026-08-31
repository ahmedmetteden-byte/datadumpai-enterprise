import type { IsoDateTime } from './api';

export type ReportStatus = 'draft' | 'ready' | 'awaiting_review' | 'archived';

export type ReportExportFormat = 'docx' | 'pdf' | 'pptx';

export interface ReportTemplate {
  id: string;
  name: string;
  description: string;
  locked?: boolean;
  requiredPlan?: string | null;
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
  instructions?: string | null;
  /** Export formats the account's current plan doesn't include, mapped to
   * the cheapest plan label that unlocks each one (e.g. {docx: "Starter"}). */
  lockedExportFormats?: Record<string, string>;
}

export interface GenerateReportInput {
  templateId: string;
  periodId: string;
  title?: string;
  instructions?: string;
  /** Scope the report to exactly these document ids instead of every
   * document in the workspace. Omitted or empty means "use all documents". */
  documentIds?: string[];
}
