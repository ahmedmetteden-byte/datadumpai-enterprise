import { ActionCard } from '@/components/cards/ActionCard';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { UI_COPY } from '@/constants/ui';
import type { QuickAction } from '@/types/home';

export function QuickActions({ actions }: { actions: QuickAction[] }) {
  return (
    <section className="animate-slide-up [animation-delay:120ms]">
      <SectionHeader title={UI_COPY.quickActions} />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {actions.map((action) => (
          <ActionCard key={action.id} action={action} />
        ))}
      </div>
    </section>
  );
}
