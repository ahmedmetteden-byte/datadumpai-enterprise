/**
 * Temporary auth / API diagnostics for diagnosing redirect loops.
 * All helpers no-op outside DEV builds.
 */

import type { AuthSession } from '@/types/auth';

export function isAuthDebugEnabled(): boolean {
  return import.meta.env.DEV === true;
}

function tokenPrefix(token?: string | null): string | null {
  if (!token) return null;
  return token.slice(0, 20);
}

export function summarizeSession(session: AuthSession | null | undefined) {
  return {
    hasSession: Boolean(session),
    hasAccessToken: Boolean(session?.accessToken),
    tokenPrefix: tokenPrefix(session?.accessToken),
    expiresAt: session?.expiresAt ?? null,
    userId: session?.user?.id ?? null,
    email: session?.user?.email ?? null,
    user: session?.user ?? null,
  };
}

export function logAuth(label: string, payload?: unknown): void {
  if (!isAuthDebugEnabled()) return;
  console.log(`========== ${label} ==========`);
  if (payload !== undefined) {
    console.log(payload);
  }
}

export function logAuthStateChanged(session: AuthSession | null): void {
  if (!isAuthDebugEnabled()) return;
  console.log('========== AUTH STATE CHANGED ==========');
  console.log({
    userId: session?.user?.id ?? null,
    email: session?.user?.email ?? null,
    tokenExists: Boolean(session?.accessToken),
    tokenPrefix: tokenPrefix(session?.accessToken),
    expiry: session?.expiresAt ?? null,
  });
}

export function logApiRequest(details: {
  url: string;
  method?: string;
  hasAuthorization?: boolean;
  tokenPrefix?: string | null;
  body?: unknown;
}): void {
  if (!isAuthDebugEnabled()) return;
  console.log('========== API REQUEST ==========');
  console.log({
    url: details.url,
    method: details.method ?? 'GET',
    authorizationHeaderPresent: Boolean(details.hasAuthorization),
    tokenPrefix: details.tokenPrefix ?? null,
    body: details.body ?? null,
  });
}

export function logApiResponse(details: {
  url: string;
  status: number;
  headers?: Record<string, string>;
  body?: unknown;
}): void {
  if (!isAuthDebugEnabled()) return;
  console.log('========== API RESPONSE ==========');
  console.log({
    url: details.url,
    status: details.status,
    headers: details.headers ?? {},
    body: details.body ?? null,
  });
}

export function logFirst401(details: {
  url: string;
  method?: string;
  status: number;
  headers?: Record<string, string>;
  body?: unknown;
  tokenPrefix?: string | null;
}): void {
  if (!isAuthDebugEnabled()) return;
  console.error('========== FIRST 401 DETECTED ==========');
  console.error(details);
  console.trace();
}

export function logUnauthorizedDiagnostic(): void {
  if (!isAuthDebugEnabled()) return;
  console.error('========== 401 UNAUTHORIZED ==========');
  console.error(
    'Redirect/sign-out disabled for diagnostics. Session left intact.',
  );
  console.trace();
  // Pause when DevTools is open so the first 401 can be inspected.
  // eslint-disable-next-line no-debugger
  debugger;
}
