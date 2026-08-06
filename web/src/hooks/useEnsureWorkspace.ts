import { useEffect, useRef, useState } from 'react';
import { services } from '@/api/services';
import { useAuth } from '@/context/AuthContext';
import { useWorkspace } from '@/context/WorkspaceContext';

interface EnsureWorkspaceState {
  ready: boolean;
  workspaceId: string | null;
  error: string | null;
}

/** Auto-assigned name given to a silently-created workspace. */
export const DEFAULT_WORKSPACE_NAME = 'My Workspace';

/**
 * Guarantees the user has an active workspace before the Home composer
 * becomes interactive — silently creates one on first use so uploading
 * a document never requires a manual "create workspace" step first.
 */
export function useEnsureWorkspace(): EnsureWorkspaceState {
  const { accessToken } = useAuth();
  const { activeWorkspaceId, setActiveWorkspaceId, bumpRevision } =
    useWorkspace();
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const attempted = useRef(false);

  useEffect(() => {
    let cancelled = false;

    async function ensure() {
      if (attempted.current) return;
      attempted.current = true;
      const auth = { accessToken };
      try {
        const workspaces = await services.workspace.listWorkspaces(auth);
        if (cancelled) return;

        if (workspaces.length > 0) {
          const activeStillExists =
            !!activeWorkspaceId &&
            workspaces.some((workspace) => workspace.id === activeWorkspaceId);
          if (!activeStillExists) {
            setActiveWorkspaceId(workspaces[0].id);
          }
          setReady(true);
          return;
        }

        const created = await services.workspace.createWorkspace(
          { name: DEFAULT_WORKSPACE_NAME },
          auth,
        );
        if (cancelled) return;
        setActiveWorkspaceId(created.id);
        bumpRevision();
        setReady(true);
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error
              ? err.message
              : 'Could not prepare your workspace.',
          );
        }
      }
    }

    void ensure();
    return () => {
      cancelled = true;
    };
  }, [accessToken, activeWorkspaceId, setActiveWorkspaceId, bumpRevision]);

  return { ready, workspaceId: activeWorkspaceId, error };
}
