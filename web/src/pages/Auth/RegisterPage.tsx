import { type FormEvent, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { InlineRequestStatus } from '@/components/feedback';
import { Button, Input } from '@/components/ui';
import { useAuth } from '@/context/AuthContext';
import { AuthError } from '@/api/services/AuthService';
import { ROUTES, UI_COPY } from '@/constants/ui';
import { AuthLayout } from '@/pages/Auth/AuthLayout';

export function RegisterPage() {
  const { signUp } = useAuth();
  const navigate = useNavigate();

  const [fullName, setFullName] = useState('');
  const [company, setCompany] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setInfo(null);

    if (password !== confirmPassword) {
      setError(UI_COPY.authPasswordMismatch);
      return;
    }
    if (password.length < 8) {
      setError(UI_COPY.authPasswordTooShort);
      return;
    }

    setSubmitting(true);
    try {
      const result = await signUp({ email, password, fullName, company });
      if (result === 'verify_email') {
        setInfo(UI_COPY.authVerifyEmail);
        return;
      }
      navigate(ROUTES.home, { replace: true });
    } catch (err) {
      setError(
        err instanceof AuthError
          ? err.message
          : err instanceof Error
            ? err.message
            : UI_COPY.authSignUpError,
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthLayout
      title={UI_COPY.authSignUpTitle}
      subtitle={UI_COPY.authSignUpSubtitle}
    >
      <form id="register-form" className="space-y-4" onSubmit={onSubmit} noValidate>
        <label className="block space-y-1.5">
          <span className="text-caption text-ink-muted">
            {UI_COPY.authFullName}
          </span>
          <Input
            type="text"
            autoComplete="name"
            required
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            placeholder="Ada Lovelace"
          />
        </label>

        <label className="block space-y-1.5">
          <span className="text-caption text-ink-muted">
            {UI_COPY.authOrganisation}
          </span>
          <Input
            type="text"
            autoComplete="organization"
            value={company}
            onChange={(e) => setCompany(e.target.value)}
            placeholder="Acme Corp"
          />
        </label>

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
            autoComplete="new-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="At least 8 characters"
          />
        </label>

        <label className="block space-y-1.5">
          <span className="text-caption text-ink-muted">
            {UI_COPY.authConfirmPassword}
          </span>
          <Input
            type="password"
            autoComplete="new-password"
            required
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            placeholder="Repeat password"
          />
        </label>

        {submitting ? (
          <InlineRequestStatus
            kind="loading"
            message={UI_COPY.authCreatingAccount}
          />
        ) : null}
        {error ? (
          <InlineRequestStatus
            kind="error"
            message={error}
            onRetry={() => {
              const form = document.getElementById('register-form') as
                | HTMLFormElement
                | null;
              form?.requestSubmit();
            }}
          />
        ) : null}

        {info ? (
          <InlineRequestStatus kind="success" message={info} />
        ) : null}

        <Button type="submit" className="w-full" disabled={submitting}>
          {submitting ? UI_COPY.authCreatingAccount : UI_COPY.authCreateAccount}
        </Button>
      </form>

      <p className="mt-6 text-center text-small text-ink-muted">
        {UI_COPY.authHaveAccount}{' '}
        <Link
          to={ROUTES.login}
          className="font-medium text-brand-600 hover:text-brand-700"
        >
          {UI_COPY.authSignIn}
        </Link>
      </p>
    </AuthLayout>
  );
}
