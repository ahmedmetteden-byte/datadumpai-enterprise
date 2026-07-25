import { Badge } from '@/components/ui/Badge';
import { Collapsible } from '@/components/ui/Collapsible';
import { UI_COPY } from '@/constants/ui';
import type { OrgIntelligenceSignal } from '@/types/home';

const trendTone = {
  up: 'success',
  down: 'warning',
  flat: 'neutral',
} as const;

export function OrganizationalIntelligenceSection({
  signals,
}: {
  signals: OrgIntelligenceSignal[];
}) {
  return (
    <Collapsible title={UI_COPY.organizationalIntelligence} defaultOpen={false}>
      <ul className="space-y-3">
        {signals.map((signal) => (
          <li
            key={signal.id}
            className="rounded-md border border-surface-border-light p-3"
          >
            <div className="mb-1 flex items-center justify-between gap-2">
              <span className="text-card text-ink">{signal.title}</span>
              <Badge tone={trendTone[signal.trend]}>{signal.valueLabel}</Badge>
            </div>
            <p className="text-small text-ink-muted">{signal.summary}</p>
          </li>
        ))}
      </ul>
    </Collapsible>
  );
}
