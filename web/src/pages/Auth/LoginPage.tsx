import { type FormEvent, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { InlineRequestStatus } from '@/components/feedback';
import { Button, Input } from '@/components/ui';
import { useAuth } from '@/context/AuthContext';
import { AuthError } from '@/api/services/AuthService';
import { ROUTES, UI_COPY } from '@/constants/ui';
import { AuthLayout } from '@/pages/Auth/AuthLayout';

export function LoginPage() {
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from =
    (location.state as { from?: string } | null)?.from || ROUTES.home;

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await signIn({ email, password });
      navigate(from, { replace: true });
    } catch (err) {
      setError(
        err instanceof AuthError
          ? err.message
          : err instanceof Error
            ? err.message
            : UI_COPY.authSignInError,
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthLayout title={UI_COPY.authSignInTitle} subtitle={UI_COPY.authSignInSubtitle}>
      <form id="login-form" className="space-y-4" onSubmit={onSubmit} noValidate>
        <label className="block space-y-1.5">
          <span className="text-caption text-ink-muted">{UI_COPY.authEmail}</span>
          <Input
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@company.com"
          />
        </label>

        <label className="block space-y-1.5">
          <span className="text-caption text-ink-muted">
            {UI_COPY.authPassword}
          </span>
          <Input
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
          />
        </label>

        <div className="flex justify-end">
          <Link
            to={ROUTES.forgotPassword}
            className="text-small text-brand-600 hover:text-brand-700"
          >
            {UI_COPY.authForgotPasswordLink}
          </Link>
        </div>

        {submitting ? (
          <InlineRequestStatus kind="loading" message={UI_COPY.authSigningIn} />
        ) : null}
        {error ? (
          <InlineRequestStatus
            kind="error"
            message={error}
            onRetry={() => {
              const form = document.getElementById('login-form') as
                | HTMLFormElement
                | null;
              form?.requestSubmit();
            }}
          />
        ) : null}

        <Button type="submit" className="w-full" disabled={submitting}>
          {submitting ? UI_COPY.authSigningIn : UI_COPY.authSignIn}
        </Button>
      </form>

      <p className="mt-6 text-center text-small text-ink-muted">
        {UI_COPY.authNoAccount}{' '}
        <Link
          to={ROUTES.register}
          className="font-medium text-brand-600 hover:text-brand-700"
        >
          {UI_COPY.authCreateAccount}
        </Link>
      </p>
    </AuthLayout>
  );
}
