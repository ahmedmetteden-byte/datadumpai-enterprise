import { useWorkspace } from '@/context/WorkspaceContext';
import { UI_COPY } from '@/constants/ui';
import { useHomeData } from '@/hooks/useHomeData';
import { DashboardRecents } from './DashboardMetrics';
import { HomeComposer } from './HomeComposer';

export function HomePage() {
  const { activeWorkspaceId } = useWorkspace();
  const { data } = useHomeData(activeWorkspaceId ?? undefined);

  const dashboard = data?.dashboard;
  const hasRecents =
    dashboard &&
    (dashboard.recentUploads.length > 0 ||
      dashboard.recentReports.length > 0 ||
      dashboard.recentConversations.length > 0);

  return (
    <div className="space-y-12 pb-16">
      <HomeComposer />

      {hasRecents ? (
        <div className="mx-auto w-full max-w-5xl space-y-3">
          <h2 className="text-section text-ink">
            {UI_COPY.homeComposerRecentTitle}
          </h2>
          <DashboardRecents dashboard={dashboard} />
        </div>
      ) : null}
    </div>
  );
}
