"""
Executive Copilot Use Case

Project-aware Q&A grounded in the active workspace, with optional web search.
"""

from __future__ import annotations

from config import WEB_SEARCH_MAX_RESULTS
from models.copilot_result import CopilotResult
from models.web_source import WebSource
from services.ai_service import AIService
from services.copilot_context_service import CopilotContextService
from services.plan_service import PlanService
from services.web_search_service import WebSearchService


class AskCopilotUseCase:
    """
    Answer executive questions using the active workspace and the public web.
    """

    def __init__(
        self,
        context_service: CopilotContextService | None = None,
        ai_service: AIService | None = None,
        web_search_service: WebSearchService | None = None,
        plan_service: PlanService | None = None,
    ) -> None:
        self._context = context_service or CopilotContextService()
        self._ai = ai_service or AIService()
        self._web_search = web_search_service or WebSearchService()
        self._plans = plan_service or PlanService()

    def execute(
        self,
        *,
        project_id: str,
        question: str,
        focus_report: dict | None = None,
    ) -> CopilotResult:
        deep_context = self._plans.can_use_deep_copilot()
        web_enabled = self._plans.can_use_web_research()

        workspace, context, sources = self._context.build(
            project_id=project_id,
            question=question,
            focus_report=focus_report,
            include_saved_knowledge=self._plans.can_use_saved_ai_knowledge(),
        )

        web_sources: list[WebSource] = []
        web_context = ""
        notice: str | None = None

        if web_enabled:
            try:
                web_sources = self._web_search.search(
                    question,
                    max_results=WEB_SEARCH_MAX_RESULTS,
                )
                web_context = WebSearchService.format_for_prompt(web_sources)
            except RuntimeError as exc:
                notice = str(exc)
        elif not deep_context:
            notice = (
                "Live internet research is available on the Professional plan. "
                "This answer uses your workspace documents only."
            )

        if not context.strip() and not web_sources:
            if notice:
                return CopilotResult(
                    answer=(
                        "I could not search the web because the search package is "
                        "not installed in this Python environment, and there are no "
                        "relevant documents in this workspace. "
                        f"{notice}"
                    ) if web_enabled else (
                        "I could not find relevant information in this workspace for "
                        f"that question. {notice}"
                    ),
                    project_name=workspace.name,
                    sources=[],
                    web_sources=[],
                    notice=notice,
                )

            return CopilotResult(
                answer=(
                    "I could not find relevant information in this workspace "
                    + ("or on the web " if web_enabled else "")
                    + "for that question. Try rephrasing it, or upload "
                    "documents that may contain the answer."
                ),
                project_name=workspace.name,
                sources=[],
                web_sources=[],
            )

        answer = self._ai.answer_question(
            context=context,
            question=question,
            project_name=workspace.name,
            web_context=web_context,
            deep_context=deep_context,
        )

        if notice and not web_sources and web_enabled:
            answer = (
                f"{answer}\n\n---\n*Web search was unavailable for this answer. "
                f"{notice}*"
            )

        try:
            from services.activity_service import ActivityService

            ActivityService().log(
                "copilot.asked",
                f'Asked AI "{question[:120]}"',
                metadata={"project_id": project_id},
            )
        except Exception:
            pass

        return CopilotResult(
            answer=answer,
            project_name=workspace.name,
            sources=sources,
            web_sources=web_sources,
            notice=notice,
        )
