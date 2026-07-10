import type { Metadata } from "next";
import { createMetadata } from "@/lib/metadata";
import { ContactForm, ContactInfo } from "@/components/contact/ContactForm";
import { PageHero, Section } from "@/components/ui/Section";

export const metadata: Metadata = createMetadata({
  title: "Contact",
  description:
    "Get in touch with the DataDumpAI team for sales, support, partnerships, and enterprise inquiries.",
  path: "/contact",
});

export default function ContactPage() {
  return (
    <>
      <PageHero
        title="Get in touch"
        description="Have a question about DataDumpAI? We'd love to hear from you."
      />
      <Section>
        <div className="grid gap-12 lg:grid-cols-5">
          <div className="lg:col-span-3">
            <ContactForm />
          </div>
          <div className="lg:col-span-2">
            <ContactInfo />
          </div>
        </div>
      </Section>
    </>
  );
}
