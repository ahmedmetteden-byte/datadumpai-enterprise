import { Link } from 'react-router-dom';
import { Badge } from '@/components/ui/Badge';
import { Collapsible } from '@/components/ui/Collapsible';
import { UI_COPY } from '@/constants/ui';
import type { TodaysBrief } from '@/types/home';

const priorityTone = {
  high: 'warning',
  medium: 'brand',
  low: 'neutral',
} as const;

export function TodaysBriefSection({ brief }: { brief: TodaysBrief }) {
  return (
    <Collapsible title={UI_COPY.todaysBrief} defaultOpen>
      <p className="mb-4 text-small text-ink-muted">{brief.greeting}</p>
      <ul className="space-y-3">
        {brief.items.map((item) => {
          const body = (
            <div className="rounded-md border border-surface-border-light bg-surface-alt/60 p-3 transition-colors hover:bg-surface-alt">
              <div className="mb-1.5 flex items-center justify-between gap-2">
                <span className="text-card text-ink">{item.headline}</span>
                <Badge tone={priorityTone[item.priority]}>{item.priority}</Badge>
              </div>
              <p className="text-small text-ink-muted">{item.detail}</p>
            </div>
          );

          return (
            <li key={item.id}>
              {item.href ? <Link to={item.href}>{body}</Link> : body}
            </li>
          );
        })}
      </ul>
    </Collapsible>
  );
}
