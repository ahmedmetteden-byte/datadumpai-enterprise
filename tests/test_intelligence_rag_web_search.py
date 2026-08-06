"""
Tests for live web search blending into Intelligence Studio's RAG answers.

Ask AI previously only ever searched the workspace's indexed documents —
questions about recent/external events (e.g. "the latest update on X as of
August 2026") had no path to get real information, since the web search
service that existed in the codebase was wired into an old, disconnected
use case rather than the RAG service the FastAPI SPA actually calls.
"""

from __future__ import annotations

from models.web_source import WebSource
from services.intelligence_rag_service import IntelligenceRagService


def test_search_web_degrades_gracefully_when_package_missing(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(
        "services.intelligence_rag_service.WebSearchService.is_available",
        staticmethod(lambda: False),
    )
    service = IntelligenceRagService()

    results, notice = service._search_web("insurance recapitalization update")

    assert results == []
    assert notice is not None
    assert "not installed" in notice.lower()


def test_search_web_degrades_gracefully_when_search_raises(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(
        "services.intelligence_rag_service.WebSearchService.is_available",
        staticmethod(lambda: True),
    )

    def _boom(self, query, *, max_results=5):
        raise RuntimeError("network unreachable")

    monkeypatch.setattr(
        "services.intelligence_rag_service.WebSearchService.search", _boom
    )
    service = IntelligenceRagService()

    results, notice = service._search_web("insurance recapitalization update")

    assert results == []
    assert notice == "network unreachable"


def test_search_web_returns_results_on_success(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(
        "services.intelligence_rag_service.WebSearchService.is_available",
        staticmethod(lambda: True),
    )
    expected = [WebSource(title="Update", url="https://example.com", snippet="...")]

    def _fake_search(self, query, *, max_results=5):
        assert max_results == 5
        return expected

    monkeypatch.setattr(
        "services.intelligence_rag_service.WebSearchService.search", _fake_search
    )
    service = IntelligenceRagService()

    results, notice = service._search_web("insurance recapitalization update")

    assert results == expected
    assert notice is None
