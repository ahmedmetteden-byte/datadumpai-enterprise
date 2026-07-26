import { createClient, type SupabaseClient } from '@supabase/supabase-js';

let client: SupabaseClient | null | undefined;

/** True when browser Supabase env vars are present. */
export function isSupabaseConfigured(): boolean {
  const url = import.meta.env.VITE_SUPABASE_URL?.trim();
  const key = import.meta.env.VITE_SUPABASE_ANON_KEY?.trim();
  return Boolean(
    url &&
      key &&
      !url.includes('your-project') &&
      !key.includes('your-supabase'),
  );
}

/**
 * Lazy singleton. Returns null when env is missing so mock auth can run locally.
 */
export function getSupabaseClient(): SupabaseClient | null {
  if (client !== undefined) {
    return client;
  }

  if (!isSupabaseConfigured()) {
    client = null;
    return client;
  }

  client = createClient(
    import.meta.env.VITE_SUPABASE_URL.trim(),
    import.meta.env.VITE_SUPABASE_ANON_KEY.trim(),
    {
      auth: {
        persistSession: true,
        autoRefreshToken: true,
        detectSessionInUrl: true,
        storage: localStorage,
      },
    },
  );

  return client;
}
