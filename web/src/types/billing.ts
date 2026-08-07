export type PlanId = 'free' | 'starter' | 'professional' | 'enterprise';

export type PaymentProvider = 'stripe' | 'paystack';

export interface Plan {
  id: PlanId;
  label: string;
  priceLabel: string;
  tagline: string;
  idealFor: string;
  reportsPerMonth: number | null;
  uploadsPerMonth: number | null;
  projectsMax: number | null;
  includes: string[];
  billable: boolean;
}

export interface UsageSnapshot {
  reportsUsed: number;
  reportsLimit: number | null;
  uploadsUsed: number;
  uploadsLimit: number | null;
  projectsMax: number | null;
}

export interface BillingSummary {
  enabled: boolean;
  availableProviders: PaymentProvider[];
  billingPlan: PlanId;
  effectivePlan: PlanId;
  subscriptionStatus: string;
  paymentProvider: PaymentProvider | null;
  cancelAtPeriodEnd: boolean;
  currentPeriodEnd: string | null;
  trialDaysRemaining: number | null;
  usage: UsageSnapshot;
}

export interface StartCheckoutInput {
  planId: PlanId;
  provider: PaymentProvider;
}

export interface CompleteCheckoutInput {
  provider: PaymentProvider;
  sessionId?: string;
  reference?: string;
}
