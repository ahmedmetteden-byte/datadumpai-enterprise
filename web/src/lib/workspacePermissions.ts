import type {
  WorkspaceCapabilities,
  WorkspaceRole,
} from '@/types/workspace';

const ROLE_LABELS: Record<WorkspaceRole, string> = {
  owner: 'Owner',
  admin: 'Admin',
  editor: 'Editor',
  reviewer: 'Reviewer',
  viewer: 'Viewer',
};

/** Fail-closed empty capabilities while loading or on error. */
export const EMPTY_CAPABILITIES: WorkspaceCapabilities = {
  canView: false,
  canEditSettings: false,
  canManageTeam: false,
  canUpload: false,
  canGenerateReports: false,
  canPublish: false,
  canArchive: false,
};

export function capabilitiesForRole(
  role: WorkspaceRole | null | undefined,
): WorkspaceCapabilities {
  if (!role) {
    return EMPTY_CAPABILITIES;
  }

  switch (role) {
    case 'owner':
      return {
        canView: true,
        canEditSettings: true,
        canManageTeam: true,
        canUpload: true,
        canGenerateReports: true,
        canPublish: true,
        canArchive: true,
      };
    case 'admin':
      return {
        canView: true,
        canEditSettings: true,
        canManageTeam: true,
        canUpload: true,
        canGenerateReports: true,
        canPublish: true,
        canArchive: false,
      };
    case 'editor':
      return {
        canView: true,
        canEditSettings: false,
        canManageTeam: false,
        canUpload: true,
        canGenerateReports: true,
        canPublish: true,
        canArchive: false,
      };
    case 'reviewer':
      return {
        canView: true,
        canEditSettings: false,
        canManageTeam: false,
        canUpload: false,
        canGenerateReports: false,
        canPublish: false,
        canArchive: false,
      };
    case 'viewer':
      return {
        canView: true,
        canEditSettings: false,
        canManageTeam: false,
        canUpload: false,
        canGenerateReports: false,
        canPublish: false,
        canArchive: false,
      };
    default:
      return EMPTY_CAPABILITIES;
  }
}

export function labelForRole(role: WorkspaceRole): string {
  return ROLE_LABELS[role];
}

export const ACTIVE_WORKSPACE_STORAGE_KEY = 'dde.activeWorkspaceId';

export function formatStorageBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
