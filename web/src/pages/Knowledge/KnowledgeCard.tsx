import { ProcessingBadge } from '@/pages/Knowledge/ProcessingBadge';
import {
  formatKnowledgeDate,
  KNOWLEDGE_TYPE_SINGULAR,
} from '@/lib/knowledgeLabels';
import { cn } from '@/lib/cn';
import type { KnowledgeListItem } from '@/types/knowledge';

export function KnowledgeCard({
  item,
  selected,
  checked,
  onSelect,
  onToggleCheck,
}: {
  item: KnowledgeListItem;
  selected: boolean;
  checked: boolean;
  onSelect: () => void;
  onToggleCheck: () => void;
}) {
  return (
    <article
      className={cn(
        'group relative flex flex-col rounded-xl border bg-white p-4 text-left transition-shadow',
        selected
          ? 'border-brand-500 shadow-sm ring-1 ring-brand-500'
          : 'border-surface-border hover:border-brand-200 hover:shadow-sm',
      )}
    >
      <div className="mb-3 flex items-start justify-between gap-2">
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={checked}
            onChange={onToggleCheck}
            onClick={(event) => event.stopPropagation()}
            className="h-4 w-4 rounded border-surface-border text-brand-500 focus:ring-brand-500"
            aria-label={`Select ${item.title}`}
          />
          <span className="text-caption font-medium uppercase tracking-wide text-ink-muted">
            {KNOWLEDGE_TYPE_SINGULAR[item.type]}
          </span>
        </label>
        <ProcessingBadge status={item.status} />
      </div>
      <button
        type="button"
        onClick={onSelect}
        className="flex flex-1 flex-col text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2 rounded-md"
      >
        <h3 className="text-body font-semibold text-ink line-clamp-2">
          {item.title}
        </h3>
        {item.summary ? (
          <p className="mt-1 line-clamp-2 text-small text-ink-muted">
            {item.summary}
          </p>
        ) : null}
        <div className="mt-auto flex flex-wrap items-center gap-x-3 gap-y-1 pt-3 text-caption text-ink-muted">
          {item.authorName ? <span>{item.authorName}</span> : null}
          {item.projectName ? <span>{item.projectName}</span> : null}
          <span>{formatKnowledgeDate(item.updatedAt)}</span>
        </div>
      </button>
    </article>
  );
}
