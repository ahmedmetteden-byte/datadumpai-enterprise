import { Link } from 'react-router-dom';
import { WorkspaceCard } from '@/components/cards/WorkspaceCard';
import { Badge } from '@/components/ui/Badge';
import { EmptyState } from '@/components/ui/EmptyState';
import { ProgressRing } from '@/components/ui/ProgressRing';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { UI_COPY } from '@/constants/ui';
import { formatPercent, formatRelativeTime } from '@/lib/format';
import { formatStorageBytes } from '@/lib/workspacePermissions';
import { WORKSPACE_ROUTES } from '@/lib/workspaceRoutes';
import type { WorkspaceDetailData } from '@/hooks/useWorkspaceDetail';

export function OverviewSection({ data }: { data: WorkspaceDetailData }) {
  const { workspace, health, insightsOverview, activity, continueWorking } =
    data;

  return (
    <div className="space-y-8 animate-slide-up">
      <section className="grid gap-4 sm:grid-cols-3">
        <MetricCard
          label={UI_COPY.workspaceHealth}
          value={formatPercent(insightsOverview.healthPercent)}
        />
        <MetricCard
          label={UI_COPY.newInsights}
          value={String(insightsOverview.newInsightCount)}
        />
        <MetricCard
          label={UI_COPY.awaitingReview}
          value={String(insightsOverview.reportsAwaitingReview)}
        />
      </section>

      <section className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
        <div className="rounded-xl border border-surface-border bg-white p-6">
          <SectionHeader title={UI_COPY.recentActivity} className="mb-4" />
          {activity.length === 0 ? (
            <EmptyState
              className="border-0 bg-transparent px-0 py-8"
              icon="◷"
              title={UI_COPY.emptyActivityTitle}
              description={UI_COPY.emptyActivityDescription}
            />
          ) : (
            <ol className="space-y-3">
              {activity.slice(0, 5).map((entry) => (
                <li key={entry.id} className="flex gap-3 text-small">
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-brand-500" />
                  <div>
                    <div className="text-ink">{entry.message}</div>
                    <div className="mt-0.5 text-caption text-ink-faint">
                      {formatRelativeTime(entry.createdAt)}
                    </div>
                  </div>
                </li>
              ))}
            </ol>
          )}
          <Link
            to={WORKSPACE_ROUTES.section(workspace.id, 'activity')}
            className="mt-4 inline-block text-small font-medium text-brand-600 hover:text-brand-700"
          >
            {UI_COPY.workspaceTimeline} →
          </Link>
        </div>

        <div className="rounded-xl border border-surface-border bg-white p-6">
          <div className="mb-4 flex items-center gap-4">
            <ProgressRing value={health.overallPercent} size={64} />
            <div>
              <div className="text-card text-ink">{UI_COPY.workspaceHealth}</div>
              <p className="mt-1 text-caption text-ink-muted">
                {UI_COPY.storageUsed}:{' '}
                {formatStorageBytes(workspace.storageUsed)}
              </p>
            </div>
          </div>
          {health.indicators.length === 0 ? (
            <EmptyState
              className="border-0 bg-transparent px-0 py-6"
              title={UI_COPY.emptyHealthTitle}
              description={UI_COPY.emptyHealthDescription}
            />
          ) : (
            <ul className="space-y-2">
              {health.indicators.slice(0, 3).map((indicator) => (
                <li
                  key={indicator.message}
                  className="flex items-start gap-2 text-small text-ink"
                >
                  <Badge
                    tone={
                      indicator.status === 'ready'
                        ? 'success'
                        : indicator.status === 'warning'
                          ? 'warning'
                          : 'neutral'
                    }
                  >
                    {indicator.status}
                  </Badge>
                  <span className="text-ink-muted">{indicator.message}</span>
                </li>
              ))}
            </ul>
          )}
          <Link
            to={WORKSPACE_ROUTES.section(workspace.id, 'health')}
            className="mt-4 inline-block text-small font-medium text-brand-600 hover:text-brand-700"
          >
            {UI_COPY.workspaceHealth} →
          </Link>
        </div>
      </section>

      <section>
        <SectionHeader title={UI_COPY.resumeWork} />
        {continueWorking.length === 0 ? (
          <EmptyState
            icon="⇢"
            title={UI_COPY.emptyContinueTitle}
            description={UI_COPY.emptyContinueDescription}
          />
        ) : (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {continueWorking.map((item) => (
              <WorkspaceCard key={item.id} item={item} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-surface-border bg-white px-5 py-4 shadow-sm">
      <div className="text-caption text-ink-muted">{label}</div>
      <div className="mt-1 text-page-title text-ink">{value}</div>
    </div>
  );
}
