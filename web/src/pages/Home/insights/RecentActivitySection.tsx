import { Collapsible } from '@/components/ui/Collapsible';
import { UI_COPY } from '@/constants/ui';
import { formatRelativeTime } from '@/lib/format';
import type { ActivityLog } from '@/types/api';

export function RecentActivitySection({
  activity,
}: {
  activity: ActivityLog[];
}) {
  return (
    <Collapsible title={UI_COPY.recentActivity} defaultOpen>
      <ol className="space-y-3">
        {activity.map((entry) => (
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
    </Collapsible>
  );
}
