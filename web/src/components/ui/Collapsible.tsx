import { useId, useState, type ReactNode } from 'react';
import { cn } from '@/lib/cn';

export function Collapsible({
  title,
  children,
  defaultOpen = true,
  className,
}: {
  title: string;
  children: ReactNode;
  defaultOpen?: boolean;
  className?: string;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const panelId = useId();

  return (
    <section
      className={cn(
        'rounded-lg border border-surface-border bg-white',
        className,
      )}
    >
      <h3>
        <button
          type="button"
          aria-expanded={open}
          aria-controls={panelId}
          onClick={() => setOpen((value) => !value)}
          className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left text-card text-ink transition-colors hover:bg-surface-alt rounded-lg"
        >
          <span>{title}</span>
          <span
            aria-hidden
            className={cn(
              'text-ink-faint transition-transform duration-200',
              open && 'rotate-180',
            )}
          >
            ▾
          </span>
        </button>
      </h3>
      <div
        id={panelId}
        hidden={!open}
        className={cn(
          'border-t border-surface-border-light px-4 py-4',
          open && 'animate-fade-in',
        )}
      >
        {children}
      </div>
    </section>
  );
}
