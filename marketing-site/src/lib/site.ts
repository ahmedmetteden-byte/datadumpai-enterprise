import { normalizeUrl } from "./env";

export const SITE = {
  name: "DataDumpAI",
  tagline: "AI-Powered Document Intelligence Platform",
  description:
    "DataDumpAI transforms reports, PDFs, meeting minutes, policies, regulations, and research into executive reports, strategic insights, presentations, compliance analyses, and intelligence briefs.",
  url: normalizeUrl(process.env.NEXT_PUBLIC_SITE_URL, "https://www.getdatadump.com"),
  appUrl: normalizeUrl(process.env.NEXT_PUBLIC_APP_URL, "https://www.getdatadump.com"),
  contactEmail:
    process.env.NEXT_PUBLIC_CONTACT_EMAIL ?? "hello@getdatadump.com",
  version: "1.0",
  twitterHandle: "@DataDumpAI",
} as const;

export const NAV_LINKS = [
  { href: "/", label: "Home" },
  { href: "/features", label: "Features" },
  { href: "/solutions", label: "Solutions" },
  { href: "/industries", label: "Industries" },
  { href: "/pricing", label: "Pricing" },
  { href: "/documentation", label: "Documentation" },
  { href: "/about", label: "About" },
  { href: "/contact", label: "Contact" },
] as const;

export const FOOTER_LINKS = {
  product: [
    { href: "/features", label: "Features" },
    { href: "/pricing", label: "Pricing" },
    { href: "/solutions", label: "Solutions" },
    { href: "/industries", label: "Industries" },
    { href: "/documentation", label: "Documentation" },
  ],
  company: [
    { href: "/about", label: "About" },
    { href: "/contact", label: "Contact" },
    { href: "/security", label: "Security" },
  ],
  resources: [
    { href: "/documentation", label: "Docs" },
    { href: "/documentation/getting-started", label: "Getting Started" },
    { href: "/documentation/api", label: "API Reference" },
  ],
  legal: [
    { href: "/privacy", label: "Privacy Policy" },
    { href: "/terms", label: "Terms of Service" },
    { href: "/security", label: "Security" },
  ],
} as const;

export const SOCIAL_LINKS = [
  {
    name: "LinkedIn",
    href: "https://www.linkedin.com/company/datadumpai",
    icon: "linkedin",
  },
  {
    name: "X",
    href: "https://x.com/DataDumpAI",
    icon: "x",
  },
  {
    name: "Facebook",
    href: "https://www.facebook.com/datadumpai",
    icon: "facebook",
  },
  {
    name: "Discord",
    href: "https://discord.gg/datadumpai",
    icon: "discord",
  },
] as const;
