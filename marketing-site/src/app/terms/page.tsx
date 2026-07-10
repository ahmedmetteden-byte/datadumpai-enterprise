import type { Metadata } from "next";
import { createMetadata } from "@/lib/metadata";
import { SITE } from "@/lib/site";
import { PageHero, Section } from "@/components/ui/Section";

export const metadata: Metadata = createMetadata({
  title: "Terms of Service",
  description: "DataDumpAI terms of service — the agreement governing use of our platform.",
  path: "/terms",
});

export default function TermsPage() {
  return (
    <>
      <PageHero
        title="Terms of Service"
        description={`Last updated: July 2026. By using ${SITE.name}, you agree to these terms.`}
      />
      <Section>
        <div className="mx-auto max-w-3xl space-y-10">
          <section>
            <h2 className="text-xl font-semibold text-ink">Acceptance of terms</h2>
            <p className="mt-3 leading-relaxed text-ink-muted">
              By accessing or using DataDumpAI, you agree to be bound by these Terms
              of Service and our Privacy Policy. If you do not agree, do not use the
              service.
            </p>
          </section>
          <section>
            <h2 className="text-xl font-semibold text-ink">Use of the service</h2>
            <p className="mt-3 leading-relaxed text-ink-muted">
              You may use DataDumpAI only for lawful purposes and in accordance with
              these terms. You are responsible for all content you upload and for
              maintaining the confidentiality of your account credentials.
            </p>
          </section>
          <section>
            <h2 className="text-xl font-semibold text-ink">Intellectual property</h2>
            <p className="mt-3 leading-relaxed text-ink-muted">
              You retain ownership of documents you upload. DataDumpAI retains
              ownership of the platform, software, and AI models. Generated reports
              are yours to use subject to your subscription plan.
            </p>
          </section>
          <section>
            <h2 className="text-xl font-semibold text-ink">Limitation of liability</h2>
            <p className="mt-3 leading-relaxed text-ink-muted">
              DataDumpAI is provided &ldquo;as is.&rdquo; We do not guarantee that
              AI-generated outputs are error-free or suitable for any particular
              purpose. You are responsible for reviewing outputs before use in
              decision-making contexts.
            </p>
          </section>
          <section>
            <h2 className="text-xl font-semibold text-ink">Contact</h2>
            <p className="mt-3 leading-relaxed text-ink-muted">
              Questions about these terms? Contact{" "}
              <a href={`mailto:${SITE.contactEmail}`} className="text-brand-500 hover:underline">
                {SITE.contactEmail}
              </a>
              .
            </p>
          </section>
        </div>
      </Section>
    </>
  );
}
