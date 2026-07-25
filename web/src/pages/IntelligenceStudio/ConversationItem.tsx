import { cn } from '@/lib/cn';
import { formatRelativeTime } from '@/lib/format';
import type { IntelligenceConversationSummary } from '@/types/intelligence';

export function ConversationItem({
  item,
  active,
  onSelect,
  onRename,
  onDelete,
  onTogglePin,
}: {
  item: IntelligenceConversationSummary;
  active: boolean;
  onSelect: () => void;
  onRename: () => void;
  onDelete: () => void;
  onTogglePin: () => void;
}) {
  return (
    <div
      className={cn(
        'group rounded-md border px-2.5 py-2 transition-colors',
        active
          ? 'border-brand-200 bg-brand-50'
          : 'border-transparent hover:bg-surface-alt',
      )}
    >
      <button
        type="button"
        onClick={onSelect}
        className="w-full text-left focus-visible:outline-none"
        aria-current={active ? 'true' : undefined}
      >
        <div className="flex items-start justify-between gap-2">
          <span className="truncate text-small font-medium text-ink">
            {item.pinned ? '📌 ' : ''}
            {item.title}
          </span>
          <span className="shrink-0 text-caption text-ink-faint">
            {formatRelativeTime(item.updatedAt)}
          </span>
        </div>
        <p className="mt-1 line-clamp-2 text-caption text-ink-muted">
          {item.preview}
        </p>
      </button>
      <div className="mt-2 hidden gap-2 group-hover:flex group-focus-within:flex">
        <button
          type="button"
          className="text-caption text-ink-muted hover:text-ink"
          onClick={onTogglePin}
        >
          {item.pinned ? 'Unpin' : 'Pin'}
        </button>
        <button
          type="button"
          className="text-caption text-ink-muted hover:text-ink"
          onClick={onRename}
        >
          Rename
        </button>
        <button
          type="button"
          className="text-caption text-danger hover:text-red-700"
          onClick={onDelete}
        >
          Delete
        </button>
      </div>
    </div>
  );
}
