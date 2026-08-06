import { ProcessingBadge } from '@/pages/Knowledge/ProcessingBadge';
import {
  formatKnowledgeDate,
  KNOWLEDGE_TYPE_SINGULAR,
} from '@/lib/knowledgeLabels';
import { cn } from '@/lib/cn';
import type { KnowledgeEntityType, KnowledgeListItem } from '@/types/knowledge';

const TYPE_CHIP: Record<KnowledgeEntityType, { bg: string; icon: string }> = {
  document: { bg: 'bg-brand-50 text-brand-700', icon: '📄' },
  meeting: { bg: 'bg-chip-teal-soft text-chip-teal', icon: '🗓️' },
  report: { bg: 'bg-chip-violet-soft text-chip-violet', icon: '📊' },
  policy: { bg: 'bg-chip-amber-soft text-chip-amber', icon: '📋' },
  project: { bg: 'bg-surface-alt text-ink-muted', icon: '📁' },
  decision: { bg: 'bg-chip-rose-soft text-chip-rose', icon: '✓' },
  action_item: { bg: 'bg-chip-rose-soft text-chip-rose', icon: '☑' },
};

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
  const chip = TYPE_CHIP[item.type];

  return (
    <article
      className={cn(
        'group relative flex flex-col rounded-xl border bg-white p-4 text-left transition-shadow',
        selected
          ? 'border-brand-500 shadow-sm ring-1 ring-brand-500'
          : 'border-surface-border hover:border-brand-200 hover:shadow-sm',
      )}
    >
      <label className="absolute right-3 top-3 z-10">
        <input
          type="checkbox"
          checked={checked}
          onChange={onToggleCheck}
          onClick={(event) => event.stopPropagation()}
          className={cn(
            'h-4 w-4 rounded border-surface-border text-brand-500 focus:ring-brand-500',
            !checked && 'opacity-0 transition-opacity group-hover:opacity-100',
          )}
          aria-label={`Select ${item.title}`}
        />
      </label>

      <button
        type="button"
        onClick={onSelect}
        className="flex flex-1 flex-col text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2 rounded-md"
      >
        <div className="mb-3 flex items-center gap-2.5">
          <span
            aria-hidden
            className={cn(
              'flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-base',
              chip.bg,
            )}
          >
            {chip.icon}
          </span>
          <span className="text-caption font-medium uppercase tracking-wide text-ink-faint">
            {KNOWLEDGE_TYPE_SINGULAR[item.type]}
          </span>
          <ProcessingBadge status={item.status} className="ml-auto mr-5" />
        </div>

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
          <span>{formatKnowledgeDate(item.updatedAt)}</span>
        </div>
      </button>
    </article>
  );
}
