import type { HealthStatus, IsoDateTime } from './api';

export type WorkspaceRole =
  | 'owner'
  | 'admin'
  | 'editor'
  | 'reviewer'
  | 'viewer';

export interface CreateWorkspaceInput {
  name: string;
  description?: string;
}

export interface UpdateWorkspaceInput {
  name?: string;
  description?: string;
}

export interface WorkspaceCapabilities {
  canView: boolean;
  canEditSettings: boolean;
  canManageTeam: boolean;
  canUpload: boolean;
  canGenerateReports: boolean;
  canPublish: boolean;
  canArchive: boolean;
}

export interface WorkspaceMembership {
  userId: string;
  workspaceId: string;
  role: WorkspaceRole;
}

export type WorkspaceSectionId =
  | 'overview'
  | 'health'
  | 'team'
  | 'activity'
  | 'settings';

export interface WorkspaceDetailBundle {
  workspace: import('./api').Project;
  health: import('./home').WorkspaceHealthSummary;
  insightsOverview: import('./home').WorkspaceInsightsOverview;
  team: import('./home').TeamMember[];
  activity: import('./api').ActivityLog[];
  continueWorking: import('./home').ContinueWorkingItem[];
  membership: WorkspaceMembership | null;
}

export type { HealthStatus, IsoDateTime };
