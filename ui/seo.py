"""
SEO and social sharing metadata for the Streamlit application.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import streamlit.components.v1 as components

from config import (
    APP_NAME,
    APP_VERSION,
    SEO_DESCRIPTION,
    SEO_OG_DESCRIPTION,
    SEO_OG_TITLE,
    SEO_STRUCTURED_DESCRIPTION,
    SEO_TWITTER_DESCRIPTION,
    SITE_URL,
)

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
LOGO_PATH = ASSETS_DIR / "logo.png"
FAVICON_PATH = ASSETS_DIR / "favicon.png"


def _absolute_asset_url(filename: str) -> str:
    return f"{SITE_URL.rstrip('/')}/{filename}"


def structured_data() -> dict:
    """Return Schema.org JSON-LD for the product."""

    site_url = SITE_URL.rstrip("/")

    return {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "name": APP_NAME,
        "applicationCategory": "BusinessApplication",
        "operatingSystem": "Web",
        "url": site_url,
        "description": SEO_STRUCTURED_DESCRIPTION,
        "image": _absolute_asset_url("og-image.png"),
        "softwareVersion": APP_VERSION,
        "offers": {
            "@type": "Offer",
            "price": "0",
            "priceCurrency": "USD",
            "description": "Free plan with 14-day Professional trial",
        },
        "publisher": {
            "@type": "Organization",
            "name": APP_NAME,
            "url": site_url,
            "logo": _absolute_asset_url("logo.png"),
        },
    }


def build_robots_txt() -> str:
    """Return robots.txt content for search engine crawlers."""

    sitemap_url = f"{SITE_URL.rstrip('/')}/sitemap.xml"

    return f"""User-agent: *
Allow: /

Disallow: /webhooks/

Sitemap: {sitemap_url}
"""


def build_sitemap_xml() -> str:
    """Return sitemap.xml content for the public marketing site."""

    site_url = SITE_URL.rstrip("/")
    lastmod = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    urls = [
        {"loc": f"{site_url}/", "changefreq": "weekly", "priority": "1.0"},
    ]

    url_entries = "\n".join(
        f"""  <url>
    <loc>{entry['loc']}</loc>
    <lastmod>{lastmod}</lastmod>
    <changefreq>{entry['changefreq']}</changefreq>
    <priority>{entry['priority']}</priority>
  </url>"""
        for entry in urls
    )

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{url_entries}
</urlset>
"""


def write_static_seo_files() -> None:
    """Write robots.txt and sitemap.xml into the static directory."""

    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    (STATIC_DIR / "robots.txt").write_text(build_robots_txt(), encoding="utf-8")
    (STATIC_DIR / "sitemap.xml").write_text(build_sitemap_xml(), encoding="utf-8")


def _head_tags() -> list[dict[str, str]]:
    og_image = _absolute_asset_url("og-image.png")
    site_url = SITE_URL.rstrip("/")

    return [
        {"tag": "meta", "name": "description", "content": SEO_DESCRIPTION},
        {"tag": "meta", "property": "og:title", "content": SEO_OG_TITLE},
        {"tag": "meta", "property": "og:description", "content": SEO_OG_DESCRIPTION},
        {"tag": "meta", "property": "og:image", "content": og_image},
        {"tag": "meta", "property": "og:url", "content": site_url},
        {"tag": "meta", "property": "og:type", "content": "website"},
        {"tag": "meta", "name": "twitter:card", "content": "summary_large_image"},
        {"tag": "meta", "name": "twitter:title", "content": SEO_OG_TITLE},
        {"tag": "meta", "name": "twitter:description", "content": SEO_TWITTER_DESCRIPTION},
        {"tag": "meta", "name": "twitter:image", "content": og_image},
        {
            "tag": "link",
            "rel": "icon",
            "type": "image/png",
            "href": _absolute_asset_url("favicon.png"),
        },
        {
            "tag": "link",
            "rel": "apple-touch-icon",
            "href": _absolute_asset_url("logo.png"),
        },
    ]


def inject_seo_head() -> None:
    """Inject SEO, Open Graph, Twitter, and JSON-LD tags into document.head."""

    tags = _head_tags()
    tags_json = json.dumps(tags)
    json_ld = json.dumps(structured_data(), ensure_ascii=False)

    components.html(
        f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8" /></head>
<body>
<script>
(function () {{
  const tags = {tags_json};
  tags.forEach((spec) => {{
    const tagName = spec.tag;
    const attrs = {{ ...spec }};
    delete attrs.tag;
    const existingSelector = tagName === "meta"
      ? (attrs.name ? `meta[name="${{attrs.name}}"]` : `meta[property="${{attrs.property}}"]`)
      : `link[rel="${{attrs.rel}}"]`;
    if (document.head.querySelector(existingSelector)) {{
      return;
    }}
    const el = document.createElement(tagName);
    Object.entries(attrs).forEach(([key, value]) => el.setAttribute(key, value));
    document.head.appendChild(el);
  }});

  if (!document.head.querySelector('script[data-datadumpai-jsonld="software-application"]')) {{
    const jsonLd = {json_ld};
    const script = document.createElement("script");
    script.type = "application/ld+json";
    script.setAttribute("data-datadumpai-jsonld", "software-application");
    script.textContent = JSON.stringify(jsonLd);
    document.head.appendChild(script);
  }}
}})();
</script>
</body>
</html>
""",
        height=0,
        width=0,
    )
