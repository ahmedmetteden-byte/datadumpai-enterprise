import { useEffect, useRef } from 'react';
import { NavLink } from 'react-router-dom';
import { APP_NAME, PRIMARY_NAV, ROUTES, UI_COPY } from '@/constants/ui';
import { useAuth } from '@/context/AuthContext';
import { useDisclosure } from '@/hooks/useDisclosure';
import { cn } from '@/lib/cn';

export function Sidebar({
  open,
  onNavigate,
}: {
  open: boolean;
  onNavigate?: () => void;
}) {
  const { user, profile, signOut } = useAuth();
  const menu = useDisclosure(false);
  const menuRef = useRef<HTMLDivElement>(null);

  const label =
    profile?.fullName || user?.fullName || user?.email?.split('@')[0] || 'User';
  const initial = label.trim().charAt(0).toUpperCase() || 'U';
  const organisation =
    profile?.organisationName || profile?.company || UI_COPY.authPersonalOrg;

  useEffect(() => {
    if (!menu.isOpen) return;
    function onPointerDown(event: MouseEvent) {
      if (!menuRef.current?.contains(event.target as Node)) {
        menu.close();
      }
    }
    document.addEventListener('mousedown', onPointerDown);
    return () => document.removeEventListener('mousedown', onPointerDown);
  }, [menu]);

  return (
    <aside
      className={cn(
        'fixed inset-y-0 left-0 z-40 flex w-64 flex-col bg-sidebar text-white transition-transform duration-300',
        'lg:static lg:translate-x-0',
        open ? 'translate-x-0' : '-translate-x-full',
      )}
      aria-label="Primary"
    >
      <div className="px-5 pb-6 pt-7">
        <NavLink
          to={ROUTES.home}
          onClick={onNavigate}
          className="block focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/60 rounded-md"
        >
          <div className="flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-500 text-sm font-bold text-white">
              D
            </span>
            <div>
              <div className="text-lg font-semibold tracking-tight">
                {APP_NAME}
              </div>
              <div className="text-caption text-white/50">Enterprise</div>
            </div>
          </div>
        </NavLink>
      </div>

      <nav className="flex-1 space-y-1 px-3">
        {PRIMARY_NAV.map((item) => (
          <NavLink
            key={item.id}
            to={item.href}
            onClick={onNavigate}
            className={({ isActive }) =>
              cn(
                'block rounded-md border-l-2 px-3 py-2.5 text-small font-medium transition-colors',
                isActive
                  ? 'border-accent bg-white/10 text-white'
                  : 'border-transparent text-white/70 hover:bg-sidebar-hover hover:text-white',
              )
            }
            end={item.href === ROUTES.home}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div ref={menuRef} className="relative border-t border-white/10 px-3 py-3">
        {menu.isOpen ? (
          <div className="absolute bottom-full left-3 right-3 mb-2 rounded-lg border border-white/10 bg-sidebar-hover p-3 shadow-float animate-fade-in">
            <p className="truncate text-small font-medium text-white">{label}</p>
            <p className="truncate text-caption text-white/50">
              {user?.email}
            </p>
            <p className="mt-1 truncate text-caption text-white/40">
              {organisation}
            </p>
            <button
              type="button"
              onClick={() => {
                menu.close();
                onNavigate?.();
                void signOut();
              }}
              className="mt-3 w-full rounded-md bg-white/10 px-3 py-2 text-left text-small text-white transition-colors hover:bg-white/20"
            >
              {UI_COPY.authSignOut}
            </button>
          </div>
        ) : null}

        <button
          type="button"
          onClick={menu.toggle}
          aria-expanded={menu.isOpen}
          className="flex w-full items-center gap-2.5 rounded-md px-2 py-2 text-left transition-colors hover:bg-sidebar-hover"
        >
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white/15 text-small font-semibold text-white">
            {initial}
          </span>
          <span className="min-w-0 flex-1">
            <span className="block truncate text-small font-medium text-white">
              {label}
            </span>
            <span className="block truncate text-caption text-white/45">
              {organisation}
            </span>
          </span>
          <span aria-hidden className="text-white/40">
            {menu.isOpen ? '▾' : '▴'}
          </span>
        </button>
      </div>
    </aside>
  );
}
