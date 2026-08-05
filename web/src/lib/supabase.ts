import { createClient, type SupabaseClient } from '@supabase/supabase-js';

let client: SupabaseClient | null | undefined;
let configLogged = false;

const PLACEHOLDER_URL = 'your-project';
const PLACEHOLDER_KEY = 'your-supabase';

function readUrl(): string {
  return (import.meta.env.VITE_SUPABASE_URL ?? '').trim();
}

function readAnonKey(): string {
  return (import.meta.env.VITE_SUPABASE_ANON_KEY ?? '').trim();
}

function readApiBaseUrl(): string {
  return (import.meta.env.VITE_API_BASE_URL ?? '').trim();
}

function isPlaceholder(url: string, key: string): boolean {
  return url.includes(PLACEHOLDER_URL) || key.includes(PLACEHOLDER_KEY);
}

/** True when browser Supabase env vars are present and not placeholders. */
export function isSupabaseConfigured(): boolean {
  const url = readUrl();
  const key = readAnonKey();
  return Boolean(url && key && !isPlaceholder(url, key));
}

/**
 * Actionable message when Vite cannot see Supabase env vars.
 * Root `.env` is invisible to the React app — values must be in `web/.env`
 * (or passed as Docker build-args).
 */
export function getSupabaseConfigErrorMessage(): string {
  return [
    'Supabase configuration missing.',
    '',
    'React expects:',
    '  VITE_SUPABASE_URL',
    '  VITE_SUPABASE_ANON_KEY',
    '',
    'These must be defined in web/.env (or injected during Docker build).',
    'The repository root .env is not visible to Vite.',
    '',
    'Copy web/.env.example → web/.env, fill the values, then restart Vite',
    '(or rebuild the frontend Docker image).',
  ].join('\n');
}

/**
 * DEV-only startup check — never prints secrets.
 * Call once from main.tsx.
 */
export function logFrontendConfiguration(): void {
  if (!import.meta.env.DEV || configLogged) return;
  configLogged = true;

  const url = readUrl();
  const key = readAnonKey();
  const apiBase = readApiBaseUrl();
  const urlOk = Boolean(url) && !url.includes(PLACEHOLDER_URL);
  const keyOk = Boolean(key) && !key.includes(PLACEHOLDER_KEY);

  console.log('========== Frontend configuration ==========');
  console.log({
    'Supabase URL': urlOk ? 'configured' : 'missing',
    'Anon key': keyOk ? 'configured' : 'missing',
    'API base URL': apiBase || '(empty — same-origin / Vite proxy)',
    'Env file hint': 'web/.env (not repository root .env)',
  });
  if (!urlOk || !keyOk) {
    console.warn(getSupabaseConfigErrorMessage());
  }
}

/**
 * Lazy singleton. Returns null when env is missing (local mock auth only).
 * Production builds always use SupabaseAuthService — configure VITE_SUPABASE_*.
 */
export function getSupabaseClient(): SupabaseClient | null {
  if (client !== undefined) {
    return client;
  }

  if (!isSupabaseConfigured()) {
    client = null;
    return client;
  }

  client = createClient(readUrl(), readAnonKey(), {
    auth: {
      persistSession: true,
      autoRefreshToken: true,
      detectSessionInUrl: true,
      storage: localStorage,
    },
  });

  return client;
}
