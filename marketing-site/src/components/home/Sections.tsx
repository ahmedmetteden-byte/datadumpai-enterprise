import Link from "next/link";
import { FEATURES, INDUSTRIES } from "@/lib/content";
import { Icon } from "@/components/ui/Icon";
import { Section, SectionHeader } from "@/components/ui/Section";
import { Button, LaunchAppButton } from "@/components/ui/Button";

export function FeaturesPreview() {
  const preview = FEATURES.slice(0, 6);

  return (
    <Section id="features">
      <SectionHeader
        eyebrow="Capabilities"
        title="Everything you need for document intelligence"
        description="From upload to executive deliverable — AI-powered workflows built for enterprise teams."
      />
      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {preview.map((feature) => (
          <article
            key={feature.title}
            className="group rounded-2xl border border-surface-border bg-white p-6 shadow-sm transition-all duration-200 hover:border-brand-200 hover:shadow-card"
          >
            <div
              className="mb-4 inline-flex rounded-xl bg-brand-50 p-3 text-brand-500 transition-colors group-hover:bg-brand-100"
              aria-hidden="true"
            >
              <Icon name={feature.icon} />
            </div>
            <h3 className="text-lg font-semibold text-ink">{feature.title}</h3>
            <p className="mt-2 text-sm leading-relaxed text-ink-muted">
              {feature.description}
            </p>
          </article>
        ))}
      </div>
      <div className="mt-10 text-center">
        <Button href="/features" variant="secondary" size="lg">
          View all features
        </Button>
      </div>
    </Section>
  );
}

export function IndustriesPreview() {
  const preview = INDUSTRIES.slice(0, 4);

  return (
    <Section muted>
      <SectionHeader
        eyebrow="Industries"
        title="Built for regulated, document-heavy sectors"
        description="Trusted by teams in insurance, government, financial services, healthcare, and more."
      />
      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {preview.map((industry) => (
          <div
            key={industry.name}
            className="rounded-2xl border border-surface-border bg-white p-6 transition-all hover:shadow-card"
          >
            <div className="mb-3 text-brand-500">
              <Icon name={industry.icon} />
            </div>
            <h3 className="font-semibold text-ink">{industry.name}</h3>
            <p className="mt-2 text-sm text-ink-muted">{industry.description}</p>
          </div>
        ))}
      </div>
      <div className="mt-10 text-center">
        <Link
          href="/industries"
          className="text-sm font-semibold text-brand-600 hover:text-brand-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-500"
        >
          Explore all industries &rarr;
        </Link>
      </div>
    </Section>
  );
}

export function CTABanner() {
  return (
    <Section>
      <div className="relative overflow-hidden rounded-3xl bg-hero-gradient px-8 py-16 text-center md:px-16 md:py-20">
        <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxnIGZpbGw9IiNmZmYiIGZpbGwtb3BhY2l0eT0iMC4wNSI+PHBhdGggZD0iTTM2IDM0djItSDI0di0yaDEyek0zNiAyNHYySDI0di0yaDEyeiIvPjwvZz48L2c+PC9zdmc+')] opacity-40" />
        <div className="relative">
          <h2 className="text-3xl font-bold text-white md:text-4xl">
            Ready to transform your documents?
          </h2>
          <p className="mx-auto mt-4 max-w-2xl text-lg text-blue-100">
            Join teams who save hours every reporting cycle with AI-powered
            document intelligence.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-4">
            <LaunchAppButton size="lg" className="!bg-white !text-brand-600 hover:!bg-blue-50">
              Start Analyzing Documents
            </LaunchAppButton>
            <Button href="/contact" variant="outline" size="lg">
              Contact Sales
            </Button>
          </div>
        </div>
      </div>
    </Section>
  );
}
