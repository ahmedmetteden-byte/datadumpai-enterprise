"""
DataDumpAI Enterprise
Chat Pipeline

Orchestrates AI Copilot Q&A grounded in project documents.
"""

from __future__ import annotations

from services.ai_service import AIService
from services.search_service import SearchService


class ChatPipeline:
    """
    Coordinates the AI Copilot workflow.

    The pipeline:
    1. Searches the current project's documents for relevant excerpts
    2. Sends only those excerpts to GPT
    3. Returns an answer grounded in project sources
    """

    def __init__(
        self,
        search_service: SearchService | None = None,
        ai_service: AIService | None = None,
    ) -> None:
        self._search_service = search_service or SearchService()
        self._ai_service = ai_service or AIService()

    def ask(
        self,
        *,
        project_id: str,
        question: str,
    ) -> tuple[str, list[dict]]:
        """
        Answer a question using documents from the active project.

        Returns:
            The generated answer and the excerpts used as context.
        """

        excerpts = self._search_service.search_excerpts(
            project_id,
            question,
        )

        if not excerpts:

            return (
                "I couldn't find any relevant information in this "
                "project's documents for that question.",
                [],
            )

        answer = self._ai_service.answer_from_excerpts(
            question=question,
            excerpts=excerpts,
        )

        return answer, excerpts
