import type { Metadata } from "next";
import Link from "next/link";
import { DOC_SECTIONS } from "@/lib/content";
import { createMetadata } from "@/lib/metadata";
import { PageHero, Section } from "@/components/ui/Section";

export const metadata: Metadata = createMetadata({
  title: "Documentation",
  description:
    "DataDumpAI documentation — getting started, platform guides, and enterprise features.",
  path: "/documentation",
});

export default function DocumentationPage() {
  return (
    <>
      <PageHero
        title="Documentation"
        description="Everything you need to get started with DataDumpAI and unlock its full potential."
      />
      <Section>
        <div className="grid gap-8 md:grid-cols-3">
          {DOC_SECTIONS.map((section) => (
            <div
              key={section.slug}
              className="rounded-2xl border border-surface-border bg-white p-6"
            >
              <h2 className="text-lg font-semibold text-ink">{section.title}</h2>
              <ul className="mt-4 space-y-2">
                {section.items.map((item) => (
                  <li key={item.slug}>
                    <Link
                      href={`/documentation/${item.slug}`}
                      className="text-sm text-brand-500 hover:text-brand-600 hover:underline"
                    >
                      {item.title}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </Section>
    </>
  );
}
