import { Drawer } from '@/components/drawers/Drawer';
import { UI_COPY } from '@/constants/ui';
import { formatConfidence, formatRelativeTime } from '@/lib/format';
import type { HomePageData } from '@/types/home';
import { AiRecommendationsSection } from './insights/AiRecommendationsSection';
import { OrganizationalIntelligenceSection } from './insights/OrganizationalIntelligenceSection';
import { RecentActivitySection } from './insights/RecentActivitySection';
import { TeamSection } from './insights/TeamSection';
import { TodaysBriefSection } from './insights/TodaysBriefSection';
import { WorkspaceHealthSection } from './insights/WorkspaceHealthSection';

export function WorkspaceInsightsDrawer({
  open,
  onClose,
  insights,
}: {
  open: boolean;
  onClose: () => void;
  insights: HomePageData['insights'];
}) {
  return (
    <Drawer
      open={open}
      onClose={onClose}
      title={UI_COPY.workspaceInsights}
      widthClassName="max-w-lg"
    >
      <div className="space-y-4">
        <TodaysBriefSection brief={insights.brief} />
        <AiRecommendationsSection recommendations={insights.recommendations} />
        <RecentActivitySection activity={insights.recentActivity} />
        <WorkspaceHealthSection health={insights.health} />
        <TeamSection team={insights.team} />
        <OrganizationalIntelligenceSection
          signals={insights.organizationalIntelligence}
        />

        <section className="rounded-lg border border-surface-border bg-surface-alt/50 p-4">
          <h3 className="text-card text-ink">{UI_COPY.aiInsightsList}</h3>
          <ul className="mt-3 space-y-3">
            {insights.items.map((item) => (
              <li key={item.id}>
                <div className="text-small font-medium text-ink">{item.title}</div>
                <p className="mt-0.5 text-small text-ink-muted">{item.summary}</p>
                <p className="mt-1 text-caption text-ink-faint">
                  {formatConfidence(item.confidence)} ·{' '}
                  {formatRelativeTime(item.updatedAt)}
                </p>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </Drawer>
  );
}
