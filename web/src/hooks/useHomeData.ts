import { useEffect, useState } from 'react';
import { services } from '@/api/services';
import { useAuth } from '@/context/AuthContext';
import type { HomePageData } from '@/types/home';

interface HomeDataState {
  data: HomePageData | null;
  loading: boolean;
  error: string | null;
  reload: () => void;
}

export function useHomeData(workspaceId?: string): HomeDataState {
  const { accessToken } = useAuth();
  const [data, setData] = useState<HomePageData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const result = await services.home.getHome(workspaceId, {
          accessToken,
        });
        if (!cancelled) {
          setData(result);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load Home');
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
  }, [workspaceId, tick, accessToken]);

  return {
    data,
    loading,
    error,
    reload: () => setTick((value) => value + 1),
  };
}
