import type { Metadata } from "next";
import { SECURITY_FEATURES } from "@/lib/content";
import { createMetadata } from "@/lib/metadata";
import { SITE } from "@/lib/site";
import { LaunchAppButton } from "@/components/ui/Button";
import { PageHero, Section } from "@/components/ui/Section";

export const metadata: Metadata = createMetadata({
  title: "Security",
  description:
    "DataDumpAI security: encryption, role-based access, audit logs, enterprise security, and AI governance.",
  path: "/security",
});

export default function SecurityPage() {
  return (
    <>
      <PageHero
        title="Enterprise-grade security"
        description="Your documents deserve the highest level of protection. Security is built into every layer of DataDumpAI."
      >
        <LaunchAppButton />
      </PageHero>
      <Section>
        <div className="grid gap-8 md:grid-cols-2">
          {SECURITY_FEATURES.map((feature) => (
            <article
              key={feature.title}
              className="rounded-2xl border border-surface-border bg-white p-8 shadow-sm"
            >
              <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-brand-50 text-brand-500">
                <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
                </svg>
              </div>
              <h2 className="text-xl font-semibold text-ink">{feature.title}</h2>
              <p className="mt-3 leading-relaxed text-ink-muted">{feature.description}</p>
            </article>
          ))}
        </div>

        <div className="mt-16 rounded-2xl border border-surface-border bg-surface-muted p-8 md:p-12">
          <h2 className="text-2xl font-bold text-ink">Security inquiries</h2>
          <p className="mt-4 max-w-2xl text-ink-muted">
            Enterprise customers can request security questionnaires, data processing
            agreements, and compliance documentation. Our team is available to support
            your procurement and security review process.
          </p>
          <p className="mt-4">
            <a
              href={`mailto:${SITE.contactEmail}`}
              className="font-medium text-brand-500 hover:text-brand-600"
            >
              {SITE.contactEmail}
            </a>
          </p>
        </div>
      </Section>
    </>
  );
}
