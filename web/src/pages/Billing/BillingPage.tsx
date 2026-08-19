import { useState } from 'react';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { EmptyState } from '@/components/ui/EmptyState';
import { ProgressRing } from '@/components/ui/ProgressRing';
import { useAuth } from '@/context/AuthContext';
import { useRequestFeedback } from '@/context/RequestFeedbackContext';
import { useBilling } from '@/hooks/useBilling';
import { services } from '@/api/services';
import { UI_COPY } from '@/constants/ui';
import { UpgradeModal } from '@/pages/Billing/UpgradeModal';
import type { Plan } from '@/types/billing';

function usagePercent(used: number, limit: number | null): number {
  if (limit === null || limit === 0) return 0;
  return Math.min(100, Math.round((used / limit) * 100));
}

const STATUS_TONE: Record<string, 'neutral' | 'brand' | 'success' | 'warning'> = {
  active: 'success',
  trialing: 'brand',
  past_due: 'warning',
  canceled: 'warning',
  expired: 'neutral',
  none: 'neutral',
};

export function BillingPage() {
  const { accessToken } = useAuth();
  const feedback = useRequestFeedback();
  const { data, plans, loading, error, reload } = useBilling();
  const [upgradePlan, setUpgradePlan] = useState<Plan | null>(null);

  if (loading) {
    return (
      <div className="mx-auto max-w-3xl space-y-6 animate-fade-in">
        <div>
          <h1 className="text-page-title text-ink">{UI_COPY.billingTitle}</h1>
          <p className="mt-1 text-small text-ink-muted">{UI_COPY.billingSubtitle}</p>
        </div>
        <div className="h-40 animate-pulse rounded-xl border border-surface-border bg-surface-alt" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="mx-auto max-w-3xl animate-fade-in">
        <EmptyState
          title={UI_COPY.billingTitle}
          description={error ?? UI_COPY.billingNotConfiguredBody}
        />
      </div>
    );
  }

  const currentPlan = plans.find((plan) => plan.id === data.effectivePlan);
  const billablePlans = plans.filter((plan) => plan.billable);

  async function handleCancel() {
    if (!window.confirm(UI_COPY.billingCancelConfirm)) return;
    await feedback
      .run(() => services.billing.cancelAtPeriodEnd({ accessToken }), {
        loading: UI_COPY.requestLoading,
        success: UI_COPY.billingCancelSuccess,
        error: UI_COPY.billingCancelError,
      })
      .then(reload)
      .catch(() => {
        /* Error toast includes Retry */
      });
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6 animate-fade-in">
      <div>
        <h1 className="text-page-title text-ink">{UI_COPY.billingTitle}</h1>
        <p className="mt-1 text-small text-ink-muted">{UI_COPY.billingSubtitle}</p>
      </div>

      {!data.enabled ? (
        <EmptyState
          title={UI_COPY.billingNotConfiguredTitle}
          description={UI_COPY.billingNotConfiguredBody}
        />
      ) : null}

      <section className="rounded-xl border border-surface-border bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-section text-ink">{UI_COPY.billingCurrentPlan}</h2>
          <Badge tone={STATUS_TONE[data.subscriptionStatus] ?? 'neutral'}>
            {data.subscriptionStatus}
          </Badge>
        </div>
        <p className="mt-2 text-body font-medium text-ink">
          {currentPlan?.label ?? data.effectivePlan}
        </p>
        {data.trialDaysRemaining !== null ? (
          <p className="mt-1 text-small text-ink-muted">
            {data.trialDaysRemaining} {UI_COPY.billingTrialBannerPrefix}{' '}
            {currentPlan?.label ?? data.effectivePlan}{' '}
            {UI_COPY.billingTrialBannerSuffix}
          </p>
        ) : null}

        <h3 className="mt-6 text-caption font-semibold uppercase tracking-wide text-ink-faint">
          {UI_COPY.billingUsageTitle}
        </h3>
        <div className="mt-3 grid gap-6 sm:grid-cols-2">
          <div className="flex items-center gap-4">
            <ProgressRing
              value={usagePercent(data.usage.reportsUsed, data.usage.reportsLimit)}
              size={56}
              strokeWidth={5}
            />
            <div>
              <p className="text-small font-medium text-ink">
                {UI_COPY.billingReportsUsed}
              </p>
              <p className="text-caption text-ink-muted">
                {data.usage.reportsUsed} /{' '}
                {data.usage.reportsLimit ?? UI_COPY.billingUnlimited}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <ProgressRing
              value={usagePercent(data.usage.uploadsUsed, data.usage.uploadsLimit)}
              size={56}
              strokeWidth={5}
            />
            <div>
              <p className="text-small font-medium text-ink">
                {UI_COPY.billingUploadsUsed}
              </p>
              <p className="text-caption text-ink-muted">
                {data.usage.uploadsUsed} /{' '}
                {data.usage.uploadsLimit ?? UI_COPY.billingUnlimited}
              </p>
            </div>
          </div>
        </div>
      </section>

      {data.enabled ? (
        <section>
          <h2 className="text-section text-ink">{UI_COPY.billingUpgradeTitle}</h2>
          <div className="mt-3 grid gap-4 sm:grid-cols-2">
            {billablePlans.map((plan) => (
              <div
                key={plan.id}
                className="flex flex-col rounded-xl border border-surface-border bg-white p-5 shadow-sm"
              >
                <h3 className="text-body font-semibold text-ink">{plan.label}</h3>
                <p className="mt-1 text-small text-ink-muted">{plan.priceLabel}</p>
                <p className="mt-2 text-caption text-ink-muted">{plan.tagline}</p>
                <Button
                  className="mt-4"
                  disabled={plan.id === data.effectivePlan}
                  onClick={() => setUpgradePlan(plan)}
                >
                  {plan.id === data.effectivePlan
                    ? UI_COPY.billingCurrentPlan
                    : UI_COPY.billingUpgradeButton}
                </Button>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      {data.paymentProvider ? (
        <section className="rounded-xl border border-surface-border bg-white p-6 shadow-sm">
          <h2 className="text-section text-ink">{UI_COPY.billingManageTitle}</h2>
          <div className="mt-4 flex flex-wrap gap-3">
            {!data.cancelAtPeriodEnd ? (
              <Button variant="ghost" onClick={() => void handleCancel()}>
                {UI_COPY.billingCancelButton}
              </Button>
            ) : null}
          </div>
        </section>
      ) : null}

      <UpgradeModal
        plan={upgradePlan}
        availableProviders={data.availableProviders}
        onClose={() => setUpgradePlan(null)}
        onCheckoutStarted={reload}
      />
    </div>
  );
}
