import { NavLink } from 'react-router-dom';
import { APP_NAME, PRIMARY_NAV, ROUTES, UI_COPY } from '@/constants/ui';
import { useAuth } from '@/context/AuthContext';
import { cn } from '@/lib/cn';

export function Sidebar({
  open,
  onNavigate,
}: {
  open: boolean;
  onNavigate?: () => void;
}) {
  const { user, profile, signOut } = useAuth();
  const label =
    profile?.fullName || user?.fullName || user?.email?.split('@')[0] || 'User';

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
          <div className="text-lg font-semibold tracking-tight">{APP_NAME}</div>
          <div className="mt-1 text-caption text-white/60">Enterprise</div>
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
                'block rounded-md px-3 py-2.5 text-small transition-colors',
                isActive
                  ? 'bg-sidebar-active text-white'
                  : 'text-white/75 hover:bg-sidebar-hover hover:text-white',
              )
            }
            end={item.href === ROUTES.home}
          >
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-white/10 px-3 py-4">
        <div className="mb-2 truncate px-3 text-caption text-white/50">
          {label}
        </div>
        <NavLink
          to={ROUTES.settings}
          onClick={onNavigate}
          className="block rounded-md px-3 py-2.5 text-small text-white/70 hover:bg-sidebar-hover hover:text-white"
        >
          Settings
        </NavLink>
        <NavLink
          to={ROUTES.account}
          onClick={onNavigate}
          className="block rounded-md px-3 py-2.5 text-small text-white/70 hover:bg-sidebar-hover hover:text-white"
        >
          Account
        </NavLink>
        <button
          type="button"
          onClick={() => {
            onNavigate?.();
            void signOut();
          }}
          className="mt-1 w-full rounded-md px-3 py-2.5 text-left text-small text-white/70 hover:bg-sidebar-hover hover:text-white"
        >
          {UI_COPY.authSignOut}
        </button>
      </div>
    </aside>
  );
}
