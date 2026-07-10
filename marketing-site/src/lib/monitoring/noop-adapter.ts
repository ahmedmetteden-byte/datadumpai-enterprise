import type { MonitoringAdapter } from "./types";

export const noopAdapter: MonitoringAdapter = {
  captureException() {
    // Monitoring disabled — no-op.
  },
  captureMessage() {
    // Monitoring disabled — no-op.
  },
};
