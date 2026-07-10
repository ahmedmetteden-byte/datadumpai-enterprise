"""
DataDumpAI Enterprise
Search Service

Enterprise keyword search across projects, documents, and reports.
"""

from __future__ import annotations

import re
from pathlib import Path

from PyPDF2 import PdfReader

from core.user_paths import get_user_projects_root
from models.search_result import SearchResult
from repositories.project_repository import ProjectRepository
from services.document_processor import DocumentProcessor


class SearchService:
    """
    Enterprise search across the full DataDumpAI knowledge base.

    Searches every project, uploaded document, and generated report.
    Designed as the backbone for AI Copilot, report comparison, and
    organization-wide knowledge retrieval.
    """

    @staticmethod
    def _root() -> Path:
        return get_user_projects_root(SearchService._current_user_id())

    @staticmethod
    def _current_user_id() -> str:
        from core.auth import get_current_user_id

        return get_current_user_id()

    def __init__(
        self,
        project_repository: ProjectRepository | None = None,
    ) -> None:
        self._projects = project_repository or ProjectRepository()

    def search(
        self,
        project_id: str,
        query: str,
    ) -> list[dict]:
        """Return documents whose full text matches the query."""

        return [
            result.to_dict()
            for result in self.enterprise_search(
                query,
                project_id=project_id,
            )
            if result.source_type == "document"
        ]

    def search_excerpts(
        self,
        project_id: str,
        query: str,
        *,
        max_excerpts: int = 8,
        excerpt_length: int = 800,
    ) -> list[dict]:
        """
        Return relevant excerpts for AI Copilot and legacy callers.

        Maps enterprise search hits into the excerpt shape expected by
        ChatPipeline.
        """

        results = self.enterprise_search(
            query,
            project_id=project_id,
            max_results=max_excerpts,
        )

        excerpts = []

        for result in results:

            if result.source_type == "project":
                continue

            excerpts.append(
                {
                    "filename": result.title,
                    "path": result.path,
                    "excerpt": result.excerpt[:excerpt_length],
                    "location": result.location,
                    "project_name": result.project_name,
                }
            )

        return excerpts

    def enterprise_search(
        self,
        query: str,
        *,
        project_id: str | None = None,
        max_results: int = 20,
    ) -> list[SearchResult]:
        """
        Search projects, documents, and reports for a query.

        Returns structured hits with source title and location labels such
        as ``Page 12``, ``Paragraph 8``, or ``Recommendations``.
        """

        query_lower = query.strip().lower()

        if not query_lower:
            return []

        keywords = self._keywords(query_lower)
        results: list[SearchResult] = []

        for project in self._projects.all():

            if project_id and project.get("id") != project_id:
                continue

            project_name = project.get("name", "Untitled Project")
            current_project_id = project["id"]

            if self._text_matches(
                f"{project.get('name', '')} {project.get('description', '')}",
                query_lower,
                keywords,
            ):
                results.append(
                    SearchResult(
                        source_type="project",
                        title=project_name,
                        location="Project",
                        excerpt=project.get("description", project_name),
                        project_id=current_project_id,
                        project_name=project_name,
                    )
                )

            results.extend(
                self._search_documents(
                    current_project_id,
                    project_name,
                    query_lower,
                    keywords,
                    max_results=max_results - len(results),
                )
            )

            results.extend(
                self._search_reports(
                    current_project_id,
                    project_name,
                    query_lower,
                    keywords,
                    max_results=max_results - len(results),
                )
            )

            if len(results) >= max_results:
                break

        return results[:max_results]

    def _search_documents(
        self,
        project_id: str,
        project_name: str,
        query_lower: str,
        keywords: list[str],
        *,
        max_results: int,
    ) -> list[SearchResult]:
        """Search uploaded documents within a project."""

        if max_results <= 0:
            return []

        folder = self._root() / project_id / "documents"

        if not folder.exists():
            return []

        results: list[SearchResult] = []

        for file in sorted(folder.iterdir()):

            if not file.is_file():
                continue

            if file.suffix.lower() == ".pdf":
                results.extend(
                    self._search_pdf(
                        file,
                        project_id,
                        project_name,
                        query_lower,
                        keywords,
                        max_results=max_results - len(results),
                    )
                )
            else:
                results.extend(
                    self._search_text_file(
                        file,
                        project_id,
                        project_name,
                        query_lower,
                        keywords,
                        source_type="document",
                        max_results=max_results - len(results),
                    )
                )

            if len(results) >= max_results:
                break

        return results[:max_results]

    def _search_reports(
        self,
        project_id: str,
        project_name: str,
        query_lower: str,
        keywords: list[str],
        *,
        max_results: int,
    ) -> list[SearchResult]:
        """Search generated reports within a project."""

        if max_results <= 0:
            return []

        folder = self._root() / project_id / "reports"

        if not folder.exists():
            return []

        results: list[SearchResult] = []

        for file in sorted(folder.glob("*.md")):

            title = self._report_title(file)

            try:
                text = file.read_text(encoding="utf-8")
            except Exception:
                continue

            results.extend(
                self._search_markdown(
                    text,
                    title=title,
                    project_id=project_id,
                    project_name=project_name,
                    path=str(file),
                    query_lower=query_lower,
                    keywords=keywords,
                    max_results=max_results - len(results),
                )
            )

            if len(results) >= max_results:
                break

        return results[:max_results]

    def _search_pdf(
        self,
        file: Path,
        project_id: str,
        project_name: str,
        query_lower: str,
        keywords: list[str],
        *,
        max_results: int,
    ) -> list[SearchResult]:
        """Search a PDF page by page."""

        results: list[SearchResult] = []

        try:
            reader = PdfReader(str(file))
        except Exception:
            return results

        title = file.stem.replace("_", " ")

        for page_number, page in enumerate(reader.pages, start=1):

            text = page.extract_text() or ""

            if not self._text_matches(text, query_lower, keywords):
                continue

            results.append(
                SearchResult(
                    source_type="document",
                    title=title,
                    location=f"Page {page_number}",
                    excerpt=self._excerpt(text),
                    project_id=project_id,
                    project_name=project_name,
                    path=str(file),
                )
            )

            if len(results) >= max_results:
                break

        return results

    def _search_text_file(
        self,
        file: Path,
        project_id: str,
        project_name: str,
        query_lower: str,
        keywords: list[str],
        *,
        source_type: str,
        max_results: int,
    ) -> list[SearchResult]:
        """Search a non-PDF document by paragraph."""

        try:
            text = DocumentProcessor.extract_text_from_path(file)
        except Exception:
            return []

        title = file.stem.replace("_", " ")

        return self._search_paragraphs(
            text,
            title=title,
            project_id=project_id,
            project_name=project_name,
            path=str(file),
            query_lower=query_lower,
            keywords=keywords,
            source_type=source_type,
            max_results=max_results,
        )

    def _search_markdown(
        self,
        text: str,
        *,
        title: str,
        project_id: str,
        project_name: str,
        path: str,
        query_lower: str,
        keywords: list[str],
        max_results: int,
    ) -> list[SearchResult]:
        """Search a markdown report by section and paragraph."""

        results: list[SearchResult] = []
        sections = re.split(r"(?m)^##\s+", text)

        if len(sections) <= 1:
            return self._search_paragraphs(
                text,
                title=title,
                project_id=project_id,
                project_name=project_name,
                path=path,
                query_lower=query_lower,
                keywords=keywords,
                source_type="report",
                max_results=max_results,
            )

        for section_number, section in enumerate(sections[1:], start=1):

            lines = section.split("\n", 1)
            section_title = lines[0].strip()
            section_body = lines[1] if len(lines) > 1 else section_title

            if not self._text_matches(
                section_body,
                query_lower,
                keywords,
            ):
                continue

            location = section_title or f"Section {section_number}"

            results.append(
                SearchResult(
                    source_type="report",
                    title=title,
                    location=location,
                    excerpt=self._excerpt(section_body),
                    project_id=project_id,
                    project_name=project_name,
                    path=path,
                )
            )

            if len(results) >= max_results:
                break

        return results

    def _search_paragraphs(
        self,
        text: str,
        *,
        title: str,
        project_id: str,
        project_name: str,
        path: str,
        query_lower: str,
        keywords: list[str],
        source_type: str,
        max_results: int,
    ) -> list[SearchResult]:
        """Search plain text content paragraph by paragraph."""

        paragraphs = [
            paragraph.strip()
            for paragraph in text.split("\n\n")
            if paragraph.strip()
        ]

        if not paragraphs:
            paragraphs = [
                line.strip()
                for line in text.split("\n")
                if line.strip()
            ]

        results: list[SearchResult] = []

        for paragraph_number, paragraph in enumerate(paragraphs, start=1):

            if not self._text_matches(paragraph, query_lower, keywords):
                continue

            results.append(
                SearchResult(
                    source_type=source_type,
                    title=title,
                    location=f"Paragraph {paragraph_number}",
                    excerpt=self._excerpt(paragraph),
                    project_id=project_id,
                    project_name=project_name,
                    path=path,
                )
            )

            if len(results) >= max_results:
                break

        return results

    def _keywords(self, query_lower: str) -> list[str]:
        """Return significant query terms."""

        return [
            word
            for word in re.findall(r"[a-z0-9]+", query_lower)
            if len(word) > 2
        ]

    def _text_matches(
        self,
        text: str,
        query_lower: str,
        keywords: list[str],
    ) -> bool:
        """Return True when text matches the query or its keywords."""

        text_lower = text.lower()

        if query_lower in text_lower:
            return True

        return any(keyword in text_lower for keyword in keywords)

    def _excerpt(self, text: str, length: int = 240) -> str:
        """Return a compact preview string."""

        cleaned = " ".join(text.split())

        if len(cleaned) <= length:
            return cleaned

        return f"{cleaned[: length - 3].rstrip()}..."

    def _report_title(self, file: Path) -> str:
        """Return a display title for a report file."""

        return file.stem.replace("_", " ").title()

    def _matching_passages(
        self,
        text: str,
        *,
        query_lower: str,
        keywords: list[str],
        excerpt_length: int,
    ) -> list[str]:
        """Extract passages from text that match the query or keywords."""

        paragraphs = [
            paragraph.strip()
            for paragraph in text.split("\n\n")
            if paragraph.strip()
        ]

        if not paragraphs:
            paragraphs = [
                line.strip()
                for line in text.split("\n")
                if line.strip()
            ]

        matches: list[str] = []

        for paragraph in paragraphs:
            if self._text_matches(paragraph, query_lower, keywords):
                matches.append(paragraph[:excerpt_length])

        return matches
