import { Link } from 'react-router-dom';
import type { ReactNode } from 'react';
import { APP_NAME } from '@/constants/ui';

export function AuthLayout({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: ReactNode;
}) {
  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-canvas px-4 py-10">
      <div
        className="pointer-events-none absolute inset-0 bg-hero-gradient opacity-[0.09]"
        aria-hidden
      />
      <div
        className="pointer-events-none absolute -left-24 top-10 h-72 w-72 rounded-full bg-brand-400/20 blur-3xl"
        aria-hidden
      />
      <div
        className="pointer-events-none absolute -right-16 bottom-0 h-80 w-80 rounded-full bg-accent/15 blur-3xl"
        aria-hidden
      />

      <div className="relative w-full max-w-md animate-slide-up">
        <div className="mb-8 text-center">
          <Link
            to="/auth/login"
            className="inline-flex flex-col items-center focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 rounded-md"
          >
            <span className="text-2xl font-semibold tracking-tight text-ink">
              {APP_NAME}
            </span>
            <span className="mt-1 text-caption text-ink-muted">Enterprise</span>
          </Link>
          <h1 className="mt-6 text-page-title text-ink">{title}</h1>
          <p className="mt-2 text-small text-ink-muted">{subtitle}</p>
        </div>

        <div className="rounded-xl border border-surface-border bg-white p-6 shadow-card sm:p-8">
          {children}
        </div>
      </div>
    </div>
  );
}
