import { Badge } from '@/components/ui/Badge';
import { EmptyState } from '@/components/ui/EmptyState';
import { ProgressRing } from '@/components/ui/ProgressRing';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { UI_COPY } from '@/constants/ui';
import { formatPercent, formatRelativeTime } from '@/lib/format';
import type { WorkspaceHealthSummary } from '@/types/home';

const statusTone = {
  ready: 'success',
  warning: 'warning',
  critical: 'neutral',
} as const;

export function HealthSection({ health }: { health: WorkspaceHealthSummary }) {
  return (
    <section className="animate-slide-up space-y-6">
      <div className="rounded-xl border border-surface-border bg-white p-6 sm:p-8">
        <div className="flex flex-wrap items-center gap-6">
          <ProgressRing value={health.overallPercent} size={96} strokeWidth={8} />
          <div>
            <SectionHeader
              title={UI_COPY.workspaceHealth}
              description={`${UI_COPY.lastUpdated} ${formatRelativeTime(health.lastUpdated)}`}
              className="mb-0"
            />
            <p className="mt-3 text-body text-ink">
              {UI_COPY.overallHealth}{' '}
              <span className="font-semibold">
                {formatPercent(health.overallPercent)}
              </span>
            </p>
            <Badge className="mt-3" tone={statusTone[health.status]}>
              {health.status}
            </Badge>
          </div>
        </div>
      </div>

      <div className="rounded-xl border border-surface-border bg-white p-6">
        <h3 className="mb-4 text-card text-ink">{UI_COPY.healthIndicators}</h3>
        {health.indicators.length === 0 ? (
          <EmptyState
            className="border-0 bg-surface-alt/50 py-10"
            title={UI_COPY.emptyHealthTitle}
            description={UI_COPY.emptyHealthDescription}
          />
        ) : (
          <ul className="space-y-3">
            {health.indicators.map((indicator) => (
              <li
                key={`${indicator.status}-${indicator.message}`}
                className="flex items-start gap-3 rounded-lg bg-surface-alt px-4 py-3"
              >
                <Badge tone={statusTone[indicator.status]}>
                  {indicator.status}
                </Badge>
                <span className="text-small text-ink">{indicator.message}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
