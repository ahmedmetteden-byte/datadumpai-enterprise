"""
Tests for Ask Copilot with web search.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from application.use_cases.ask_copilot import AskCopilotUseCase
from models.web_source import WebSource
from services.plan_service import PlanService
from services.project_service import ProjectService
from services.usage_service import UsageService


def test_ask_copilot_uses_web_sources_when_workspace_is_empty(
    isolated_env,
    project_service: ProjectService,
):
    project = project_service.create_project("Web Copilot Project")

    usage = UsageService(storage_path=str(isolated_env["usage_json"]))
    usage.set_plan("professional")

    ai = MagicMock()
    ai.answer_question.return_value = (
        "Nigeria's inflation rate is about 23% according to recent data."
    )

    web_search = MagicMock()
    web_search.search.return_value = [
        WebSource(
            title="Nigeria inflation",
            url="https://example.com/inflation",
            snippet="Inflation stood at 23%.",
        )
    ]

    use_case = AskCopilotUseCase(
        ai_service=ai,
        web_search_service=web_search,
        plan_service=PlanService(usage),
    )

    result = use_case.execute(
        project_id=project["id"],
        question="What is the current inflation rate of Nigeria?",
    )

    assert "23%" in result.answer
    assert len(result.web_sources) == 1
    assert result.web_sources[0].url == "https://example.com/inflation"
    ai.answer_question.assert_called_once()
    assert "WEB SEARCH RESULTS" in ai.answer_question.call_args.kwargs["web_context"]


def test_ask_copilot_skips_web_search_on_free_plan(
    isolated_env,
    project_service: ProjectService,
):
    project = project_service.create_project("Free Copilot Project")

    usage = UsageService(storage_path=str(isolated_env["usage_json"]))

    ai = MagicMock()
    ai.answer_question.return_value = "Answer from workspace only."

    web_search = MagicMock()

    use_case = AskCopilotUseCase(
        ai_service=ai,
        web_search_service=web_search,
        plan_service=PlanService(usage),
    )

    result = use_case.execute(
        project_id=project["id"],
        question="What is the current inflation rate of Nigeria?",
    )

    web_search.search.assert_not_called()
    assert result.web_sources == []
    assert result.notice is not None
