import { cn } from '@/lib/cn';

export interface TimelineStep {
  id: string;
  label: string;
  meta?: string;
  state: 'done' | 'active' | 'pending';
}

export function StatusTimeline({
  steps,
  className,
}: {
  steps: TimelineStep[];
  className?: string;
}) {
  return (
    <ol className={cn('space-y-0', className)}>
      {steps.map((step, index) => (
        <li key={step.id} className="relative flex gap-3 pb-4 last:pb-0">
          {index < steps.length - 1 ? (
            <span
              aria-hidden
              className={cn(
                'absolute left-[7px] top-4 h-full w-px',
                step.state === 'done' ? 'bg-success' : 'bg-surface-border',
              )}
            />
          ) : null}
          <span
            aria-hidden
            className={cn(
              'relative z-10 mt-0.5 flex h-4 w-4 shrink-0 rounded-full border-2',
              step.state === 'done' && 'border-success bg-success',
              step.state === 'active' &&
                'animate-pulse border-brand-500 bg-brand-500',
              step.state === 'pending' && 'border-surface-border bg-white',
            )}
          />
          <div className="min-w-0 pb-0.5">
            <p
              className={cn(
                'text-small font-medium',
                step.state === 'pending' ? 'text-ink-faint' : 'text-ink',
              )}
            >
              {step.label}
            </p>
            {step.meta ? (
              <p className="text-caption text-ink-muted">{step.meta}</p>
            ) : null}
          </div>
        </li>
      ))}
    </ol>
  );
}
