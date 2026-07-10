"use client";

import { SITE } from "@/lib/site";
import { buildShareUrl } from "@/lib/metadata";

const platforms = [
  { id: "linkedin", label: "LinkedIn", color: "hover:bg-[#0A66C2] hover:text-white" },
  { id: "facebook", label: "Facebook", color: "hover:bg-[#1877F2] hover:text-white" },
  { id: "whatsapp", label: "WhatsApp", color: "hover:bg-[#25D366] hover:text-white" },
  { id: "slack", label: "Slack", color: "hover:bg-[#4A154B] hover:text-white" },
  { id: "discord", label: "Discord", color: "hover:bg-[#5865F2] hover:text-white" },
  { id: "x", label: "X", color: "hover:bg-black hover:text-white" },
];

export function ShareButtons({ url, title }: { url?: string; title?: string }) {
  const shareUrl = url ?? SITE.url;
  const shareTitle = title ?? `${SITE.name} — ${SITE.tagline}`;

  return (
    <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Share this page">
      <span className="mr-2 text-sm font-medium text-ink-muted">Share:</span>
      {platforms.map((platform) => (
        <a
          key={platform.id}
          href={buildShareUrl(platform.id, shareUrl, shareTitle)}
          target="_blank"
          rel="noopener noreferrer"
          className={`rounded-lg border border-surface-border px-3 py-1.5 text-xs font-medium text-ink-muted transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-500 ${platform.color}`}
          aria-label={`Share on ${platform.label} (opens in new tab)`}
        >
          {platform.label}
        </a>
      ))}
    </div>
  );
}
