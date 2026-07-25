/**
 * Shared API contracts for the enterprise frontend.
 * Shapes mirror domain models in `models/*.py` and repository dicts
 * so future FastAPI responses can drop in with minimal UI changes.
 */

export type HealthStatus = 'ready' | 'warning' | 'critical';

export type IsoDateTime = string;

export interface ApiErrorBody {
  detail: string;
  code?: string;
}

export interface Paginated<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface User {
  id: string;
  email: string;
  fullName: string;
  emailVerified: boolean;
}

export interface Project {
  id: string;
  ownerId: string;
  name: string;
  description: string;
  createdAt: IsoDateTime;
  updatedAt: IsoDateTime;
  lastActivity: IsoDateTime;
  storageUsed: number;
}

export interface DocumentSummary {
  filename: string;
  size: number;
  uploadedAt: IsoDateTime;
  path: string;
}

export interface ReportSummary {
  filename: string;
  name: string;
  path: string;
  size: number;
  createdAt: IsoDateTime;
  reportType?: string;
  status?: 'draft' | 'ready' | 'awaiting_review' | 'archived';
}

export interface WorkspaceHealthIndicator {
  status: HealthStatus;
  icon: string;
  message: string;
}

export interface WorkspaceAI {
  ready: boolean;
  documentCount: number;
  reportCount: number;
  status: string;
}

export interface WorkspaceAnalytics {
  documentCount: number;
  reportCount: number;
  exportCount: number;
  storageUsed: number;
  lastActivity: IsoDateTime;
  createdAt: IsoDateTime;
  updatedAt: IsoDateTime;
}

export interface ActivityLog {
  id: string;
  userId: string;
  action: string;
  message: string;
  metadata: Record<string, unknown>;
  createdAt: IsoDateTime;
}

export interface NotificationItem {
  id: string;
  message: string;
  level: 'info' | 'success' | 'warning' | 'error';
  createdAt: IsoDateTime;
  read: boolean;
}
