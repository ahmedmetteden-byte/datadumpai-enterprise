import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { DOC_CONTENT, DOC_SECTIONS } from "@/lib/content";
import { breadcrumbJsonLd, createMetadata } from "@/lib/metadata";
import { JsonLd } from "@/components/seo/JsonLd";
import { DocSidebar } from "@/components/documentation/DocSidebar";

type Props = {
  params: Promise<{ slug: string }>;
};

export async function generateStaticParams() {
  return DOC_SECTIONS.flatMap((section) =>
    section.items.map((item) => ({ slug: item.slug })),
  );
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const doc = DOC_CONTENT[slug];
  if (!doc) {
    notFound();
  }

  return createMetadata({
    title: doc.title,
    description: doc.description,
    path: `/documentation/${slug}`,
  });
}

export default async function DocPage({ params }: Props) {
  const { slug } = await params;
  const doc = DOC_CONTENT[slug];

  if (!doc) {
    notFound();
  }

  return (
    <>
      <JsonLd
        data={breadcrumbJsonLd([
          { name: "Documentation", path: "/documentation" },
          { name: doc.title, path: `/documentation/${slug}` },
        ])}
      />
      <div className="mx-auto max-w-7xl px-6 py-12 lg:px-8 lg:py-16">
        <div className="flex flex-col gap-10 lg:flex-row">
          <DocSidebar activeSlug={slug} />
          <article className="min-w-0 flex-1">
            <h1 className="text-3xl font-bold text-ink md:text-4xl">{doc.title}</h1>
            <p className="mt-4 text-lg text-ink-muted">{doc.description}</p>
            <div className="mt-10 space-y-10">
              {doc.sections.map((section, index) => (
                <section key={section.heading} aria-labelledby={`doc-section-${index}`}>
                  <h2
                    id={`doc-section-${index}`}
                    className="text-xl font-semibold text-ink"
                  >
                    {section.heading}
                  </h2>
                  <p className="mt-3 leading-relaxed text-ink-muted">{section.body}</p>
                </section>
              ))}
            </div>
          </article>
        </div>
      </div>
    </>
  );
}
