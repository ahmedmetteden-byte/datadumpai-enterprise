import { useEffect, useState } from 'react';
import { ApiError } from '@/api/client';
import { services } from '@/api/services';
import { useAuth } from '@/context/AuthContext';
import { useWorkspace } from '@/context/WorkspaceContext';
import type { ActivityLog, Project } from '@/types/api';
import type {
  ContinueWorkingItem,
  TeamMember,
  WorkspaceHealthSummary,
  WorkspaceInsightsOverview,
} from '@/types/home';
import type { WorkspaceMembership } from '@/types/workspace';

export interface WorkspaceDetailData {
  workspace: Project;
  health: WorkspaceHealthSummary;
  insightsOverview: WorkspaceInsightsOverview;
  team: TeamMember[];
  activity: ActivityLog[];
  continueWorking: ContinueWorkingItem[];
  membership: WorkspaceMembership | null;
}

interface WorkspaceDetailState {
  data: WorkspaceDetailData | null;
  loading: boolean;
  error: string | null;
  forbidden: boolean;
  reload: () => void;
}

export function useWorkspaceDetail(
  workspaceId: string | undefined,
): WorkspaceDetailState {
  const { revision } = useWorkspace();
  const { accessToken } = useAuth();
  const auth = { accessToken };
  const [data, setData] = useState<WorkspaceDetailData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [forbidden, setForbidden] = useState(false);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      if (!workspaceId) {
        setData(null);
        setLoading(false);
        setError(null);
        setForbidden(false);
        return;
      }

      setLoading(true);
      setError(null);
      setForbidden(false);

      try {
        const [
          workspace,
          health,
          insightsOverview,
          team,
          activity,
          continueWorking,
          membership,
        ] = await Promise.all([
          services.workspace.getWorkspace(workspaceId, auth),
          services.workspace.getHealth(workspaceId, auth),
          services.workspace.getInsightsOverview(workspaceId, auth),
          services.workspace.getTeam(workspaceId, auth),
          services.workspace.getRecentActivity(workspaceId, 20, auth),
          services.workspace.getContinueWorking(workspaceId, auth),
          services.workspace.getMyMembership(workspaceId, auth),
        ]);

        if (!cancelled) {
          setData({
            workspace,
            health,
            insightsOverview,
            team,
            activity,
            continueWorking,
            membership,
          });
        }
      } catch (err) {
        if (!cancelled) {
          const isForbidden =
            err instanceof ApiError &&
            (err.status === 403 || err.status === 404);
          setForbidden(isForbidden);
          setError(
            err instanceof Error ? err.message : 'Failed to load workspace',
          );
          setData(null);
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
  }, [workspaceId, revision, tick, accessToken]);

  return {
    data,
    loading,
    error,
    forbidden,
    reload: () => setTick((value) => value + 1),
  };
}
