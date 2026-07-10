"""
DataDumpAI v1.0
Ask AI — project Q&A with web search.
"""

from __future__ import annotations

import streamlit as st

from application.use_cases.ask_copilot import AskCopilotUseCase
from config import COPILOT_PROMPTS
from core.workspace import Workspace
from services.plan_service import PlanService
from ui.feedback import loading, show_error
from ui.plan_upgrade import render_upgrade_prompt
from ui.projects import get_current_project


def _ask_copilot() -> AskCopilotUseCase:
    return AskCopilotUseCase()


def _plan_service() -> PlanService:
    return PlanService()


def render_copilot() -> None:
    workspace = Workspace(get_current_project()["id"])

    st.markdown("## Ask AI")

    if _plan_service().can_use_deep_copilot():
        assistant_mode = (
            "Deep-context analyst — contradictions, comparisons, strategy, and citations."
        )
    else:
        assistant_mode = "Basic assistant — answers from your project documents."

    st.caption(
        f"Ask about **{workspace.name}**. {assistant_mode} "
        f"({workspace.document_count} documents, {workspace.report_count} reports)"
    )

    if not _plan_service().can_use_web_research():
        render_upgrade_prompt("web_research")

    focus_report = st.session_state.get("report_for_chat")

    if focus_report:
        clear_col, _ = st.columns([1, 4])

        with clear_col:
            if st.button("Clear report focus", use_container_width=True):
                st.session_state.pop("report_for_chat", None)
                st.rerun()

        st.info(f"Focused on report: **{focus_report.get('name', 'Report')}**")

    st.markdown("##### Quick questions")

    prompt_cols = st.columns(2)

    for index, example in enumerate(COPILOT_PROMPTS):
        with prompt_cols[index % 2]:
            if st.button(
                example,
                key=f"copilot_example_{index}",
                use_container_width=True,
            ):
                st.session_state.copilot_question = example

    default_question = st.session_state.get("copilot_question", "")

    question = st.text_area(
        "Your question",
        value=default_question,
        placeholder=(
            "Example: What is the current inflation rate in Nigeria?"
        ),
        height=120,
        label_visibility="collapsed",
    )

    if st.button("Ask AI", type="primary", use_container_width=True):
        if not question.strip():
            st.warning("Enter a question first.")
            return

        try:
            with loading("Searching your project and the web…"):
                result = _ask_copilot().execute(
                    project_id=workspace.project_id,
                    question=question.strip(),
                    focus_report=focus_report,
                )

            st.session_state.copilot_question = question.strip()
            st.session_state.copilot_answer = result.answer
            st.session_state.copilot_sources = result.sources
            st.session_state.copilot_web_sources = [
                {
                    "title": source.title,
                    "url": source.url,
                    "snippet": source.snippet,
                }
                for source in result.web_sources
            ]
            st.session_state.copilot_notice = result.notice
        except Exception as exc:
            show_error(exc)

    answer = st.session_state.get("copilot_answer")

    if answer:
        notice = st.session_state.get("copilot_notice")
        if notice:
            st.warning(notice)

        st.markdown("### Answer")
        st.markdown(answer)

        workspace_sources = st.session_state.get("copilot_sources", [])
        web_sources = st.session_state.get("copilot_web_sources", [])

        if workspace_sources:
            st.markdown("#### Project sources")
            for source in workspace_sources:
                st.markdown(f"- {source}")

        if web_sources:
            st.markdown("#### Web sources")
            for source in web_sources:
                title = source.get("title", "Web result")
                url = source.get("url", "")
                snippet = source.get("snippet", "")

                if url:
                    st.markdown(f"- [{title}]({url})")
                else:
                    st.markdown(f"- {title}")

                if snippet:
                    st.caption(snippet)
