import type { Metadata } from "next";
import { createMetadata } from "@/lib/metadata";
import { SITE } from "@/lib/site";
import { Hero } from "@/components/home/Hero";
import {
  CTABanner,
  FeaturesPreview,
  IndustriesPreview,
} from "@/components/home/Sections";
import { ShareButtons } from "@/components/ui/ShareButtons";
import { Section } from "@/components/ui/Section";

export const metadata: Metadata = createMetadata({
  title: SITE.name,
  description: SITE.description,
  path: "/",
});

export default function HomePage() {
  return (
    <>
      <Hero />
      <FeaturesPreview />
      <IndustriesPreview />
      <CTABanner />
      <Section muted className="!py-12">
        <ShareButtons url={`${SITE.url}/`} title={`${SITE.name} — ${SITE.tagline}`} />
      </Section>
    </>
  );
}
