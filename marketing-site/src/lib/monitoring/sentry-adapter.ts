/**
 * Sentry adapter stub.
 *
 * To enable Sentry in production:
 * 1. Create a project at https://sentry.io and copy the DSN.
 * 2. Set NEXT_PUBLIC_SENTRY_DSN in your deployment environment.
 * 3. Install the SDK: npm install @sentry/nextjs
 * 4. Implement createSentryAdapter() below using Sentry.init() and Sentry.captureException().
 * 5. Export the adapter from lib/monitoring/index.ts when the package is present.
 */

import type { MonitoringAdapter } from "./types";
import { noopAdapter } from "./noop-adapter";

export function createSentryAdapter(): MonitoringAdapter {
  // Placeholder until @sentry/nextjs is installed and configured.
  return noopAdapter;
}
