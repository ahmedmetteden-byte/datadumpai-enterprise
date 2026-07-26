import { Link } from 'react-router-dom';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { UI_COPY } from '@/constants/ui';
import { formatNumber, formatPercent, formatRelativeTime } from '@/lib/format';
import type { DashboardMetric, HomeDashboard } from '@/types/home';

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

export function DashboardRecents({ dashboard }: { dashboard: HomeDashboard }) {
  return (
    <section className="animate-slide-up grid gap-6 [animation-delay:200ms] lg:grid-cols-3">
      <RecentColumn
        title={UI_COPY.dashboardRecentUploads}
        empty={UI_COPY.dashboardRecentUploadsEmpty}
        items={dashboard.recentUploads}
      />
      <RecentColumn
        title={UI_COPY.dashboardRecentReports}
        empty={UI_COPY.dashboardRecentReportsEmpty}
        items={dashboard.recentReports}
      />
      <RecentColumn
        title={UI_COPY.dashboardRecentConversations}
        empty={UI_COPY.dashboardRecentConversationsEmpty}
        items={dashboard.recentConversations}
      />
    </section>
  );
}

function RecentColumn({
  title,
  empty,
  items,
}: {
  title: string;
  empty: string;
  items: HomeDashboard['recentUploads'];
}) {
  return (
    <div className="rounded-xl border border-surface-border bg-white p-4 shadow-sm">
      <SectionHeader title={title} className="mb-3" />
      {items.length === 0 ? (
        <p className="text-small text-ink-muted">{empty}</p>
      ) : (
        <ul className="space-y-2">
          {items.map((item) => (
            <li key={item.id}>
              <Link
                to={item.href}
                className="block rounded-lg px-2 py-2 hover:bg-surface-alt/70 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
              >
                <div className="truncate text-small font-medium text-ink">
                  {item.title}
                </div>
                <div className="mt-0.5 flex items-center justify-between gap-2 text-caption text-ink-muted">
                  <span className="truncate">{item.subtitle}</span>
                  <span className="shrink-0">
                    {formatRelativeTime(item.at)}
                  </span>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
