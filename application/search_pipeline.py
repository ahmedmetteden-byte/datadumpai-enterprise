"""
DataDumpAI Enterprise
Search Pipeline
"""

from __future__ import annotations

from models.search_result import SearchResult
from services.search_service import SearchService


class SearchPipeline:
    """
    Orchestrates enterprise search workflows.

    Provides a single entry point for searching projects, documents,
    and reports across the organization.
    """

    def __init__(
        self,
        search_service: SearchService | None = None,
    ) -> None:
        self._search_service = search_service or SearchService()

    def search(
        self,
        query: str,
        *,
        project_id: str | None = None,
        max_results: int = 20,
    ) -> list[SearchResult]:
        """
        Run enterprise search across projects, documents, and reports.

        When ``project_id`` is provided, search is scoped to that project.
        Otherwise, search runs organization-wide.
        """

        return self._search_service.enterprise_search(
            query,
            project_id=project_id,
            max_results=max_results,
        )

    def search_documents(
        self,
        project_id: str,
        query: str,
    ) -> list[dict]:
        """Search project documents and return matching files."""

        return self._search_service.search(
            project_id,
            query,
        )

    def search_excerpts(
        self,
        project_id: str,
        query: str,
    ) -> list[dict]:
        """Search project documents and return relevant excerpts."""

        return self._search_service.search_excerpts(
            project_id,
            query,
        )
