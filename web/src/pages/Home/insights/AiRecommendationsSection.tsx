import { Link } from 'react-router-dom';
import { Collapsible } from '@/components/ui/Collapsible';
import { UI_COPY } from '@/constants/ui';
import { formatConfidence } from '@/lib/format';
import type { AiRecommendation } from '@/types/home';

export function AiRecommendationsSection({
  recommendations,
}: {
  recommendations: AiRecommendation[];
}) {
  return (
    <Collapsible title={UI_COPY.aiRecommendations} defaultOpen>
      <ul className="space-y-3">
        {recommendations.map((item) => (
          <li
            key={item.id}
            className="rounded-md border border-surface-border-light p-3"
          >
            <div className="text-card text-ink">{item.title}</div>
            <p className="mt-1 text-small text-ink-muted">{item.rationale}</p>
            <div className="mt-3 flex items-center justify-between gap-3">
              <span className="text-caption text-ink-faint">
                {formatConfidence(item.confidence)}
              </span>
              <Link
                to={item.actionHref}
                className="text-small font-medium text-brand-600 hover:text-brand-700"
              >
                {item.actionLabel} →
              </Link>
            </div>
          </li>
        ))}
      </ul>
    </Collapsible>
  );
}
