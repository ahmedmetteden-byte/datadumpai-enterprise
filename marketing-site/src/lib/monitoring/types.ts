export type MonitoringLevel = "info" | "warning" | "error";

export interface MonitoringAdapter {
  captureException(error: unknown, context?: Record<string, unknown>): void;
  captureMessage(message: string, level?: MonitoringLevel): void;
}
