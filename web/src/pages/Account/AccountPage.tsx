import { useAuth } from '@/context/AuthContext';
import { Button } from '@/components/ui';
import { UI_COPY } from '@/constants/ui';
import { WORKSPACE_ROUTES } from '@/lib/workspaceRoutes';
import { Link } from 'react-router-dom';

export function AccountPage() {
  const { user, profile, signOut } = useAuth();

  const displayName = profile?.fullName || user?.fullName || user?.email || 'User';
  const organisation =
    profile?.organisationName || profile?.company || UI_COPY.authPersonalOrg;
  const memberships = profile?.memberships ?? [];

  return (
    <div className="mx-auto max-w-2xl space-y-6 animate-fade-in">
      <div>
        <h1 className="text-page-title text-ink">{UI_COPY.accountTitle}</h1>
        <p className="mt-1 text-small text-ink-muted">
          {UI_COPY.accountSubtitle}
        </p>
      </div>

      <section className="rounded-xl border border-surface-border bg-white p-6 shadow-sm">
        <h2 className="text-section text-ink">{UI_COPY.accountProfile}</h2>
        <dl className="mt-4 grid gap-3 text-small sm:grid-cols-2">
          <div>
            <dt className="text-caption text-ink-muted">{UI_COPY.authFullName}</dt>
            <dd className="mt-0.5 text-ink">{displayName}</dd>
          </div>
          <div>
            <dt className="text-caption text-ink-muted">{UI_COPY.authEmail}</dt>
            <dd className="mt-0.5 text-ink">{user?.email ?? '—'}</dd>
          </div>
          <div>
            <dt className="text-caption text-ink-muted">
              {UI_COPY.authOrganisation}
            </dt>
            <dd className="mt-0.5 text-ink">{organisation}</dd>
          </div>
          <div>
            <dt className="text-caption text-ink-muted">{UI_COPY.accountJobTitle}</dt>
            <dd className="mt-0.5 text-ink">{profile?.jobTitle || '—'}</dd>
          </div>
        </dl>
      </section>

      <section className="rounded-xl border border-surface-border bg-white p-6 shadow-sm">
        <h2 className="text-section text-ink">
          {UI_COPY.accountMemberships}
        </h2>
        <p className="mt-1 text-small text-ink-muted">
          {UI_COPY.accountMembershipsHint}
        </p>

        {memberships.length === 0 ? (
          <p className="mt-4 text-small text-ink-muted">
            {UI_COPY.accountNoMemberships}
          </p>
        ) : (
          <ul className="mt-4 divide-y divide-surface-border">
            {memberships.map((m) => (
              <li
                key={m.workspaceId}
                className="flex items-center justify-between gap-3 py-3"
              >
                <div className="min-w-0">
                  <Link
                    to={WORKSPACE_ROUTES.section(m.workspaceId, 'overview')}
                    className="block truncate font-medium text-ink hover:text-brand-600"
                  >
                    {m.workspaceName}
                  </Link>
                  <p className="text-caption capitalize text-ink-muted">
                    {m.role}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <div className="flex justify-end">
        <Button variant="secondary" onClick={() => void signOut()}>
          {UI_COPY.authSignOut}
        </Button>
      </div>
    </div>
  );
}
