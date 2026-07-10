"use client";

import Link from "next/link";
import { useEffect } from "react";
import { captureException } from "@/lib/monitoring";
import "./globals.css";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    captureException(error, { digest: error.digest, boundary: "global" });
  }, [error]);

  return (
    <html lang="en">
      <body className="flex min-h-screen flex-col items-center justify-center bg-white px-6 text-center font-sans text-ink antialiased">
        <p className="text-sm font-semibold text-brand-500">Error</p>
        <h1 className="mt-2 text-3xl font-bold">Something went wrong</h1>
        <p className="mt-4 max-w-md text-ink-muted">
          A critical error occurred. Please refresh the page or return home.
        </p>
        <div className="mt-8 flex flex-wrap justify-center gap-4">
          <button
            type="button"
            onClick={reset}
            className="inline-flex items-center justify-center rounded-xl bg-brand-500 px-7 py-3.5 text-base font-semibold text-white hover:bg-brand-600"
          >
            Try again
          </button>
          <Link
            href="/"
            className="inline-flex items-center justify-center rounded-xl border border-surface-border bg-white px-7 py-3.5 text-base font-semibold text-ink hover:bg-brand-50"
          >
            Back to home
          </Link>
        </div>
      </body>
    </html>
  );
}
