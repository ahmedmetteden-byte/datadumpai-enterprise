"""
Internet search for Ask AI.
"""

from __future__ import annotations

import logging
from typing import Any

from models.web_source import WebSource

logger = logging.getLogger(__name__)

_WEB_SEARCH_INSTALL_HINT = (
    "Install web search support with: pip install -r requirements.txt"
)


def _load_ddgs_class() -> type[Any] | None:
    """Return the DDGS client class from whichever search package is installed."""
    for module_name in ("ddgs", "duckduckgo_search"):
        try:
            module = __import__(module_name, fromlist=["DDGS"])
            return module.DDGS
        except ImportError:
            continue
    return None


class WebSearchService:
    """Search the public web and return citable sources."""

    def search(self, query: str, *, max_results: int = 5) -> list[WebSource]:
        query = query.strip()

        if not query:
            return []

        ddgs_cls = _load_ddgs_class()
        if ddgs_cls is None:
            raise RuntimeError(
                "Web search requires the ddgs package. "
                f"{_WEB_SEARCH_INSTALL_HINT}"
            )

        results: list[WebSource] = []

        try:
            with ddgs_cls() as ddgs:
                for item in ddgs.text(query, max_results=max_results):
                    url = (item.get("href") or item.get("url") or "").strip()
                    title = (item.get("title") or "Web result").strip()
                    snippet = (item.get("body") or item.get("snippet") or "").strip()

                    if not url:
                        continue

                    results.append(
                        WebSource(
                            title=title,
                            url=url,
                            snippet=snippet,
                        )
                    )
        except Exception as exc:
            logger.warning("Web search failed for %r: %s", query, exc)
            return []

        return results

    @staticmethod
    def format_for_prompt(sources: list[WebSource]) -> str:
        if not sources:
            return ""

        blocks = ["WEB SEARCH RESULTS"]

        for index, source in enumerate(sources, start=1):
            blocks.append(
                f"[{index}] {source.title}\n"
                f"URL: {source.url}\n"
                f"Snippet: {source.snippet}"
            )

        return "\n\n".join(blocks)

    @staticmethod
    def is_available() -> bool:
        return _load_ddgs_class() is not None
