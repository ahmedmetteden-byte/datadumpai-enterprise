import { Link } from 'react-router-dom';
import { Badge } from '@/components/ui/Badge';
import { UI_COPY } from '@/constants/ui';
import { formatNumber, formatPercent, formatRelativeTime } from '@/lib/format';
import type { DashboardMetric, DashboardRecentItem, HomeDashboard } from '@/types/home';

export function DashboardMetrics({ metrics }: { metrics: DashboardMetric[] }) {
  return (
    <section
      className="animate-slide-up [animation-delay:80ms]"
      aria-label={UI_COPY.dashboardMetrics}
    >
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {metrics.map((metric) => (
          <article
            key={metric.id}
            className="rounded-xl border border-surface-border bg-white px-5 py-4 shadow-sm"
          >
            <p className="text-caption uppercase tracking-wide text-ink-faint">
              {metric.label}
            </p>
            <p className="mt-2 text-page-title tabular-nums text-ink">
              {metric.unit === 'percent'
                ? formatPercent(metric.value)
                : formatNumber(metric.value)}
            </p>
          </article>
        ))}
      </div>
    </section>
  );
}

const MAX_RECENT_ITEMS = 8;

const KIND_LABEL: Record<DashboardRecentItem['kind'], string> = {
  document: UI_COPY.dashboardKindDocument,
  report: UI_COPY.dashboardKindReport,
  conversation: UI_COPY.dashboardKindConversation,
  workspace: UI_COPY.dashboardKindDocument,
};

const KIND_TONE: Record<
  DashboardRecentItem['kind'],
  'neutral' | 'brand' | 'success'
> = {
  document: 'neutral',
  report: 'brand',
  conversation: 'success',
  workspace: 'neutral',
};

export function DashboardRecents({ dashboard }: { dashboard: HomeDashboard }) {
  const items = [
    ...dashboard.recentUploads,
    ...dashboard.recentReports,
    ...dashboard.recentConversations,
  ]
    .sort((a, b) => (a.at < b.at ? 1 : a.at > b.at ? -1 : 0))
    .slice(0, MAX_RECENT_ITEMS);

  return (
    <section
      className="animate-slide-up rounded-xl border border-surface-border bg-white p-4 shadow-sm [animation-delay:200ms]"
      aria-label={UI_COPY.homeComposerRecentTitle}
    >
      {items.length === 0 ? (
        <p className="text-small text-ink-muted">
          {UI_COPY.dashboardMostRecentEmpty}
        </p>
      ) : (
        <ul className="divide-y divide-surface-border">
          {items.map((item) => (
            <li key={`${item.kind}-${item.id}`}>
              <Link
                to={item.href}
                className="flex items-center gap-3 rounded-lg px-2 py-2.5 hover:bg-surface-alt/70 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
              >
                <Badge tone={KIND_TONE[item.kind]} className="shrink-0">
                  {KIND_LABEL[item.kind]}
                </Badge>
                <div className="min-w-0 flex-1">
                  <div className="truncate text-small font-medium text-ink">
                    {item.title}
                  </div>
                  <div className="truncate text-caption text-ink-muted">
                    {item.subtitle}
                  </div>
                </div>
                <span className="shrink-0 text-caption text-ink-faint">
                  {formatRelativeTime(item.at)}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
