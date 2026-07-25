import { ProcessingBadge } from '@/pages/Knowledge/ProcessingBadge';
import {
  formatKnowledgeDate,
  KNOWLEDGE_TYPE_SINGULAR,
} from '@/lib/knowledgeLabels';
import { cn } from '@/lib/cn';
import { UI_COPY } from '@/constants/ui';
import type { KnowledgeListItem } from '@/types/knowledge';

export function KnowledgeTable({
  items,
  selectedId,
  selectedIds,
  onSelect,
  onToggleCheck,
  onToggleAll,
}: {
  items: KnowledgeListItem[];
  selectedId: string | null;
  selectedIds: string[];
  onSelect: (id: string) => void;
  onToggleCheck: (id: string) => void;
  onToggleAll: () => void;
}) {
  const allChecked = items.length > 0 && selectedIds.length === items.length;

  return (
    <div className="overflow-x-auto rounded-xl border border-surface-border bg-white">
      <table className="min-w-full text-left text-small">
        <thead className="border-b border-surface-border bg-surface-alt/60 text-caption uppercase tracking-wide text-ink-muted">
          <tr>
            <th className="w-10 px-3 py-3">
              <input
                type="checkbox"
                checked={allChecked}
                onChange={onToggleAll}
                aria-label={UI_COPY.knowledgeSelectAll}
                className="h-4 w-4 rounded border-surface-border text-brand-500 focus:ring-brand-500"
              />
            </th>
            <th className="px-3 py-3 font-medium">{UI_COPY.knowledgeColTitle}</th>
            <th className="px-3 py-3 font-medium">{UI_COPY.knowledgeColType}</th>
            <th className="px-3 py-3 font-medium">{UI_COPY.knowledgeColStatus}</th>
            <th className="px-3 py-3 font-medium">{UI_COPY.knowledgeColAuthor}</th>
            <th className="px-3 py-3 font-medium">{UI_COPY.knowledgeColUpdated}</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => {
            const active = selectedId === item.id;
            return (
              <tr
                key={item.id}
                className={cn(
                  'border-b border-surface-border last:border-0',
                  active ? 'bg-brand-50/50' : 'hover:bg-surface-alt/40',
                )}
              >
                <td className="px-3 py-3">
                  <input
                    type="checkbox"
                    checked={selectedIds.includes(item.id)}
                    onChange={() => onToggleCheck(item.id)}
                    aria-label={`Select ${item.title}`}
                    className="h-4 w-4 rounded border-surface-border text-brand-500 focus:ring-brand-500"
                  />
                </td>
                <td className="px-3 py-3">
                  <button
                    type="button"
                    onClick={() => onSelect(item.id)}
                    className="text-left font-medium text-ink hover:text-brand-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
                  >
                    {item.title}
                  </button>
                </td>
                <td className="px-3 py-3 text-ink-muted">
                  {KNOWLEDGE_TYPE_SINGULAR[item.type]}
                </td>
                <td className="px-3 py-3">
                  <ProcessingBadge status={item.status} />
                </td>
                <td className="px-3 py-3 text-ink-muted">
                  {item.authorName ?? '—'}
                </td>
                <td className="px-3 py-3 text-ink-muted">
                  {formatKnowledgeDate(item.updatedAt)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
