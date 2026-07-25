import { useEffect } from 'react';
import { Button } from '@/components/ui/Button';
import { useWorkspace } from '@/context/WorkspaceContext';
import { UI_COPY } from '@/constants/ui';
import { useDisclosure } from '@/hooks/useDisclosure';
import { useHomeData } from '@/hooks/useHomeData';
import { ContinueWorking } from './ContinueWorking';
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
    if (data && !activeWorkspaceId) {
      setActiveWorkspaceId(data.activeWorkspace.id);
    }
  }, [data, activeWorkspaceId, setActiveWorkspaceId]);

  if (loading && !data) {
    return (
      <div
        className="flex min-h-[40vh] items-center justify-center text-small text-ink-muted"
        role="status"
        aria-live="polite"
      >
        {UI_COPY.loadingHome}
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="flex min-h-[40vh] flex-col items-center justify-center gap-3 text-center">
        <p className="text-body text-ink">{UI_COPY.loadError}</p>
        <p className="text-small text-ink-muted">{error}</p>
        <Button onClick={reload}>{UI_COPY.retry}</Button>
      </div>
    );
  }

  return (
    <div className="space-y-10 pb-16">
      <HeroSection
        greeting={data.greeting}
        unreadCount={data.unreadNotificationCount}
        notifications={data.notifications}
      />

      <UniversalSearch payload={data.search} />
      <QuickActions actions={data.quickActions} />
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
  );
}
