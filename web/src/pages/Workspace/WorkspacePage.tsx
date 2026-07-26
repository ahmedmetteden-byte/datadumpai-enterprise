import { useEffect } from 'react';
import {
  Navigate,
  Route,
  Routes,
  useNavigate,
  useParams,
} from 'react-router-dom';
import { PageRequestState } from '@/components/feedback';
import { Button } from '@/components/ui/Button';
import { UI_COPY } from '@/constants/ui';
import { useWorkspace } from '@/context/WorkspaceContext';
import { useWorkspaceDetail } from '@/hooks/useWorkspaceDetail';
import { useWorkspacePermissions } from '@/hooks/useWorkspacePermissions';
import { WORKSPACE_ROUTES } from '@/lib/workspaceRoutes';
import { WorkspaceHeader } from './WorkspaceHeader';
import { WorkspaceSectionNav } from './WorkspaceSectionNav';
import { ActivitySection } from './sections/ActivitySection';
import { HealthSection } from './sections/HealthSection';
import { OverviewSection } from './sections/OverviewSection';
import { SettingsSection } from './sections/SettingsSection';
import { TeamPanelSection } from './sections/TeamSection';

function WorkspaceShell() {
  const { workspaceId } = useParams<{ workspaceId: string }>();
  const navigate = useNavigate();
  const { setActiveWorkspaceId } = useWorkspace();
  const { data, loading, error, forbidden, reload } =
    useWorkspaceDetail(workspaceId);
  const { capabilities } = useWorkspacePermissions(
    data?.membership?.role,
    loading,
  );

  useEffect(() => {
    if (workspaceId) {
      setActiveWorkspaceId(workspaceId);
    }
  }, [workspaceId, setActiveWorkspaceId]);

  if (forbidden) {
    return (
      <div className="flex min-h-[40vh] flex-col items-center justify-center gap-3 text-center">
        <p className="max-w-md text-body text-ink">{UI_COPY.workspaceForbidden}</p>
        <Button onClick={() => navigate(WORKSPACE_ROUTES.list)}>
          {UI_COPY.backToWorkspaces}
        </Button>
      </div>
    );
  }

  if (!capabilities.canView && !loading && data) {
    return (
      <div className="flex min-h-[40vh] flex-col items-center justify-center gap-3 text-center">
        <p className="max-w-md text-body text-ink">{UI_COPY.workspaceForbidden}</p>
        <Button onClick={() => navigate(WORKSPACE_ROUTES.list)}>
          {UI_COPY.backToWorkspaces}
        </Button>
      </div>
    );
  }

  return (
    <PageRequestState
      loading={loading && !data}
      error={
        !data
          ? error || (!workspaceId ? UI_COPY.workspacesLoadError : null)
          : null
      }
      onRetry={reload}
      loadingMessage={UI_COPY.loadingWorkspaces}
      errorTitle={UI_COPY.workspacesLoadError}
    >
      {data && workspaceId ? (
        <div className="space-y-6 pb-16">
          <WorkspaceHeader workspace={data.workspace} health={data.health} />
          <WorkspaceSectionNav workspaceId={workspaceId} />

          <Routes>
            <Route index element={<Navigate to="overview" replace />} />
            <Route path="overview" element={<OverviewSection data={data} />} />
            <Route path="health" element={<HealthSection health={data.health} />} />
            <Route
              path="activity"
              element={<ActivitySection activity={data.activity} />}
            />
            <Route
              path="team"
              element={
                <TeamPanelSection
                  team={data.team}
                  capabilities={capabilities}
                />
              }
            />
            <Route
              path="settings"
              element={
                <SettingsSection
                  workspace={data.workspace}
                  capabilities={capabilities}
                  onArchived={() => navigate(WORKSPACE_ROUTES.list)}
                />
              }
            />
            <Route path="*" element={<Navigate to="overview" replace />} />
          </Routes>
        </div>
      ) : null}
    </PageRequestState>
  );
}

export function WorkspacePage() {
  return <WorkspaceShell />;
}
