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

PRIMARY_ACTION_IDS: frozenset[str] = frozenset(
    {"executive_report", "summarize", "board_pack", "compare"}
)


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


def _render_action_buttons(
    actions: tuple[AIWorkspaceAction, ...],
    on_action: Callable[[AIWorkspaceAction], None],
    *,
    key_prefix: str,
) -> None:
    if not actions:
        return

    st.markdown('<div class="dde-ai-action-row">', unsafe_allow_html=True)
    columns = st.columns(len(actions))
    for column, action in zip(columns, actions):
        with column:
            label = action.label
            if action.status == "coming_soon":
                st.button(
                    label,
                    key=f"{key_prefix}_{action.id}",
                    use_container_width=True,
                    disabled=True,
                    help="Coming soon",
                )
            elif st.button(
                label,
                key=f"{key_prefix}_{action.id}",
                use_container_width=True,
                type="secondary",
            ):
                on_action(action)
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def _render_prompt_hero(on_action: Callable[[AIWorkspaceAction], None]) -> None:
    st.markdown(
        """
<div class="dde-ai-prompt-hero">
<div class="dde-ai-prompt-title">What would you like to do today?</div>
</div>
""",
        unsafe_allow_html=True,
    )

    prompt_value = st.session_state.get(AI_WORKSPACE_PROMPT_KEY, "")

    with st.form("ai_workspace_prompt_form", clear_on_submit=False):
        input_col, send_col = st.columns([8, 1], gap="small", vertical_alignment="bottom")

        with input_col:
            prompt = st.text_input(
                "What would you like DataDumpAI to do?",
                value=prompt_value,
                placeholder="Summarize this document...",
                key="ai_workspace_prompt_input",
                label_visibility="collapsed",
            )

        with send_col:
            st.markdown('<div class="dde-ai-send-wrap">', unsafe_allow_html=True)
            submitted = st.form_submit_button(
                "+",
                type="primary",
                use_container_width=True,
                help="Run request",
            )
            st.markdown("</div>", unsafe_allow_html=True)

        if submitted:
            st.session_state[AI_WORKSPACE_PROMPT_KEY] = prompt
            _handle_prompt_submit(prompt)
            st.rerun()

    primary_actions = tuple(
        action for action in AI_WORKSPACE_ACTIONS if action.id in PRIMARY_ACTION_IDS
    )
    _render_action_buttons(primary_actions, on_action, key_prefix="ai_action_primary")

    secondary_actions = tuple(
        action
        for action in AI_WORKSPACE_ACTIONS
        if action.id not in PRIMARY_ACTION_IDS and action.status != "coming_soon"
    )
    if secondary_actions:
        _render_action_buttons(secondary_actions, on_action, key_prefix="ai_action_secondary")


def _render_conversation() -> None:
    messages = st.session_state.get(AI_WORKSPACE_MESSAGES_KEY, [])
    if not messages:
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
        st.info(
            "Select **Project** in the sidebar and create your project to start working "
            "with your documents."
        )
        return

    _render_prompt_hero(_apply_action)
    _render_conversation()

    instruction = st.session_state.get(AI_WORKSPACE_INSTRUCTION_KEY)
    if instruction:
        clear_col, caption_col = st.columns([1, 5])
        with clear_col:
            if st.button("Clear", key="ai_workspace_clear"):
                st.session_state.pop(AI_WORKSPACE_PROMPT_KEY, None)
                st.session_state.pop(AI_WORKSPACE_INSTRUCTION_KEY, None)
                st.session_state[AI_WORKSPACE_MESSAGES_KEY] = []
                st.rerun()
        with caption_col:
            st.caption(f"Active request: _{instruction}_")

    with st.expander("Advanced options", expanded=False):
        st.caption(
            "Upload documents, choose sources, pick report types, and configure "
            "generation — all existing capabilities live here."
        )
        render_document_upload()
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        document_selection = render_document_source_selection(user_projects, workspace)
        st.markdown("---")
        render_documents_page_generation(user_projects, document_selection)
