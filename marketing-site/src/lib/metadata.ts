import type { Metadata } from "next";
import { SITE, SOCIAL_LINKS } from "./site";

type PageMeta = {
  title: string;
  description: string;
  path: string;
  ogImage?: string;
  noIndex?: boolean;
};

export function createMetadata({
  title,
  description,
  path,
  ogImage = "/og-image.webp",
  noIndex = false,
}: PageMeta): Metadata {
  const canonical = `${SITE.url}${path}`;
  const fullTitle =
    path === "/" ? `${SITE.name} | ${SITE.tagline}` : `${title} | ${SITE.name}`;
  const imageUrl = ogImage.startsWith("http")
    ? ogImage
    : `${SITE.url}${ogImage}`;
  const imageType = ogImage.endsWith(".webp") ? "image/webp" : "image/png";

  return {
    title: fullTitle,
    description,
    metadataBase: new URL(SITE.url),
    alternates: {
      canonical,
    },
    openGraph: {
      type: "website",
      locale: "en_US",
      url: canonical,
      siteName: SITE.name,
      title: fullTitle,
      description,
      images: [
        {
          url: imageUrl,
          width: 1200,
          height: 630,
          alt: `${SITE.name} — ${SITE.tagline}`,
          type: imageType,
        },
      ],
    },
    twitter: {
      card: "summary_large_image",
      site: SITE.twitterHandle,
      creator: SITE.twitterHandle,
      title: fullTitle,
      description,
      images: [{ url: imageUrl, alt: `${SITE.name} — ${SITE.tagline}` }],
    },
    robots: noIndex
      ? { index: false, follow: false }
      : {
          index: true,
          follow: true,
          googleBot: {
            index: true,
            follow: true,
            "max-image-preview": "large",
            "max-snippet": -1,
          },
        },
  };
}

export function softwareApplicationJsonLd() {
  return {
    "@context": "https://schema.org",
    "@type": "SoftwareApplication",
    name: SITE.name,
    applicationCategory: "BusinessApplication",
    operatingSystem: "Web",
    url: SITE.url,
    description: SITE.description,
    image: `${SITE.url}/og-image.webp`,
    softwareVersion: SITE.version,
    offers: {
      "@type": "Offer",
      price: "0",
      priceCurrency: "USD",
      description: "Free trial with Professional features",
    },
    publisher: {
      "@type": "Organization",
      name: SITE.name,
      url: SITE.url,
      logo: `${SITE.url}/logo.png`,
      sameAs: SOCIAL_LINKS.map((link) => link.href),
    },
  };
}

export function breadcrumbJsonLd(items: { name: string; path: string }[]) {
  return {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: items.map((item, index) => ({
      "@type": "ListItem",
      position: index + 1,
      name: item.name,
      item: `${SITE.url}${item.path}`,
    })),
  };
}

export function buildShareUrl(
  platform: string,
  url: string,
  title: string,
): string {
  const encoded = encodeURIComponent(url);
  const encodedTitle = encodeURIComponent(title);

  switch (platform) {
    case "linkedin":
      return `https://www.linkedin.com/sharing/share-offsite/?url=${encoded}`;
    case "facebook":
      return `https://www.facebook.com/sharer/sharer.php?u=${encoded}`;
    case "whatsapp":
      return `https://wa.me/?text=${encodedTitle}%20${encoded}`;
    case "slack":
      return `https://slack.com/intl/en-gb/help/articles/206870377-Add-apps-to-your-workspace`;
    case "discord":
      return url;
    case "x":
      return `https://twitter.com/intent/tweet?url=${encoded}&text=${encodedTitle}`;
    default:
      return url;
  }
}
