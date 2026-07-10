import type { Metadata } from "next";
import { PRICING_PLANS } from "@/lib/content";
import { createMetadata } from "@/lib/metadata";
import { SITE } from "@/lib/site";
import { Button, LaunchAppButton } from "@/components/ui/Button";
import { PageHero, Section } from "@/components/ui/Section";

export const metadata: Metadata = createMetadata({
  title: "Pricing",
  description:
    "DataDumpAI pricing plans: Starter, Professional, and Enterprise. Start with a 14-day free trial.",
  path: "/pricing",
});

const COMPARISON_ROWS: [string, string, string, string][] = [
  ["Reports per month", "100", "Unlimited", "Unlimited"],
  ["Document uploads", "100/mo", "Unlimited", "Unlimited"],
  ["Cross-document intelligence", "—", "✓", "✓"],
  ["Live web research", "—", "✓", "✓"],
  ["PowerPoint export", "—", "✓", "✓"],
  ["Custom branding", "—", "✓", "✓"],
  ["Team collaboration", "—", "✓", "✓"],
  ["SSO", "—", "—", "✓"],
  ["Audit logs", "—", "—", "✓"],
  ["API access", "—", "—", "✓"],
];

function ComparisonCell({ value }: { value: string }) {
  if (value === "✓") {
    return (
      <>
        <span aria-hidden="true">✓</span>
        <span className="sr-only">Included</span>
      </>
    );
  }
  if (value === "—") {
    return (
      <>
        <span aria-hidden="true">—</span>
        <span className="sr-only">Not included</span>
      </>
    );
  }
  return <>{value}</>;
}

export default function PricingPage() {
  return (
    <>
      <PageHero
        title="Simple, transparent pricing"
        description="Choose the plan that fits your team. All plans include a 14-day Professional trial."
      />
      <Section>
        <div className="grid gap-8 lg:grid-cols-3">
          {PRICING_PLANS.map((plan) => (
            <article
              key={plan.id}
              aria-label={`${plan.name} plan`}
              className={`relative flex flex-col rounded-2xl border p-8 ${
                plan.highlighted
                  ? "border-brand-500 bg-white shadow-glow ring-1 ring-brand-500"
                  : "border-surface-border bg-white shadow-sm"
              }`}
            >
              {plan.highlighted && (
                <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-brand-500 px-4 py-1 text-xs font-semibold text-white">
                  Most Popular
                </span>
              )}
              <h2 className="text-xl font-bold text-ink">{plan.name}</h2>
              <p className="mt-2 text-sm text-ink-muted">{plan.description}</p>
              <div className="mt-6 flex items-baseline gap-1">
                <span className="text-4xl font-bold text-ink">{plan.price}</span>
                {plan.period && (
                  <span className="text-sm text-ink-muted">{plan.period}</span>
                )}
              </div>
              <ul className="mt-8 flex-1 space-y-3">
                {plan.features.map((feature) => (
                  <li key={feature} className="flex items-start gap-2 text-sm text-ink-muted">
                    <svg
                      className="mt-0.5 h-4 w-4 shrink-0 text-brand-500"
                      fill="currentColor"
                      viewBox="0 0 20 20"
                      aria-hidden="true"
                    >
                      <path
                        fillRule="evenodd"
                        d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                        clipRule="evenodd"
                      />
                    </svg>
                    {feature}
                  </li>
                ))}
              </ul>
              <div className="mt-8">
                {plan.id === "enterprise" ? (
                  <Button href="/contact" variant="secondary" className="w-full">
                    {plan.cta}
                  </Button>
                ) : (
                  <LaunchAppButton className="w-full" />
                )}
              </div>
            </article>
          ))}
        </div>

        <div className="mt-16 overflow-x-auto rounded-2xl border border-surface-border">
          <table className="w-full min-w-[640px] text-left text-sm">
            <caption className="sr-only">Feature comparison across pricing plans</caption>
            <thead>
              <tr className="border-b border-surface-border bg-surface-muted">
                <th scope="col" className="px-6 py-4 font-semibold text-ink">
                  Feature
                </th>
                <th scope="col" className="px-6 py-4 font-semibold text-ink">
                  Starter
                </th>
                <th scope="col" className="px-6 py-4 font-semibold text-ink">
                  Professional
                </th>
                <th scope="col" className="px-6 py-4 font-semibold text-ink">
                  Enterprise
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-border">
              {COMPARISON_ROWS.map(([feature, starter, pro, enterprise]) => (
                <tr key={feature} className="hover:bg-surface-muted/50">
                  <th scope="row" className="px-6 py-4 font-medium text-ink">
                    {feature}
                  </th>
                  <td className="px-6 py-4 text-ink-muted">
                    <ComparisonCell value={starter} />
                  </td>
                  <td className="px-6 py-4 text-ink-muted">
                    <ComparisonCell value={pro} />
                  </td>
                  <td className="px-6 py-4 text-ink-muted">
                    <ComparisonCell value={enterprise} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <p className="mt-8 text-center text-sm text-ink-muted">
          Questions?{" "}
          <a
            href={`mailto:${SITE.contactEmail}`}
            className="text-brand-600 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-500"
          >
            {SITE.contactEmail}
          </a>
        </p>
      </Section>
    </>
  );
}
