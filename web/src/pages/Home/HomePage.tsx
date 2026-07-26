import { useEffect } from 'react';
import { PageRequestState } from '@/components/feedback';
import { useWorkspace } from '@/context/WorkspaceContext';
import { UI_COPY } from '@/constants/ui';
import { useDisclosure } from '@/hooks/useDisclosure';
import { useHomeData } from '@/hooks/useHomeData';
import { ContinueWorking } from './ContinueWorking';
import { DashboardMetrics, DashboardRecents } from './DashboardMetrics';
import { HeroSection } from './HeroSection';
import { QuickActions } from './QuickActions';
import { UniversalSearch } from './UniversalSearch';
import { WorkspaceInsightsCard } from './WorkspaceInsightsCard';
import { WorkspaceInsightsDrawer } from './WorkspaceInsightsDrawer';

export function HomePage() {
  const { activeWorkspaceId, setActiveWorkspaceId } = useWorkspace();
  const { data, loading, error, reload } = useHomeData(
    activeWorkspaceId ?? undefined,
  );
  const insightsDrawer = useDisclosure(false);

  useEffect(() => {
    if (data?.activeWorkspace && !activeWorkspaceId) {
      setActiveWorkspaceId(data.activeWorkspace.id);
    }
  }, [data, activeWorkspaceId, setActiveWorkspaceId]);

  return (
    <PageRequestState
      loading={loading && !data}
      error={!data ? error || (loading ? null : UI_COPY.loadError) : null}
      onRetry={reload}
      loadingMessage={UI_COPY.loadingHome}
      errorTitle={UI_COPY.loadError}
    >
      {data ? (
        <div className="space-y-10 pb-16">
          <HeroSection
            greeting={data.greeting}
            unreadCount={data.unreadNotificationCount}
            notifications={data.notifications}
          />

          <DashboardMetrics metrics={data.dashboard?.metrics ?? []} />
          <UniversalSearch payload={data.search} />
          <QuickActions actions={data.quickActions} />
          <DashboardRecents
            dashboard={
              data.dashboard ?? {
                metrics: [],
                recentUploads: [],
                recentReports: [],
                recentConversations: [],
              }
            }
          />
          <ContinueWorking items={data.continueWorking} />
          <WorkspaceInsightsCard
            overview={data.insightsOverview}
            onViewInsights={insightsDrawer.open}
          />

          <WorkspaceInsightsDrawer
            open={insightsDrawer.isOpen}
            onClose={insightsDrawer.close}
            insights={data.insights}
          />
        </div>
      ) : null}
    </PageRequestState>
  );
}
