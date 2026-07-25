import { EmptyState } from '@/components/ui/EmptyState';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { UI_COPY } from '@/constants/ui';
import { formatRelativeTime } from '@/lib/format';
import type { ActivityLog } from '@/types/api';

export function ActivitySection({ activity }: { activity: ActivityLog[] }) {
  return (
    <section className="animate-slide-up rounded-xl border border-surface-border bg-white p-6 sm:p-8">
      <SectionHeader
        title={UI_COPY.workspaceTimeline}
        description={UI_COPY.recentActivity}
      />
      {activity.length === 0 ? (
        <EmptyState
          className="border-0 bg-surface-alt/50 py-12"
          icon="◷"
          title={UI_COPY.emptyActivityTitle}
          description={UI_COPY.emptyActivityDescription}
        />
      ) : (
        <ol className="relative space-y-0 border-l border-surface-border pl-6">
          {activity.map((entry) => (
            <li key={entry.id} className="relative pb-6 last:pb-0">
              <span
                aria-hidden
                className="absolute -left-[1.625rem] top-1.5 h-2.5 w-2.5 rounded-full border-2 border-white bg-brand-500"
              />
              <div className="text-card text-ink">{entry.message}</div>
              <div className="mt-1 flex flex-wrap gap-2 text-caption text-ink-faint">
                <span>{formatRelativeTime(entry.createdAt)}</span>
                <span aria-hidden>·</span>
                <span className="font-mono">{entry.action}</span>
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
