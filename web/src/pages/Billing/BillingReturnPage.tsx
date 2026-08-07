import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { services } from '@/api/services';
import { useAuth } from '@/context/AuthContext';
import { ROUTES, UI_COPY } from '@/constants/ui';
import type { PaymentProvider } from '@/types/billing';

type Status = 'verifying' | 'success' | 'error' | 'canceled';

export function BillingReturnPage() {
  const { accessToken } = useAuth();
  const [searchParams] = useSearchParams();
  const [status, setStatus] = useState<Status>('verifying');
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    const billing = searchParams.get('billing');
    const provider = searchParams.get('provider') as PaymentProvider | null;
    const sessionId = searchParams.get('session_id') ?? undefined;
    const reference = searchParams.get('reference') ?? searchParams.get('trxref') ?? undefined;

    if (billing === 'canceled') {
      setStatus('canceled');
      return;
    }

    if (!provider) {
      setStatus('error');
      return;
    }

    let cancelled = false;
    services.billing
      .completeCheckout({ provider, sessionId, reference }, { accessToken })
      .then(() => {
        if (!cancelled) setStatus('success');
      })
      .catch((err) => {
        if (!cancelled) {
          setStatus('error');
          setMessage(err instanceof Error ? err.message : null);
        }
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams, accessToken]);

  const content = {
    verifying: {
      title: UI_COPY.billingReturnVerifying,
      body: '',
    },
    success: {
      title: UI_COPY.billingReturnSuccessTitle,
      body: UI_COPY.billingReturnSuccessBody,
    },
    error: {
      title: UI_COPY.billingReturnErrorTitle,
      body: message ?? UI_COPY.billingReturnErrorBody,
    },
    canceled: {
      title: UI_COPY.billingReturnCanceledTitle,
      body: UI_COPY.billingReturnCanceledBody,
    },
  }[status];

  return (
    <div className="mx-auto max-w-md space-y-4 py-16 text-center animate-fade-in">
      <h1 className="text-page-title text-ink">{content.title}</h1>
      {content.body ? (
        <p className="text-small text-ink-muted">{content.body}</p>
      ) : null}
      {status !== 'verifying' ? (
        <Link
          to={ROUTES.billing}
          className="inline-flex h-10 items-center justify-center rounded-md bg-brand-500 px-4 text-body font-medium text-white transition-colors hover:bg-brand-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2"
        >
          {UI_COPY.billingReturnBackLink}
        </Link>
      ) : (
        <p className="text-caption text-ink-faint">
          <Link to={ROUTES.billing} className="text-brand-600 hover:underline">
            {UI_COPY.billingReturnBackLink}
          </Link>
        </p>
      )}
    </div>
  );
}
