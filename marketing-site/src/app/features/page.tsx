import type { Metadata } from "next";
import { FEATURES } from "@/lib/content";
import { createMetadata } from "@/lib/metadata";
import { Icon } from "@/components/ui/Icon";
import { PageHero, Section } from "@/components/ui/Section";
import { LaunchAppButton } from "@/components/ui/Button";

export const metadata: Metadata = createMetadata({
  title: "Features",
  description:
    "Explore DataDumpAI capabilities: AI summaries, executive reports, meeting intelligence, compliance analysis, cross-document insights, and more.",
  path: "/features",
});

export default function FeaturesPage() {
  return (
    <>
      <PageHero
        title="Powerful features for document intelligence"
        description="Everything your team needs to transform unstructured documents into executive-grade deliverables."
      >
        <LaunchAppButton />
      </PageHero>
      <Section>
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((feature) => (
            <article
              key={feature.title}
              className="rounded-2xl border border-surface-border bg-white p-7 shadow-sm transition-all hover:border-brand-200 hover:shadow-card"
            >
              <div
                className="mb-4 inline-flex rounded-xl bg-brand-50 p-3 text-brand-500"
                aria-hidden="true"
              >
                <Icon name={feature.icon} />
              </div>
              <h2 className="text-xl font-semibold text-ink">{feature.title}</h2>
              <p className="mt-3 text-sm leading-relaxed text-ink-muted">
                {feature.description}
              </p>
            </article>
          ))}
        </div>
      </Section>
    </>
  );
}
