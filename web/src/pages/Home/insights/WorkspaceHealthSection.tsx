import { Collapsible } from '@/components/ui/Collapsible';
import { ProgressRing } from '@/components/ui/ProgressRing';
import { UI_COPY } from '@/constants/ui';
import { formatPercent, formatRelativeTime } from '@/lib/format';
import type { WorkspaceHealthSummary } from '@/types/home';

const statusDot: Record<string, string> = {
  ready: 'bg-success',
  warning: 'bg-warning',
  critical: 'bg-danger',
};

export function WorkspaceHealthSection({
  health,
}: {
  health: WorkspaceHealthSummary;
}) {
  return (
    <Collapsible title={UI_COPY.workspaceHealth} defaultOpen>
      <div className="mb-4 flex items-center gap-4">
        <ProgressRing value={health.overallPercent} />
        <div>
          <div className="text-card text-ink">
            {UI_COPY.overallHealth} {formatPercent(health.overallPercent)}
          </div>
          <p className="mt-1 text-caption text-ink-muted">
            {UI_COPY.lastUpdated} {formatRelativeTime(health.lastUpdated)}
          </p>
        </div>
      </div>
      <ul className="space-y-2">
        {health.indicators.map((indicator) => (
          <li
            key={`${indicator.status}-${indicator.message}`}
            className="flex items-start gap-2 rounded-md bg-surface-alt px-3 py-2 text-small text-ink"
          >
            <span
              aria-hidden
              className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${statusDot[indicator.status] ?? 'bg-ink-faint'}`}
            />
            <span>{indicator.message}</span>
          </li>
        ))}
      </ul>
    </Collapsible>
  );
}
