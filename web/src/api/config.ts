/**
 * Shared API runtime config.
 * Flip VITE_USE_MOCK_API=false when FastAPI product routes are live.
 */

export function useMockApi(): boolean {
  return (
    (import.meta.env.VITE_USE_MOCK_API ?? 'true').toString().toLowerCase() !==
    'false'
  );
}

export async function mockLatency(ms = 160): Promise<void> {
  await new Promise((resolve) => setTimeout(resolve, ms));
}

/** Optional auth context passed into HTTP service calls later. */
export interface ServiceAuth {
  accessToken?: string | null;
}
