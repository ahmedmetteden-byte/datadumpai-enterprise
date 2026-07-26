/**
 * Mutable in-memory workspace store for MockWorkspaceService.
 * Starts empty — workspaces are created through the UI.
 */

import type { Project } from '@/types/api';
import type { TeamMember } from '@/types/home';
import type {
  CreateWorkspaceInput,
  UpdateWorkspaceInput,
  WorkspaceMembership,
} from '@/types/workspace';
import { ApiError } from '@/api/client';
import { mockUser, mockWorkspaces as seedWorkspaces } from '@/api/mock/data';

let workspaces: Project[] = seedWorkspaces.map((item) => ({ ...item }));
let archivedIds = new Set<string>();

function ownerTeam(): TeamMember[] {
  return [
    {
      id: mockUser.id,
      name: mockUser.fullName,
      role: 'owner',
      title: 'Owner',
      status: 'online',
    },
  ];
}

/** Per-workspace team overrides; defaults to owner only */
const teamByWorkspace = new Map<string, TeamMember[]>();

export function listActiveWorkspaces(): Project[] {
  return workspaces
    .filter((workspace) => !archivedIds.has(workspace.id))
    .map((workspace) => ({ ...workspace }));
}

export function getActiveWorkspace(workspaceId: string): Project {
  const match = workspaces.find(
    (workspace) =>
      workspace.id === workspaceId && !archivedIds.has(workspace.id),
  );
  if (!match) {
    throw new ApiError('Workspace not found or access denied', 404, {
      detail: 'Workspace not found or access denied',
      code: 'workspace_forbidden',
    });
  }
  return { ...match };
}

export function createWorkspaceRecord(input: CreateWorkspaceInput): Project {
  const now = new Date().toISOString();
  const workspace: Project = {
    id: `ws_${Date.now().toString(36)}`,
    ownerId: mockUser.id,
    name: input.name.trim(),
    description: input.description?.trim() ?? '',
    createdAt: now,
    updatedAt: now,
    lastActivity: now,
    storageUsed: 0,
  };
  workspaces = [workspace, ...workspaces];
  teamByWorkspace.set(workspace.id, ownerTeam());
  return { ...workspace };
}

export function updateWorkspaceRecord(
  workspaceId: string,
  input: UpdateWorkspaceInput,
): Project {
  const current = getActiveWorkspace(workspaceId);
  const updated: Project = {
    ...current,
    name: input.name?.trim() ?? current.name,
    description:
      input.description !== undefined
        ? input.description.trim()
        : current.description,
    updatedAt: new Date().toISOString(),
  };
  workspaces = workspaces.map((item) =>
    item.id === workspaceId ? updated : item,
  );
  return { ...updated };
}

export function archiveWorkspaceRecord(workspaceId: string): void {
  getActiveWorkspace(workspaceId);
  archivedIds.add(workspaceId);
}

export function getTeamForWorkspace(workspaceId: string): TeamMember[] {
  getActiveWorkspace(workspaceId);
  const team = teamByWorkspace.get(workspaceId) ?? ownerTeam();
  return team.map((member) => ({ ...member }));
}

export function getMembershipForCurrentUser(
  workspaceId: string,
): WorkspaceMembership | null {
  const team = getTeamForWorkspace(workspaceId);
  const self = team.find((member) => member.id === mockUser.id);
  if (!self) {
    return null;
  }
  return {
    userId: mockUser.id,
    workspaceId,
    role: self.role,
  };
}

export function resolveDefaultWorkspaceId(
  preferred?: string | null,
): string | null {
  const active = listActiveWorkspaces();
  if (preferred && active.some((item) => item.id === preferred)) {
    return preferred;
  }
  return active[0]?.id ?? null;
}
