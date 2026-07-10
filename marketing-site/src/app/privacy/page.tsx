import type { Metadata } from "next";
import { createMetadata } from "@/lib/metadata";
import { SITE } from "@/lib/site";
import { PageHero, Section } from "@/components/ui/Section";

export const metadata: Metadata = createMetadata({
  title: "Privacy Policy",
  description: "DataDumpAI privacy policy — how we collect, use, and protect your data.",
  path: "/privacy",
});

export default function PrivacyPage() {
  return (
    <>
      <PageHero
        title="Privacy Policy"
        description={`Last updated: July 2026. This policy describes how ${SITE.name} handles your information.`}
      />
      <Section>
        <div className="prose prose-slate mx-auto max-w-3xl">
          <section className="mb-10">
            <h2 className="text-xl font-semibold text-ink">Information we collect</h2>
            <p className="mt-3 leading-relaxed text-ink-muted">
              We collect information you provide directly, including account details,
              uploaded documents, and usage data necessary to deliver our services.
              We also collect technical information such as IP addresses, browser type,
              and device identifiers for security and analytics purposes.
            </p>
          </section>
          <section className="mb-10">
            <h2 className="text-xl font-semibold text-ink">How we use your information</h2>
            <p className="mt-3 leading-relaxed text-ink-muted">
              Your information is used to provide, maintain, and improve DataDumpAI
              services, process documents, generate reports, communicate with you,
              and ensure platform security. We do not sell your personal data to
              third parties.
            </p>
          </section>
          <section className="mb-10">
            <h2 className="text-xl font-semibold text-ink">Data retention</h2>
            <p className="mt-3 leading-relaxed text-ink-muted">
              We retain your data for as long as your account is active or as needed
              to provide services. You may request deletion of your account and
              associated data at any time by contacting us at {SITE.contactEmail}.
            </p>
          </section>
          <section className="mb-10">
            <h2 className="text-xl font-semibold text-ink">Your rights</h2>
            <p className="mt-3 leading-relaxed text-ink-muted">
              Depending on your jurisdiction, you may have rights to access, correct,
              delete, or port your personal data. Contact us to exercise these rights.
            </p>
          </section>
          <section>
            <h2 className="text-xl font-semibold text-ink">Contact</h2>
            <p className="mt-3 leading-relaxed text-ink-muted">
              For privacy-related inquiries, email us at{" "}
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
