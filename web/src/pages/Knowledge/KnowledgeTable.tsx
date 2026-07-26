import { Button } from '@/components/ui/Button';
import { IndexingProgress } from '@/pages/Knowledge/IndexingProgress';
import { formatKnowledgeDate } from '@/lib/knowledgeLabels';
import { formatStorageBytes } from '@/lib/workspacePermissions';
import { cn } from '@/lib/cn';
import { UI_COPY } from '@/constants/ui';
import type { KnowledgeListItem } from '@/types/knowledge';

function TagsCell({ tags }: { tags?: string[] }) {
  if (!tags || tags.length === 0) {
    return <span className="text-ink-faint">—</span>;
  }
  return (
    <div className="flex max-w-[10rem] flex-wrap gap-1">
      {tags.slice(0, 3).map((tag) => (
        <span
          key={tag}
          className="inline-flex rounded-md bg-surface-alt px-1.5 py-0.5 text-caption text-ink-muted"
        >
          {tag}
        </span>
      ))}
      {tags.length > 3 ? (
        <span className="text-caption text-ink-faint">+{tags.length - 3}</span>
      ) : null}
    </div>
  );
}

export function KnowledgeTable({
  items,
  selectedId,
  selectedIds,
  onToggleCheck,
  onToggleAll,
  onView,
  onDelete,
  onReindex,
  onDownload,
}: {
  items: KnowledgeListItem[];
  selectedId: string | null;
  selectedIds: string[];
  onToggleCheck: (id: string) => void;
  onToggleAll: () => void;
  onView: (id: string) => void;
  onDelete: (id: string) => void;
  onReindex: (id: string) => void;
  onDownload: (id: string) => void;
}) {
  const allChecked = items.length > 0 && selectedIds.length === items.length;

  return (
    <div className="overflow-x-auto rounded-xl border border-surface-border bg-white shadow-sm">
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
            <th className="px-3 py-3 font-medium">
              {UI_COPY.knowledgeColFilename}
            </th>
            <th className="px-3 py-3 font-medium">
              {UI_COPY.knowledgeColSize}
            </th>
            <th className="px-3 py-3 font-medium">{UI_COPY.knowledgeColStatus}</th>
            <th className="px-3 py-3 font-medium">
              {UI_COPY.knowledgeColIndexed}
            </th>
            <th className="px-3 py-3 font-medium">
              {UI_COPY.knowledgeColCreated}
            </th>
            <th className="px-3 py-3 font-medium">
              {UI_COPY.knowledgeColTags}
            </th>
            <th className="px-3 py-3 font-medium">
              {UI_COPY.knowledgeColCollection}
            </th>
            <th className="px-3 py-3 font-medium">
              {UI_COPY.knowledgeColActions}
            </th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => {
            const active = selectedId === item.id;
            const filename = item.filename || item.title;
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
                    aria-label={`Select ${filename}`}
                    className="h-4 w-4 rounded border-surface-border text-brand-500 focus:ring-brand-500"
                  />
                </td>
                <td className="max-w-[14rem] px-3 py-3">
                  <button
                    type="button"
                    onClick={() => onView(item.id)}
                    className="truncate text-left font-medium text-ink hover:text-brand-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
                    title={filename}
                  >
                    {filename}
                  </button>
                </td>
                <td className="whitespace-nowrap px-3 py-3 text-ink-muted">
                  {typeof item.sizeBytes === 'number'
                    ? formatStorageBytes(item.sizeBytes)
                    : '—'}
                </td>
                <td className="min-w-[9rem] px-3 py-3">
                  <IndexingProgress
                    status={item.status}
                    progressPercent={item.progressPercent}
                    indexStage={item.indexStage}
                    compact
                  />
                </td>
                <td className="whitespace-nowrap px-3 py-3 text-ink-muted">
                  {item.indexedAt
                    ? formatKnowledgeDate(item.indexedAt)
                    : '—'}
                </td>
                <td className="whitespace-nowrap px-3 py-3 text-ink-muted">
                  {formatKnowledgeDate(item.createdAt)}
                </td>
                <td className="px-3 py-3">
                  <TagsCell tags={item.tags} />
                </td>
                <td className="px-3 py-3 text-ink-muted">
                  {item.collectionName || 'Library'}
                </td>
                <td className="px-3 py-3">
                  <div className="flex flex-wrap gap-1">
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => onView(item.id)}
                    >
                      {UI_COPY.knowledgeActionView}
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => onDownload(item.id)}
                    >
                      {UI_COPY.knowledgeActionDownload}
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => onDelete(item.id)}
                    >
                      {UI_COPY.knowledgeActionDelete}
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => onReindex(item.id)}
                    >
                      {UI_COPY.knowledgeActionReindex}
                    </Button>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
