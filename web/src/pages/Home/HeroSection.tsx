import { Link } from 'react-router-dom';
import { IconButton } from '@/components/ui/IconButton';
import { ROUTES, UI_COPY } from '@/constants/ui';
import { cn } from '@/lib/cn';
import type { NotificationItem } from '@/types/api';

export function HeroSection({
  greeting,
  unreadCount,
  notifications,
}: {
  greeting: string;
  unreadCount: number;
  notifications: NotificationItem[];
}) {
  return (
    <header className="animate-slide-up rounded-xl bg-hero-gradient p-6 text-white shadow-card sm:p-8">
      <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
        <div className="min-w-0">
          <p className="text-caption uppercase tracking-[0.14em] text-white/70">
            {UI_COPY.homeCrumb}
          </p>
          <h1 className="mt-2 text-hero text-white">{greeting}</h1>
          <p className="mt-2 max-w-xl text-small text-white/85">
            {UI_COPY.heroSupport}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
          <div className="relative">
            <IconButton
              tone="onDark"
              label={UI_COPY.notifications}
              aria-describedby={
                unreadCount > 0 ? 'notification-count' : undefined
              }
            >
              <span aria-hidden>🔔</span>
              {unreadCount > 0 ? (
                <span
                  id="notification-count"
                  className="absolute right-1.5 top-1.5 inline-flex h-4 min-w-4 items-center justify-center rounded-full bg-white px-1 text-[10px] font-semibold text-brand-600"
                >
                  {unreadCount}
                </span>
              ) : null}
            </IconButton>
            <span className="sr-only">
              {notifications
                .filter((item) => !item.read)
                .map((item) => item.message)
                .join('. ')}
            </span>
          </div>

          <Link
            to={ROUTES.reportsNew}
            className={cn(
              'inline-flex h-10 items-center justify-center rounded-md bg-white px-4 text-body font-medium text-brand-700',
              'transition-colors hover:bg-brand-50',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-brand-600',
            )}
          >
            {UI_COPY.createReport}
          </Link>
        </div>
      </div>
    </header>
  );
}
