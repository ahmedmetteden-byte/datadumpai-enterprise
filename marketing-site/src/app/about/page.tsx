import type { Metadata } from "next";
import { createMetadata } from "@/lib/metadata";
import { SITE } from "@/lib/site";
import { LaunchAppButton } from "@/components/ui/Button";
import { PageHero, Section } from "@/components/ui/Section";

export const metadata: Metadata = createMetadata({
  title: "About",
  description:
    "Learn about DataDumpAI's mission to transform documents into AI-powered decision intelligence for enterprise teams.",
  path: "/about",
});

const VALUES = [
  {
    title: "Decision Intelligence",
    description:
      "We believe every organization deserves instant access to the intelligence buried in their documents.",
  },
  {
    title: "Trust & Transparency",
    description:
      "Every AI-generated insight is cited, traceable, and auditable — because decisions demand evidence.",
  },
  {
    title: "Enterprise Ready",
    description:
      "Built for regulated industries with security, governance, and scale at the core of our platform.",
  },
];

export default function AboutPage() {
  return (
    <>
      <PageHero
        title="AI-powered decision intelligence"
        description={`${SITE.name} exists to close the gap between document overload and executive action.`}
      >
        <LaunchAppButton />
      </PageHero>
      <Section>
        <div className="mx-auto max-w-3xl">
          <h2 className="text-2xl font-bold text-ink">Our mission</h2>
          <p className="mt-4 text-lg leading-relaxed text-ink-muted">
            Organizations generate vast amounts of unstructured information — reports,
            policies, meeting minutes, regulations, and research. Yet turning this
            material into actionable intelligence remains slow, manual, and expensive.
          </p>
          <p className="mt-4 text-lg leading-relaxed text-ink-muted">
            DataDumpAI was built to change that. We combine advanced AI with
            enterprise-grade document processing to deliver executive reports,
            strategic insights, compliance analyses, and intelligence briefs in
            minutes — not days.
          </p>
          <p className="mt-4 text-lg leading-relaxed text-ink-muted">
            Our platform serves executive teams, boards, compliance officers,
            regulators, researchers, and consultants who need reliable,
            citation-backed intelligence from their document libraries.
          </p>
        </div>

        <section className="mt-16" aria-labelledby="values-heading">
          <h2 id="values-heading" className="text-2xl font-bold text-ink">
            What we stand for
          </h2>
          <div className="mt-8 grid gap-8 md:grid-cols-3">
            {VALUES.map((value) => (
              <article
                key={value.title}
                className="rounded-2xl border border-surface-border bg-white p-7"
              >
                <h3 className="text-lg font-semibold text-ink">{value.title}</h3>
                <p className="mt-3 text-sm leading-relaxed text-ink-muted">
                  {value.description}
                </p>
              </article>
            ))}
          </div>
        </section>
      </Section>
    </>
  );
}
