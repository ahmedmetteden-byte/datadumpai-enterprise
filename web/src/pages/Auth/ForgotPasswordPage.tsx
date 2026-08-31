import { type FormEvent, useState } from 'react';
import { Link } from 'react-router-dom';
import { InlineRequestStatus } from '@/components/feedback';
import { Button, Input } from '@/components/ui';
import { useAuth } from '@/context/AuthContext';
import { AuthError } from '@/api/services/AuthService';
import { ROUTES, UI_COPY } from '@/constants/ui';
import { AuthLayout } from '@/pages/Auth/AuthLayout';

export function ForgotPasswordPage() {
  const { sendPasswordReset } = useAuth();
  const [email, setEmail] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await sendPasswordReset({ email });
      setSent(true);
    } catch (err) {
      setError(
        err instanceof AuthError
          ? err.message
          : err instanceof Error
            ? err.message
            : UI_COPY.authResetError,
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthLayout
      title={UI_COPY.authForgotTitle}
      subtitle={UI_COPY.authForgotSubtitle}
    >
      {sent ? (
        <div className="space-y-4">
          <p className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-small text-success" role="status">
            {UI_COPY.authResetSent}
          </p>
          <Link
            to={ROUTES.login}
            className="inline-flex h-10 w-full items-center justify-center rounded-md bg-brand-500 text-body font-medium text-white hover:bg-brand-600"
          >
            {UI_COPY.authBackToSignIn}
          </Link>
        </div>
      ) : (
        <form id="forgot-form" className="space-y-4" onSubmit={onSubmit} noValidate>
          <label className="block space-y-1.5">
            <span className="text-caption text-ink-muted">
              {UI_COPY.authEmail}
            </span>
            <Input
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
            />
          </label>

          {submitting ? (
            <InlineRequestStatus
              kind="loading"
              message={UI_COPY.authSendingReset}
            />
          ) : null}
          {error ? (
            <InlineRequestStatus
              kind="error"
              message={error}
              onRetry={() => {
                const form = document.getElementById('forgot-form') as
                  | HTMLFormElement
                  | null;
                form?.requestSubmit();
              }}
            />
          ) : null}

          <Button type="submit" className="w-full" disabled={submitting}>
            {submitting ? UI_COPY.authSendingReset : UI_COPY.authSendReset}
          </Button>
        </form>
      )}

      {!sent ? (
        <p className="mt-6 text-center text-small text-ink-muted">
          <Link
            to={ROUTES.login}
            className="font-medium text-brand-600 hover:text-brand-700"
          >
            {UI_COPY.authBackToSignIn}
          </Link>
        </p>
      ) : null}
    </AuthLayout>
  );
}
