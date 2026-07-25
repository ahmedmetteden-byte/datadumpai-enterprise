import { Badge } from '@/components/ui/Badge';
import { ProgressRing } from '@/components/ui/ProgressRing';
import { UI_COPY } from '@/constants/ui';
import { formatPercent, formatRelativeTime } from '@/lib/format';
import type { Project } from '@/types/api';
import type { WorkspaceHealthSummary } from '@/types/home';

export function WorkspaceHeader({
  workspace,
  health,
}: {
  workspace: Project;
  health: WorkspaceHealthSummary;
}) {
  return (
    <header className="animate-slide-up rounded-xl border border-surface-border bg-white p-6 shadow-card sm:p-8">
      <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
        <div className="min-w-0">
          <Badge
            tone={
              health.status === 'ready'
                ? 'success'
                : health.status === 'warning'
                  ? 'warning'
                  : 'neutral'
            }
          >
            {health.status}
          </Badge>
          <h1 className="mt-3 text-page-title text-ink">{workspace.name}</h1>
          {workspace.description ? (
            <p className="mt-2 max-w-2xl text-small text-ink-muted">
              {workspace.description}
            </p>
          ) : null}
          <p className="mt-3 text-caption text-ink-faint">
            {UI_COPY.lastUpdated} {formatRelativeTime(workspace.updatedAt)}
          </p>
        </div>

        <div className="flex items-center gap-4">
          <ProgressRing
            value={health.overallPercent}
            size={80}
            label={`${UI_COPY.workspaceHealth} ${formatPercent(health.overallPercent)}`}
          />
          <div>
            <div className="text-caption uppercase tracking-wide text-ink-faint">
              {UI_COPY.workspaceHealth}
            </div>
            <div className="mt-1 text-section text-ink">
              {formatPercent(health.overallPercent)}
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
