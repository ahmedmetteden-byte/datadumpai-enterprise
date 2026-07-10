import { createSentryAdapter } from "./sentry-adapter";
import { noopAdapter } from "./noop-adapter";
import type { MonitoringAdapter, MonitoringLevel } from "./types";

let adapter: MonitoringAdapter = noopAdapter;
let initialized = false;

/** Read the Sentry DSN from the environment (empty disables monitoring). */
export function getMonitoringDsn(): string {
  return process.env.NEXT_PUBLIC_SENTRY_DSN?.trim() ?? "";
}

/** True when a DSN is configured and the app runs in production. */
export function isMonitoringEnabled(): boolean {
  return process.env.NODE_ENV === "production" && getMonitoringDsn().length > 0;
}

/**
 * Initialize production monitoring.
 *
 * When NEXT_PUBLIC_SENTRY_DSN is set, wires the Sentry adapter stub.
 * Install @sentry/nextjs and complete sentry-adapter.ts to send events.
 */
export async function initMonitoring(): Promise<void> {
  if (initialized) {
    return;
  }

  if (!isMonitoringEnabled()) {
    adapter = noopAdapter;
    initialized = true;
    return;
  }

  adapter = createSentryAdapter();
  initialized = true;
}

export function captureException(
  error: unknown,
  context?: Record<string, unknown>,
): void {
  adapter.captureException(error, context);
}

export function captureMessage(
  message: string,
  level: MonitoringLevel = "info",
): void {
  adapter.captureMessage(message, level);
}

export function setMonitoringAdapter(next: MonitoringAdapter): void {
  adapter = next;
  initialized = true;
}
