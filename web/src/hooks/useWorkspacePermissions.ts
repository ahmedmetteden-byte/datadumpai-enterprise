import { useMemo } from 'react';
import {
  capabilitiesForRole,
  EMPTY_CAPABILITIES,
} from '@/lib/workspacePermissions';
import type { WorkspaceCapabilities, WorkspaceRole } from '@/types/workspace';

interface PermissionsState {
  role: WorkspaceRole | null;
  capabilities: WorkspaceCapabilities;
  loading: boolean;
}

/**
 * Maps membership role → capability flags.
 * Fail-closed: loading or missing role ⇒ no elevated capabilities.
 */
export function useWorkspacePermissions(
  role: WorkspaceRole | null | undefined,
  loading: boolean,
): PermissionsState {
  return useMemo(() => {
    if (loading) {
      return { role: null, capabilities: EMPTY_CAPABILITIES, loading: true };
    }
    const resolved = role ?? null;
    return {
      role: resolved,
      capabilities: capabilitiesForRole(resolved),
      loading: false,
    };
  }, [role, loading]);
}
