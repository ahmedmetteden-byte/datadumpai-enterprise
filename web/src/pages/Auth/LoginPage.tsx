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
  const [showPassword, setShowPassword] = useState(false);

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
          <div className="relative">
            <Input
              type={showPassword ? 'text' : 'password'}
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="pr-11"
            />
            <button
              type="button"
              onClick={() => setShowPassword((prev) => !prev)}
              className="absolute inset-y-0 right-0 flex w-11 items-center justify-center text-ink-faint hover:text-ink-muted focus-visible:outline-none focus-visible:text-ink-muted"
              aria-label={showPassword ? UI_COPY.authHidePassword : UI_COPY.authShowPassword}
              aria-pressed={showPassword}
            >
              {showPassword ? (
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 20 20"
                  fill="none"
                  className="h-5 w-5"
                  aria-hidden="true"
                >
                  <path
                    d="M2.5 10.5C2.5 10.5 5.5 5 10 5s7.5 5.5 7.5 5.5-3 5.5-7.5 5.5-7.5-5.5-7.5-5.5Z"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                  <circle cx="10" cy="10.5" r="2.25" stroke="currentColor" strokeWidth="1.5" />
                  <path d="M3 17 17 3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                </svg>
              ) : (
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 20 20"
                  fill="none"
                  className="h-5 w-5"
                  aria-hidden="true"
                >
                  <path
                    d="M2.5 10.5C2.5 10.5 5.5 5 10 5s7.5 5.5 7.5 5.5-3 5.5-7.5 5.5-7.5-5.5-7.5-5.5Z"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                  <circle cx="10" cy="10.5" r="2.25" stroke="currentColor" strokeWidth="1.5" />
                </svg>
              )}
            </button>
          </div>
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
