"""
Tests for WebSearchService.
"""

from __future__ import annotations

from models.web_source import WebSource
from services.web_search_service import WebSearchService


def test_format_for_prompt_includes_urls():
    sources = [
        WebSource(
            title="Nigeria inflation data",
            url="https://example.com/inflation",
            snippet="Inflation eased to 23%.",
        )
    ]

    formatted = WebSearchService.format_for_prompt(sources)

    assert "WEB SEARCH RESULTS" in formatted
    assert "https://example.com/inflation" in formatted
    assert "Nigeria inflation data" in formatted


def test_search_returns_empty_for_blank_query():
    service = WebSearchService()

    assert service.search("   ") == []


def test_search_uses_provider(monkeypatch):
    service = WebSearchService()

    class FakeDDGS:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def text(self, query, max_results=5):
            assert query == "Nigeria inflation rate"
            assert max_results == 2
            return [
                {
                    "title": "Inflation update",
                    "href": "https://example.com/rate",
                    "body": "Current inflation is 23%.",
                }
            ]

    fake_module = type("module", (), {"DDGS": FakeDDGS})

    monkeypatch.setitem(__import__("sys").modules, "ddgs", fake_module)
    monkeypatch.setitem(
        __import__("sys").modules,
        "duckduckgo_search",
        type("module", (), {}),
    )

    results = service.search("Nigeria inflation rate", max_results=2)

    assert len(results) == 1
    assert results[0].url == "https://example.com/rate"
    assert results[0].title == "Inflation update"


def test_search_raises_when_package_missing(monkeypatch):
    service = WebSearchService()
    monkeypatch.setattr(
        "services.web_search_service._load_ddgs_class",
        lambda: None,
    )

    try:
        service.search("Nigeria inflation rate")
        raised = False
    except RuntimeError as exc:
        raised = True
        assert "ddgs" in str(exc).lower()

    assert raised


def test_is_available_reflects_installed_package(monkeypatch):
    monkeypatch.setattr(
        "services.web_search_service._load_ddgs_class",
        lambda: None,
    )
    assert WebSearchService.is_available() is False
