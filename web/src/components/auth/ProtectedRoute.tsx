import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';
import { ROUTES } from '@/constants/ui';

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-canvas bg-mesh-soft">
        <div className="rounded-xl border border-surface-border bg-white px-6 py-5 text-small text-ink-muted shadow-card animate-fade-in">
          Restoring your session…
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <Navigate
        to={ROUTES.login}
        replace
        state={{ from: location.pathname }}
      />
    );
  }

  return children;
}

export function PublicOnlyRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, loading } = useAuth();
  const location = useLocation();
  const redirectTo =
    (location.state as { from?: string } | null)?.from || ROUTES.home;

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-canvas bg-mesh-soft">
        <div className="rounded-xl border border-surface-border bg-white px-6 py-5 text-small text-ink-muted shadow-card animate-fade-in">
          Checking session…
        </div>
      </div>
    );
  }

  if (isAuthenticated) {
    return <Navigate to={redirectTo} replace />;
  }

  return children;
}
