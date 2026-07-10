import type { MetadataRoute } from "next";
import { DOC_SECTIONS } from "@/lib/content";
import { SITE } from "@/lib/site";

export default function sitemap(): MetadataRoute.Sitemap {
  const baseUrl = SITE.url;

  const staticPages = [
    "",
    "/features",
    "/solutions",
    "/industries",
    "/pricing",
    "/documentation",
    "/about",
    "/contact",
    "/privacy",
    "/terms",
    "/security",
  ];

  const docPages = DOC_SECTIONS.flatMap((section) =>
    section.items.map((item) => `/documentation/${item.slug}`),
  );

  const allPages = [...staticPages, ...docPages];

  return allPages.map((path) => ({
    url: `${baseUrl}${path}`,
    lastModified: new Date(),
    changeFrequency: path === "" ? "weekly" : "monthly",
    priority: path === "" ? 1 : path.startsWith("/documentation") ? 0.6 : 0.8,
  }));
}
