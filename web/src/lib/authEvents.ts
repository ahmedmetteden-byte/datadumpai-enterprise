/**
 * Central auth event bus for API 401s.
 * AuthProvider registers a handler so redirects stay out of apiRequest().
 *
 * DIAGNOSTICS MODE: handlers must not redirect / sign out / clear session.
 */

type UnauthorizedHandler = () => void;

let unauthorizedHandler: UnauthorizedHandler | null = null;
let unauthorizedNotified = false;

export function setUnauthorizedHandler(handler: UnauthorizedHandler | null): void {
  unauthorizedHandler = handler;
  unauthorizedNotified = false;
}

/** Called once per auth failure wave. Handler is logging-only while diagnosing. */
export function notifyUnauthorized(): void {
  if (unauthorizedNotified) return;
  unauthorizedNotified = true;
  try {
    unauthorizedHandler?.();
  } finally {
    window.setTimeout(() => {
      unauthorizedNotified = false;
    }, 1500);
  }
}
