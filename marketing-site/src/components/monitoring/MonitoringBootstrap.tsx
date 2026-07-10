"use client";

import { useEffect } from "react";
import { initMonitoring } from "@/lib/monitoring";

/** Client bootstrap for production error monitoring (no-op when DSN is unset). */
export function MonitoringBootstrap() {
  useEffect(() => {
    void initMonitoring();
  }, []);

  return null;
}
