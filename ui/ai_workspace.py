"""
AI Workspace — conversational front-end for report and analysis actions.

Routes natural-language requests to existing report-generation capabilities.
The section id remains ``documents`` for backward-compatible routing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable

import streamlit as st

from ui.document_library import render_document_upload
from ui.projects import (
    get_active_workspace,
    get_user_projects,
    initialize_projects,
)
from ui.report_generation import (
    render_document_source_selection,
    render_documents_page_generation,
)

AI_WORKSPACE_PROMPT_KEY = "ai_workspace_prompt"
AI_WORKSPACE_MESSAGES_KEY = "ai_workspace_messages"
AI_WORKSPACE_INSTRUCTION_KEY = "ai_workspace_instruction"


@dataclass(frozen=True)
class AIWorkspaceAction:
    """First-class action that can grow without another navigation redesign."""

    id: str
    label: str
    icon: str
    prompt: str
    report_type: str | None = None
    status: str = "available"  # available | coming_soon


AI_WORKSPACE_ACTIONS: tuple[AIWorkspaceAction, ...] = (
    AIWorkspaceAction(
        "executive_report",
        "Executive Report",
        "📊",
        "Generate an executive report.",
        "Executive Summary",
    ),
    AIWorkspaceAction(
        "summarize",
        "Summarize",
        "📄",
        "Summarize this document in one page.",
        "Executive Summary",
    ),
    AIWorkspaceAction(
        "board_pack",
        "Board Pack",
        "📑",
        "Generate a board-ready report.",
        "Board Report",
    ),
    AIWorkspaceAction(
        "compare",
        "Compare",
        "⚖️",
        "Compare these two reports.",
        "Full Report",
    ),
    AIWorkspaceAction(
        "me_framework",
        "M&E Framework",
        "📐",
        "Build a monitoring and evaluation framework.",
        "Strategic Planning Report",
    ),
    AIWorkspaceAction(
        "visual_insights",
        "Visual Insights",
        "📈",
        "Explore visual insights for this workspace.",
        None,
        status="coming_soon",
    ),
    AIWorkspaceAction(
        "swot",
        "SWOT Analysis",
        "🎯",
        "Generate a SWOT analysis.",
        None,
        status="coming_soon",
    ),
    AIWorkspaceAction(
        "risk_register",
        "Risk Register",
        "🛡️",
        "Build a risk register.",
        "Risk Assessment Report",
    ),
    AIWorkspaceAction(
        "presentation",
        "Presentation",
        "📽️",
        "Create a presentation deck.",
        None,
        status="coming_soon",
    ),
)

_INTENT_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bexecutive\b", re.I), "Executive Summary"),
    (re.compile(r"\bboard\b", re.I), "Board Report"),
    (re.compile(r"\bfinancial\b", re.I), "Financial Analysis"),
    (re.compile(r"\brisk\b", re.I), "Risk Assessment Report"),
    (re.compile(r"\bmeeting\b", re.I), "Meeting Intelligence Report"),
    (re.compile(r"\bmarket\b", re.I), "Market Intelligence Report"),
    (re.compile(r"\bstrategic\b", re.I), "Strategic Planning Report"),
    (re.compile(r"\bmanagement\b", re.I), "Management Report"),
    (re.compile(r"\bcompliance\b|\bregulatory\b", re.I), "Regulatory Compliance Report"),
    (re.compile(r"\bmonitoring\b|\bevaluation\b|\bm&e\b", re.I), "Strategic Planning Report"),
    (re.compile(r"\bcompare\b", re.I), "Full Report"),
    (re.compile(r"\bsummar", re.I), "Executive Summary"),
    (re.compile(r"\bone page\b", re.I), "Executive Summary"),
    (re.compile(r"\bfull report\b", re.I), "Full Report"),
    (re.compile(r"\bdashboard\b", re.I), "Executive Intelligence Dashboard"),
)


def parse_prompt_intent(prompt: str) -> tuple[str | None, str]:
    """Map a natural-language request to a report type when possible."""

    cleaned = prompt.strip()
    if not cleaned:
        return None, ""

    for pattern, report_type in _INTENT_RULES:
        if pattern.search(cleaned):
            return report_type, cleaned

    return None, cleaned


def _append_message(role: str, content: str) -> None:
    messages = list(st.session_state.get(AI_WORKSPACE_MESSAGES_KEY, []))
    messages.append({"role": role, "content": content})
    st.session_state[AI_WORKSPACE_MESSAGES_KEY] = messages[-12:]


def _apply_action(action: AIWorkspaceAction) -> None:
    st.session_state[AI_WORKSPACE_PROMPT_KEY] = action.prompt
    st.session_state[AI_WORKSPACE_INSTRUCTION_KEY] = action.prompt
    if action.report_type:
        st.session_state["selected_report_type"] = action.report_type
    _append_message("user", action.prompt)
    if action.status == "coming_soon":
        _append_message(
            "assistant",
            f"**{action.label}** is on the roadmap. For now, use an available action "
            "or describe your request below — report generation is fully supported.",
        )
    else:
        _append_message(
            "assistant",
            f"Ready to **{action.label.lower()}**. Select documents in Advanced Options "
            "if needed, then run your request.",
        )


def _handle_prompt_submit(prompt: str) -> None:
    cleaned = prompt.strip()
    if not cleaned:
        return

    report_type, instruction = parse_prompt_intent(cleaned)
    st.session_state[AI_WORKSPACE_INSTRUCTION_KEY] = instruction
    _append_message("user", cleaned)

    if report_type:
        st.session_state["selected_report_type"] = report_type
        _append_message(
            "assistant",
            f"Understood. I'll prepare a **{report_type}** based on your request. "
            "Confirm document selection in **Advanced Options**, then generate.",
        )
    else:
        _append_message(
            "assistant",
            "Got it. Open **Advanced Options** to choose documents and a report type, "
            "or try a quick action above.",
        )


def _render_action_chips(on_action: Callable[[AIWorkspaceAction], None]) -> None:
    st.markdown('<div class="dde-ai-action-grid">', unsafe_allow_html=True)
    columns = st.columns(3)
    for index, action in enumerate(AI_WORKSPACE_ACTIONS):
        with columns[index % 3]:
            label = f"{action.icon} {action.label}"
            if action.status == "coming_soon":
                st.button(
                    label,
                    key=f"ai_action_{action.id}",
                    use_container_width=True,
                    disabled=True,
                    help="Coming soon",
                )
            elif st.button(
                label,
                key=f"ai_action_{action.id}",
                use_container_width=True,
            ):
                on_action(action)
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def _render_conversation() -> None:
    messages = st.session_state.get(AI_WORKSPACE_MESSAGES_KEY, [])
    if not messages:
        st.markdown(
            """
<div class="dde-ai-empty-state">
<div class="dde-ai-empty-title">What would you like to create?</div>
<div class="dde-ai-empty-copy">
Ask in plain language, pick a quick action, or open Advanced Options for full control.
</div>
</div>
""",
            unsafe_allow_html=True,
        )
        return

    st.markdown('<div class="dde-ai-thread">', unsafe_allow_html=True)
    for index, message in enumerate(messages):
        role = message.get("role", "assistant")
        css_class = "dde-ai-message-user" if role == "user" else "dde-ai-message-assistant"
        st.markdown(
            f'<div class="{css_class}">{message.get("content", "")}</div>',
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)


def render_ai_workspace() -> None:
    """Render the AI-first workspace experience."""

    initialize_projects()
    workspace = get_active_workspace()
    user_projects = get_user_projects()

    if workspace.get("is_pending"):
        st.markdown("## AI Workspace")
        st.info(
            "Select **Project** in the sidebar and create your project to start working "
            "with your documents."
        )
        return

    st.markdown("## AI Workspace")
    if workspace.get("is_quick_report"):
        st.caption(
            "Ask questions, generate reports, and run analysis on your documents. "
            "You are in **Quick Report** mode."
        )
    else:
        st.caption(
            f"Ask questions, generate reports, and run analysis inside "
            f"**{workspace['name']}**."
        )

    _render_action_chips(_apply_action)
    _render_conversation()

    st.markdown('<div class="dde-ai-composer">', unsafe_allow_html=True)
    prompt = st.text_area(
        "Ask DataDumpAI",
        value=st.session_state.get(AI_WORKSPACE_PROMPT_KEY, ""),
        placeholder=(
            "e.g. Summarize this document in one page. "
            "Generate an executive report. Compare these two reports."
        ),
        key="ai_workspace_prompt_input",
        height=96,
        label_visibility="collapsed",
    )

    send_col, clear_col = st.columns([3, 1])
    with send_col:
        if st.button(
            "Run request",
            type="primary",
            use_container_width=True,
            key="ai_workspace_send",
        ):
            st.session_state[AI_WORKSPACE_PROMPT_KEY] = prompt
            _handle_prompt_submit(prompt)
            st.rerun()
    with clear_col:
        if st.button("Clear", use_container_width=True, key="ai_workspace_clear"):
            st.session_state.pop(AI_WORKSPACE_PROMPT_KEY, None)
            st.session_state.pop(AI_WORKSPACE_INSTRUCTION_KEY, None)
            st.session_state[AI_WORKSPACE_MESSAGES_KEY] = []
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    instruction = st.session_state.get(AI_WORKSPACE_INSTRUCTION_KEY)
    if instruction:
        st.caption(f"Active request: _{instruction}_")

    with st.expander("Advanced Options", expanded=False):
        st.caption(
            "Upload documents, choose sources, pick report types, and configure "
            "generation — all existing capabilities live here."
        )
        render_document_upload()
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        document_selection = render_document_source_selection(user_projects, workspace)
        st.markdown("---")
        render_documents_page_generation(user_projects, document_selection)
