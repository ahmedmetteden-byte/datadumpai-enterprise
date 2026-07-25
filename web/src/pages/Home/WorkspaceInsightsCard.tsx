import { Button } from '@/components/ui/Button';
import { ProgressRing } from '@/components/ui/ProgressRing';
import { UI_COPY } from '@/constants/ui';
import { formatPercent, formatRelativeTime } from '@/lib/format';
import type { WorkspaceInsightsOverview } from '@/types/home';

export function WorkspaceInsightsCard({
  overview,
  onViewInsights,
}: {
  overview: WorkspaceInsightsOverview;
  onViewInsights: () => void;
}) {
  return (
    <section className="animate-slide-up [animation-delay:240ms]">
      <article className="overflow-hidden rounded-xl border border-surface-border bg-white shadow-card">
        <div className="flex flex-col gap-6 p-6 sm:flex-row sm:items-center sm:justify-between sm:p-8">
          <div className="flex items-center gap-5">
            <ProgressRing
              value={overview.healthPercent}
              size={88}
              strokeWidth={7}
              label={`${UI_COPY.workspaceHealth} ${formatPercent(overview.healthPercent)}`}
            />
            <div>
              <p className="text-caption uppercase tracking-wide text-ink-faint">
                {UI_COPY.workspaceInsights}
              </p>
              <h2 className="mt-1 text-section text-ink">
                {UI_COPY.workspaceHealth}
              </h2>
              <p className="mt-1 text-small text-ink-muted">
                {UI_COPY.lastUpdated}{' '}
                {formatRelativeTime(overview.lastUpdated)}
              </p>
            </div>
          </div>

          <Button
            variant="primary"
            onClick={onViewInsights}
            rightIcon={<span aria-hidden>→</span>}
          >
            {UI_COPY.viewInsights}
          </Button>
        </div>

        <div className="grid grid-cols-1 divide-y divide-surface-border-light border-t border-surface-border-light sm:grid-cols-3 sm:divide-x sm:divide-y-0">
          <Stat
            label={UI_COPY.workspaceHealth}
            value={formatPercent(overview.healthPercent)}
          />
          <Stat
            label={UI_COPY.newInsights}
            value={String(overview.newInsightCount)}
          />
          <Stat
            label={UI_COPY.awaitingReview}
            value={String(overview.reportsAwaitingReview)}
          />
        </div>
      </article>
    </section>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="px-6 py-4">
      <div className="text-caption text-ink-muted">{label}</div>
      <div className="mt-1 text-page-title text-ink">{value}</div>
    </div>
  );
}
