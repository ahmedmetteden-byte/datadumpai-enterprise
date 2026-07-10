import type { Metadata } from "next";
import { SOLUTIONS } from "@/lib/content";
import { createMetadata } from "@/lib/metadata";
import { LaunchAppButton } from "@/components/ui/Button";
import { PageHero, Section } from "@/components/ui/Section";

export const metadata: Metadata = createMetadata({
  title: "Solutions",
  description:
    "DataDumpAI solutions for executive teams, regulators, compliance officers, risk managers, researchers, consultants, and boards.",
  path: "/solutions",
});

export default function SolutionsPage() {
  return (
    <>
      <PageHero
        title="Solutions for every stakeholder"
        description="Tailored workflows for the people who turn documents into decisions."
      >
        <LaunchAppButton />
      </PageHero>
      <Section>
        <div className="grid gap-8 md:grid-cols-2">
          {SOLUTIONS.map((solution) => (
            <article
              key={solution.title}
              className="rounded-2xl border border-surface-border bg-white p-8 shadow-sm transition-all hover:shadow-card"
            >
              <span className="inline-block rounded-full bg-brand-50 px-3 py-1 text-xs font-semibold text-brand-600">
                {solution.audience}
              </span>
              <h2 className="mt-4 text-2xl font-bold text-ink">{solution.title}</h2>
              <p className="mt-3 leading-relaxed text-ink-muted">
                {solution.description}
              </p>
            </article>
          ))}
        </div>
      </Section>
    </>
  );
}
