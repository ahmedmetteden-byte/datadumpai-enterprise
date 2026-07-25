import { WorkspaceCard } from '@/components/cards/WorkspaceCard';
import { EmptyState } from '@/components/ui/EmptyState';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { UI_COPY } from '@/constants/ui';
import type { ContinueWorkingItem } from '@/types/home';

export function ContinueWorking({ items }: { items: ContinueWorkingItem[] }) {
  return (
    <section className="animate-slide-up [animation-delay:180ms]">
      <SectionHeader title={UI_COPY.continueWorking} />
      {items.length === 0 ? (
        <EmptyState
          icon="⇢"
          title={UI_COPY.emptyContinueTitle}
          description={UI_COPY.emptyContinueDescription}
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {items.map((item) => (
            <WorkspaceCard key={item.id} item={item} />
          ))}
        </div>
      )}
    </section>
  );
}
