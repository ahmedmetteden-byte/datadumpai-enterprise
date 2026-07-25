import type { WorkspaceSectionId } from '@/types/workspace';

export const WORKSPACE_ROUTES = {
  list: '/workspaces',
  root: (workspaceId: string) => `/workspaces/${workspaceId}`,
  section: (workspaceId: string, section: WorkspaceSectionId) =>
    `/workspaces/${workspaceId}/${section}`,
} as const;

export const WORKSPACE_SECTIONS: Array<{
  id: WorkspaceSectionId;
  label: string;
}> = [
  { id: 'overview', label: 'Overview' },
  { id: 'health', label: 'Health' },
  { id: 'activity', label: 'Timeline' },
  { id: 'team', label: 'Team' },
  { id: 'settings', label: 'Settings' },
];
