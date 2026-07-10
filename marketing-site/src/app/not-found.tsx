import type { Metadata } from "next";
import { Button } from "@/components/ui/Button";
import { createMetadata } from "@/lib/metadata";

export const metadata: Metadata = createMetadata({
  title: "Page Not Found",
  description: "The page you requested could not be found on DataDumpAI.",
  path: "/404",
  noIndex: true,
});

export default function NotFound() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center px-6 text-center">
      <p className="text-sm font-semibold text-brand-500">404</p>
      <h1 className="mt-2 text-3xl font-bold text-ink">Page not found</h1>
      <p className="mt-4 max-w-md text-ink-muted">
        The page you&apos;re looking for doesn&apos;t exist or has been moved.
      </p>
      <div className="mt-8">
        <Button href="/" size="lg">
          Back to home
        </Button>
      </div>
    </div>
  );
}
