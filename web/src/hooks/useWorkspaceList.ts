import { useEffect, useState } from 'react';
import { services } from '@/api/services';
import { useAuth } from '@/context/AuthContext';
import { useWorkspace } from '@/context/WorkspaceContext';
import type { Project } from '@/types/api';

interface WorkspaceListState {
  workspaces: Project[];
  loading: boolean;
  error: string | null;
  reload: () => void;
}

export function useWorkspaceList(): WorkspaceListState {
  const { revision } = useWorkspace();
  const { accessToken } = useAuth();
  const [workspaces, setWorkspaces] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const items = await services.workspace.listWorkspaces({
          accessToken,
        });
        if (!cancelled) {
          setWorkspaces(items);
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error ? err.message : 'Failed to load workspaces',
          );
          setWorkspaces([]);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [revision, tick, accessToken]);

  return {
    workspaces,
    loading,
    error,
    reload: () => setTick((value) => value + 1),
  };
}
