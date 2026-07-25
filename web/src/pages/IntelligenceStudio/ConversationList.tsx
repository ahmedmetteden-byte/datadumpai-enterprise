import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { UI_COPY } from '@/constants/ui';
import { ConversationItem } from './ConversationItem';
import type { IntelligenceConversationSummary } from '@/types/intelligence';

export function ConversationList({
  pinned,
  recent,
  activeId,
  query,
  loading,
  onQueryChange,
  onSelect,
  onNew,
  onRename,
  onDelete,
  onTogglePin,
}: {
  pinned: IntelligenceConversationSummary[];
  recent: IntelligenceConversationSummary[];
  activeId: string | null;
  query: string;
  loading: boolean;
  onQueryChange: (value: string) => void;
  onSelect: (id: string) => void;
  onNew: () => void;
  onRename: (id: string) => void;
  onDelete: (id: string) => void;
  onTogglePin: (id: string) => void;
}) {
  return (
    <aside
      className="flex h-full min-h-0 flex-col border-r border-surface-border bg-white"
      aria-label={UI_COPY.studioConversations}
    >
      <div className="space-y-3 border-b border-surface-border p-4">
        <Button className="w-full" onClick={onNew}>
          {UI_COPY.studioNewConversation}
        </Button>
        <Input
          value={query}
          onChange={(event) => onQueryChange(event.target.value)}
          placeholder={UI_COPY.studioSearchConversations}
          aria-label={UI_COPY.studioSearchConversations}
          className="h-10"
        />
      </div>

      <div className="min-h-0 flex-1 space-y-5 overflow-y-auto p-3">
        {loading ? (
          <p className="px-1 text-small text-ink-muted">{UI_COPY.studioLoading}</p>
        ) : null}

        {pinned.length > 0 ? (
          <section>
            <h3 className="mb-2 px-1 text-caption uppercase tracking-wide text-ink-faint">
              {UI_COPY.studioPinned}
            </h3>
            <div className="space-y-1">
              {pinned.map((item) => (
                <ConversationItem
                  key={item.id}
                  item={item}
                  active={item.id === activeId}
                  onSelect={() => onSelect(item.id)}
                  onRename={() => onRename(item.id)}
                  onDelete={() => onDelete(item.id)}
                  onTogglePin={() => onTogglePin(item.id)}
                />
              ))}
            </div>
          </section>
        ) : null}

        <section>
          <h3 className="mb-2 px-1 text-caption uppercase tracking-wide text-ink-faint">
            {UI_COPY.studioRecent}
          </h3>
          {recent.length === 0 && pinned.length === 0 ? (
            <p className="px-1 text-small text-ink-muted">
              {UI_COPY.studioNoConversations}
            </p>
          ) : (
            <div className="space-y-1">
              {recent.map((item) => (
                <ConversationItem
                  key={item.id}
                  item={item}
                  active={item.id === activeId}
                  onSelect={() => onSelect(item.id)}
                  onRename={() => onRename(item.id)}
                  onDelete={() => onDelete(item.id)}
                  onTogglePin={() => onTogglePin(item.id)}
                />
              ))}
            </div>
          )}
        </section>
      </div>
    </aside>
  );
}
