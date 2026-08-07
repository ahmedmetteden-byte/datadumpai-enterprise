import { apiRequest } from '@/api/client';
import { mockLatency, type ServiceAuth } from '@/api/config';
import type { BillingService } from '@/api/services/contracts';
import type {
  BillingSummary,
  CompleteCheckoutInput,
  Plan,
  StartCheckoutInput,
} from '@/types/billing';

export class HttpBillingService implements BillingService {
  async listPlans(auth?: ServiceAuth): Promise<Plan[]> {
    return apiRequest<Plan[]>('/api/v1/billing/plans', {
      token: auth?.accessToken,
    });
  }

  async getSummary(auth?: ServiceAuth): Promise<BillingSummary> {
    return apiRequest<BillingSummary>('/api/v1/billing/summary', {
      token: auth?.accessToken,
    });
  }

  async startCheckout(
    input: StartCheckoutInput,
    auth?: ServiceAuth,
  ): Promise<{ checkoutUrl: string }> {
    return apiRequest<{ checkoutUrl: string }>('/api/v1/billing/checkout', {
      method: 'POST',
      body: input,
      token: auth?.accessToken,
    });
  }

  async completeCheckout(
    input: CompleteCheckoutInput,
    auth?: ServiceAuth,
  ): Promise<BillingSummary> {
    return apiRequest<BillingSummary>('/api/v1/billing/checkout/complete', {
      method: 'POST',
      body: input,
      token: auth?.accessToken,
    });
  }

  async openPortal(auth?: ServiceAuth): Promise<{ portalUrl: string }> {
    return apiRequest<{ portalUrl: string }>('/api/v1/billing/portal', {
      method: 'POST',
      token: auth?.accessToken,
    });
  }

  async cancelAtPeriodEnd(auth?: ServiceAuth): Promise<BillingSummary> {
    return apiRequest<BillingSummary>('/api/v1/billing/cancel', {
      method: 'POST',
      token: auth?.accessToken,
    });
  }
}

const MOCK_PLANS: Plan[] = [
  {
    id: 'free',
    label: 'Free',
    priceLabel: '$0',
    tagline: 'Try the platform without replacing your existing workflow.',
    idealFor: 'Individuals trying the platform.',
    reportsPerMonth: 5,
    uploadsPerMonth: 10,
    projectsMax: 3,
    includes: ['Up to 3 projects', '10 uploads/mo', '5 reports/mo'],
    billable: false,
  },
  {
    id: 'starter',
    label: 'Starter',
    priceLabel: '~$15/mo',
    tagline: 'Everything you need for regular reporting.',
    idealFor: 'Solo operators, analysts, and team leads.',
    reportsPerMonth: 100,
    uploadsPerMonth: 100,
    projectsMax: null,
    includes: ['Unlimited projects', '100 uploads/mo', '100 reports/mo'],
    billable: true,
  },
  {
    id: 'professional',
    label: 'Professional',
    priceLabel: '~$39/mo',
    tagline: 'Move from an assistant to an analyst.',
    idealFor: 'Consultants, managers, and research teams.',
    reportsPerMonth: null,
    uploadsPerMonth: null,
    projectsMax: null,
    includes: ['Unlimited everything', 'Cross-document intelligence', 'Live web research'],
    billable: true,
  },
  {
    id: 'enterprise',
    label: 'Enterprise',
    priceLabel: 'Custom',
    tagline: 'Security, scale, and control for large teams.',
    idealFor: 'Organizations with compliance and deployment needs.',
    reportsPerMonth: null,
    uploadsPerMonth: null,
    projectsMax: null,
    includes: ['SSO', 'Admin dashboard', 'API access'],
    billable: false,
  },
];

export class MockBillingService implements BillingService {
  async listPlans(_auth?: ServiceAuth): Promise<Plan[]> {
    await mockLatency(80);
    return MOCK_PLANS;
  }

  async getSummary(_auth?: ServiceAuth): Promise<BillingSummary> {
    await mockLatency(100);
    return {
      enabled: false,
      availableProviders: [],
      billingPlan: 'free',
      effectivePlan: 'free',
      subscriptionStatus: 'none',
      paymentProvider: null,
      cancelAtPeriodEnd: false,
      currentPeriodEnd: null,
      trialDaysRemaining: null,
      usage: {
        reportsUsed: 0,
        reportsLimit: 5,
        uploadsUsed: 0,
        uploadsLimit: 10,
        projectsMax: 3,
      },
    };
  }

  async startCheckout(
    _input: StartCheckoutInput,
    _auth?: ServiceAuth,
  ): Promise<{ checkoutUrl: string }> {
    await mockLatency(80);
    throw new Error('Billing is not configured in this demo.');
  }

  async completeCheckout(
    _input: CompleteCheckoutInput,
    _auth?: ServiceAuth,
  ): Promise<BillingSummary> {
    return this.getSummary(_auth);
  }

  async openPortal(_auth?: ServiceAuth): Promise<{ portalUrl: string }> {
    await mockLatency(80);
    throw new Error('Billing is not configured in this demo.');
  }

  async cancelAtPeriodEnd(_auth?: ServiceAuth): Promise<BillingSummary> {
    return this.getSummary(_auth);
  }
}
