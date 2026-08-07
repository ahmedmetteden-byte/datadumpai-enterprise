import { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { InlineRequestStatus } from '@/components/feedback';
import { Modal } from '@/components/ui/Modal';
import { Select } from '@/components/ui/Select';
import { services } from '@/api/services';
import { useAuth } from '@/context/AuthContext';
import { UI_COPY } from '@/constants/ui';
import type { PaymentProvider, Plan } from '@/types/billing';

export function UpgradeModal({
  plan,
  availableProviders,
  onClose,
  onCheckoutStarted,
}: {
  plan: Plan | null;
  availableProviders: PaymentProvider[];
  onClose: () => void;
  onCheckoutStarted: () => void;
}) {
  const { accessToken } = useAuth();
  const [provider, setProvider] = useState<PaymentProvider | ''>(
    availableProviders[0] ?? '',
  );
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!plan) return null;

  async function handleConfirm() {
    if (!plan || !provider) return;
    setSubmitting(true);
    setError(null);
    try {
      const { checkoutUrl } = await services.billing.startCheckout(
        { planId: plan.id, provider },
        { accessToken },
      );
      onCheckoutStarted();
      window.location.href = checkoutUrl;
    } catch (err) {
      setError(err instanceof Error ? err.message : UI_COPY.billingCheckoutError);
      setSubmitting(false);
    }
  }

  return (
    <Modal
      open={Boolean(plan)}
      onClose={onClose}
      title={`${UI_COPY.billingUpgradeButton} — ${plan.label}`}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={submitting}>
            {UI_COPY.destinationCancel}
          </Button>
          <Button
            onClick={() => void handleConfirm()}
            disabled={submitting || !provider}
          >
            {submitting ? UI_COPY.requestLoading : UI_COPY.billingContinue}
          </Button>
        </>
      }
    >
      <p className="mb-4 text-small text-ink-muted">{plan.tagline}</p>

      {availableProviders.length > 1 ? (
        <label className="block">
          <span className="mb-1 block text-caption font-medium text-ink-muted">
            {UI_COPY.billingProviderLabel}
          </span>
          <Select
            value={provider}
            onChange={(event) => setProvider(event.target.value as PaymentProvider)}
            className="w-full"
          >
            <option value="stripe">Stripe (card)</option>
            <option value="paystack">Paystack</option>
          </Select>
        </label>
      ) : null}

      {error ? (
        <InlineRequestStatus className="mt-3" kind="error" message={error} />
      ) : null}
    </Modal>
  );
}
