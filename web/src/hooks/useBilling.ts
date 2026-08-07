import { useEffect, useState } from 'react';
import { services } from '@/api/services';
import { useAuth } from '@/context/AuthContext';
import type { BillingSummary, Plan } from '@/types/billing';

interface BillingState {
  data: BillingSummary | null;
  plans: Plan[];
  loading: boolean;
  error: string | null;
  reload: () => void;
}

export function useBilling(): BillingState {
  const { accessToken } = useAuth();
  const [data, setData] = useState<BillingSummary | null>(null);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const auth = { accessToken };
        const [summary, planList] = await Promise.all([
          services.billing.getSummary(auth),
          services.billing.listPlans(auth),
        ]);
        if (!cancelled) {
          setData(summary);
          setPlans(planList);
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error ? err.message : 'Failed to load billing information',
          );
          setData(null);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [tick, accessToken]);

  return {
    data,
    plans,
    loading,
    error,
    reload: () => setTick((value) => value + 1),
  };
}
