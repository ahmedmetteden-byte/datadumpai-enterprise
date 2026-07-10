"""
SEO metadata injection tests.
"""

from __future__ import annotations

from ui.seo import _head_tags, build_robots_txt, build_sitemap_xml, structured_data


def test_head_tags_include_description_and_open_graph():
    tags = _head_tags()

    descriptions = [t for t in tags if t.get("name") == "description"]
    og_images = [t for t in tags if t.get("property") == "og:image"]
    twitter_cards = [t for t in tags if t.get("name") == "twitter:card"]

    assert descriptions
    assert "executive reports" in descriptions[0]["content"].lower()
    assert og_images
    assert og_images[0]["content"].endswith("/og-image.png")
    assert twitter_cards[0]["content"] == "summary_large_image"


def test_structured_data_uses_schema_org_software_application():
    data = structured_data()

    assert data["@context"] == "https://schema.org"
    assert data["@type"] == "SoftwareApplication"
    assert data["name"] == "DataDumpAI"
    assert data["applicationCategory"] == "BusinessApplication"
    assert data["operatingSystem"] == "Web"
    assert data["url"].startswith("https://")
    assert "document intelligence" in data["description"].lower()


def test_robots_txt_points_to_sitemap():
    robots = build_robots_txt()

    assert "User-agent: *" in robots
    assert "Allow: /" in robots
    assert "Sitemap: https://" in robots
    assert robots.strip().endswith("/sitemap.xml")


def test_sitemap_xml_includes_homepage():
    sitemap = build_sitemap_xml()

    assert '<?xml version="1.0"' in sitemap
    assert "<urlset" in sitemap
    assert "<loc>https://" in sitemap
    assert "</urlset>" in sitemap
