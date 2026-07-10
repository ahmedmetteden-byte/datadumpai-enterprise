import Image from "next/image";
import { SITE } from "@/lib/site";
import { LaunchAppButton } from "@/components/ui/Button";

const OUTPUTS = [
  "Executive reports",
  "Strategic insights",
  "Presentations",
  "Compliance analyses",
  "Intelligence briefs",
];

export function Hero() {
  return (
    <section
      className="relative overflow-hidden bg-mesh-gradient"
      aria-labelledby="hero-heading"
    >
      <div
        className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(37,99,235,0.08),transparent_50%)]"
        aria-hidden="true"
      />
      <div className="relative mx-auto max-w-7xl px-6 pb-24 pt-16 md:pb-32 md:pt-24 lg:px-8">
        <div className="grid items-center gap-12 lg:grid-cols-2 lg:gap-16">
          <div className="motion-safe:animate-slide-up">
            <p className="mb-4 inline-flex items-center rounded-full border border-brand-200 bg-brand-50 px-4 py-1.5 text-sm font-medium text-brand-700">
              {SITE.tagline}
            </p>
            <h1
              id="hero-heading"
              className="text-4xl font-bold tracking-tight text-ink sm:text-5xl lg:text-[3.5rem] lg:leading-[1.1]"
            >
              Transform Documents into{" "}
              <span className="bg-hero-gradient bg-clip-text text-transparent">
                Executive Intelligence
              </span>
            </h1>
            <p className="mt-6 text-lg leading-relaxed text-ink-muted md:text-xl">
              DataDumpAI converts reports, PDFs, meeting minutes, policies,
              regulations, and research into:
            </p>
            <ul className="mt-4 grid gap-2 sm:grid-cols-2" aria-label="Output types">
              {OUTPUTS.map((item) => (
                <li
                  key={item}
                  className="flex items-center gap-2 text-sm font-medium text-ink md:text-base"
                >
                  <span
                    className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-brand-100 text-brand-600"
                    aria-hidden="true"
                  >
                    <svg className="h-3 w-3" fill="currentColor" viewBox="0 0 20 20">
                      <path
                        fillRule="evenodd"
                        d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                        clipRule="evenodd"
                      />
                    </svg>
                  </span>
                  {item}
                </li>
              ))}
            </ul>
            <div className="mt-10 flex flex-wrap gap-4">
              <LaunchAppButton size="lg">Start Analyzing Documents</LaunchAppButton>
              <LaunchAppButton size="lg" variant="secondary">
                Launch App
              </LaunchAppButton>
            </div>
            <p className="mt-4 text-sm text-ink-muted">
              14-day Professional trial &middot; No credit card required
            </p>
          </div>

          <div className="relative flex justify-center lg:justify-end">
            <div className="motion-safe:animate-float relative">
              <div
                className="absolute -inset-4 rounded-3xl bg-hero-gradient opacity-20 blur-2xl"
                aria-hidden="true"
              />
              <div className="relative rounded-2xl border border-surface-border bg-white p-6 shadow-card md:p-8">
                <Image
                  src="/datadump-hero-logo.webp"
                  alt={`${SITE.name} platform illustration`}
                  width={540}
                  height={540}
                  sizes="(max-width: 1024px) 90vw, 540px"
                  className="h-auto w-full max-w-lg"
                  priority
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
