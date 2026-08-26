import { useEffect, useRef, useState, type ChangeEvent } from 'react';
import { useAuth } from '@/context/AuthContext';
import { useBilling } from '@/hooks/useBilling';
import { services } from '@/api/services';
import { Button } from '@/components/ui';
import { ROUTES, UI_COPY } from '@/constants/ui';
import { WORKSPACE_ROUTES } from '@/lib/workspaceRoutes';
import { Link } from 'react-router-dom';
import type { BrandingLogo } from '@/types/auth';

export function AccountPage() {
  const { user, profile, accessToken, refreshProfile, signOut } = useAuth();
  const { data: billing } = useBilling();

  const displayName = profile?.fullName || user?.fullName || user?.email || 'User';
  const organisation =
    profile?.organisationName || profile?.company || UI_COPY.authPersonalOrg;
  const memberships = profile?.memberships ?? [];

  const canUseBranding =
    billing?.effectivePlan === 'professional' || billing?.effectivePlan === 'enterprise';

  const [logo, setLogo] = useState<BrandingLogo | null>(null);
  const [logoBusy, setLogoBusy] = useState(false);
  const [logoError, setLogoError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!profile?.hasBrandingLogo) {
      setLogo(null);
      return;
    }
    let cancelled = false;
    services.branding
      .getLogo({ accessToken })
      .then((result) => {
        if (!cancelled) setLogo(result);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [profile?.hasBrandingLogo, accessToken]);

  async function handleLogoSelected(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;

    setLogoBusy(true);
    setLogoError(null);
    try {
      const result = await services.branding.uploadLogo(file, { accessToken });
      setLogo(result);
      await refreshProfile();
    } catch (err) {
      setLogoError(err instanceof Error ? err.message : 'Failed to upload logo.');
    } finally {
      setLogoBusy(false);
    }
  }

  async function handleLogoRemove() {
    setLogoBusy(true);
    setLogoError(null);
    try {
      const result = await services.branding.removeLogo({ accessToken });
      setLogo(result);
      await refreshProfile();
    } catch (err) {
      setLogoError(err instanceof Error ? err.message : 'Failed to remove logo.');
    } finally {
      setLogoBusy(false);
    }
  }

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

      <section className="rounded-xl border border-surface-border bg-white p-6 shadow-sm">
        <h2 className="text-section text-ink">Report branding</h2>
        <p className="mt-1 text-small text-ink-muted">
          Upload your logo to replace the DataDumpAI mark on exported PDF, Word, and
          PowerPoint reports.
        </p>

        {!canUseBranding ? (
          <p className="mt-4 text-small text-ink-muted">
            Branded reports require the Professional plan or higher.{' '}
            <Link to={ROUTES.billing} className="text-brand-600 hover:underline">
              Upgrade to unlock this
            </Link>
            .
          </p>
        ) : (
          <div className="mt-4 flex items-center gap-4">
            {logo?.hasLogo && logo.dataUrl ? (
              <img
                src={logo.dataUrl}
                alt="Report logo"
                className="h-16 w-16 rounded border border-surface-border object-contain p-1"
              />
            ) : (
              <div className="flex h-16 w-16 items-center justify-center rounded border border-dashed border-surface-border text-caption text-ink-muted">
                No logo
              </div>
            )}
            <div className="flex gap-2">
              <Button
                variant="secondary"
                size="sm"
                disabled={logoBusy}
                onClick={() => fileInputRef.current?.click()}
              >
                {logo?.hasLogo ? 'Replace logo' : 'Upload logo'}
              </Button>
              {logo?.hasLogo && (
                <Button
                  variant="ghost"
                  size="sm"
                  disabled={logoBusy}
                  onClick={() => void handleLogoRemove()}
                >
                  Remove
                </Button>
              )}
            </div>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/png,image/jpeg,image/svg+xml"
              className="hidden"
              onChange={(event) => void handleLogoSelected(event)}
            />
          </div>
        )}
        {logoError && <p className="mt-2 text-caption text-danger">{logoError}</p>}
      </section>

      <div className="flex justify-end">
        <Button variant="secondary" onClick={() => void signOut()}>
          {UI_COPY.authSignOut}
        </Button>
      </div>
    </div>
  );
}
