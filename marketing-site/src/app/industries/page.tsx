import type { Metadata } from "next";
import { INDUSTRIES } from "@/lib/content";
import { createMetadata } from "@/lib/metadata";
import { Icon } from "@/components/ui/Icon";
import { LaunchAppButton } from "@/components/ui/Button";
import { PageHero, Section } from "@/components/ui/Section";

export const metadata: Metadata = createMetadata({
  title: "Industries",
  description:
    "DataDumpAI serves insurance, government, financial services, healthcare, legal, energy, manufacturing, and education.",
  path: "/industries",
});

export default function IndustriesPage() {
  return (
    <>
      <PageHero
        title="Built for document-intensive industries"
        description="From regulated sectors to research-driven organizations — DataDumpAI adapts to your domain."
      >
        <LaunchAppButton />
      </PageHero>
      <Section>
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {INDUSTRIES.map((industry) => (
            <article
              key={industry.name}
              className="group rounded-2xl border border-surface-border bg-white p-7 transition-all hover:border-brand-200 hover:shadow-card"
            >
              <div className="mb-4 inline-flex rounded-xl bg-brand-50 p-3 text-brand-500 transition-colors group-hover:bg-brand-100">
                <Icon name={industry.icon} className="h-7 w-7" />
              </div>
              <h2 className="text-lg font-semibold text-ink">{industry.name}</h2>
              <p className="mt-3 text-sm leading-relaxed text-ink-muted">
                {industry.description}
              </p>
            </article>
          ))}
        </div>
      </Section>
    </>
  );
}
