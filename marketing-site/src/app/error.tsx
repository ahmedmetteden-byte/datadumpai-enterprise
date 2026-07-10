"use client";

import { useEffect } from "react";
import { captureException } from "@/lib/monitoring";
import { Button } from "@/components/ui/Button";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    captureException(error, { digest: error.digest, boundary: "route" });
  }, [error]);

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center px-6 text-center">
      <p className="text-sm font-semibold text-brand-500">Error</p>
      <h1 className="mt-2 text-3xl font-bold text-ink">Something went wrong</h1>
      <p className="mt-4 max-w-md text-ink-muted">
        An unexpected error occurred. Please try again.
      </p>
      <div className="mt-8 flex flex-wrap justify-center gap-4">
        <Button type="button" size="lg" onClick={reset}>
          Try again
        </Button>
        <Button href="/" size="lg" variant="secondary">
          Back to home
        </Button>
      </div>
    </div>
  );
}
