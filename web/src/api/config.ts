/**
 * Shared API runtime config.
 * Mock data is off by default — set VITE_USE_MOCK_API=true only for offline demos.
 */

export function isMockApiEnabled(): boolean {
  return (
    (import.meta.env.VITE_USE_MOCK_API ?? 'false').toString().toLowerCase() ===
    'true'
  );
}

/** @deprecated Prefer isMockApiEnabled — name avoided "use*" for oxlint hooks rule. */
export const useMockApi = isMockApiEnabled;

export async function mockLatency(ms = 160): Promise<void> {
  await new Promise((resolve) => setTimeout(resolve, ms));
}

/** Optional auth context passed into HTTP service calls later. */
export interface ServiceAuth {
  accessToken?: string | null;
}
