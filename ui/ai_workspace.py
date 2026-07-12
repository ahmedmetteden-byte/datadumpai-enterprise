"""
AI Workspace — conversational front-end for knowledge-driven analysis.

Routes natural-language requests to existing report-generation capabilities.
The section id remains ``documents`` for backward-compatible routing.
"""

from __future__ import annotations

import re
from typing import Callable

import streamlit as st

from ui.document_library import (
    AI_WORKSPACE_ATTACH_BATCH_KEY,
    AI_WORKSPACE_ATTACH_KEY,
    SUPPORTED_TYPES,
    process_workspace_uploads,
)
from ui.projects import get_active_workspace, initialize_projects
from ui.ai_workspace_runtime import (
    AIWorkspaceSettings,
    AUTO_REPORT_TYPE,
    LANGUAGES,
    OUTPUT_LENGTHS,
    TONES,
    WorkspaceContextSummary,
    available_report_type_options,
    execute_workspace_request,
    list_workspace_context_filenames,
    summarize_workspace_context,
)

AI_WORKSPACE_PROMPT_KEY = "ai_workspace_prompt"
AI_WORKSPACE_MESSAGES_KEY = "ai_workspace_messages"
AI_WORKSPACE_ATTACH_OPEN_KEY = "ai_workspace_attach_open"
AI_WORKSPACE_SETTINGS_PREFIX = "ai_workspace_setting_"
AI_WORKSPACE_LAST_INFERENCE_KEY = "ai_workspace_last_inference"

PROMPT_HEADLINE = "What would you like DataDumpAI to do?"
PROMPT_SUBHEAD = "Ask anything about your documents — summarize, compare, extract, or generate."

PROMPT_EXAMPLES: tuple[str, ...] = (
    "Summarize this annual report",
    "Generate a Board paper",
    "Extract all KPIs",
    "Create a risk register",
    "Compare this with last year's report",
    "Build an M&E framework",
    "Produce a PowerPoint presentation",
)

SETTING_DEFAULTS: dict[str, object] = {
    "report_type": AUTO_REPORT_TYPE,
    "output_length": "Standard",
    "tone": "Professional",
    "language": "English",
    "include_charts": True,
    "custom_instructions": "",
}

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
    (re.compile(r"\bkpis?\b|\bkey performance\b", re.I), "Management Report"),
    (re.compile(r"\bswot\b", re.I), "Strategic Planning Report"),
    (re.compile(r"\brisk register\b", re.I), "Risk Assessment Report"),
)


def _excluded_state_key(workspace_id: str) -> str:
    return f"ai_workspace_excluded_{workspace_id}"


def get_excluded_filenames(workspace_id: str) -> set[str]:
    return set(st.session_state.get(_excluded_state_key(workspace_id), []))


def exclude_filename(workspace_id: str, filename: str) -> None:
    excluded = get_excluded_filenames(workspace_id)
    excluded.add(filename)
    st.session_state[_excluded_state_key(workspace_id)] = sorted(excluded)


def active_context_filenames(workspace: dict) -> list[str]:
    excluded = get_excluded_filenames(workspace["id"])
    return [
        filename
        for filename in list_workspace_context_filenames(workspace)
        if filename not in excluded
    ]


def parse_prompt_intent(prompt: str) -> tuple[str | None, str]:
    """Map a natural-language request to a report type when possible."""

    cleaned = prompt.strip()
    if not cleaned:
        return None, ""

    for pattern, report_type in _INTENT_RULES:
        if pattern.search(cleaned):
            return report_type, cleaned

    return None, cleaned


def _init_settings_state() -> None:
    for key, value in SETTING_DEFAULTS.items():
        state_key = f"{AI_WORKSPACE_SETTINGS_PREFIX}{key}"
        if state_key not in st.session_state:
            st.session_state[state_key] = value


def _read_settings() -> AIWorkspaceSettings:
    _init_settings_state()
    return AIWorkspaceSettings(
        report_type_override=st.session_state[f"{AI_WORKSPACE_SETTINGS_PREFIX}report_type"],
        output_length=st.session_state[f"{AI_WORKSPACE_SETTINGS_PREFIX}output_length"],
        tone=st.session_state[f"{AI_WORKSPACE_SETTINGS_PREFIX}tone"],
        language=st.session_state[f"{AI_WORKSPACE_SETTINGS_PREFIX}language"],
        include_charts=bool(
            st.session_state[f"{AI_WORKSPACE_SETTINGS_PREFIX}include_charts"]
        ),
        custom_instructions=st.session_state[
            f"{AI_WORKSPACE_SETTINGS_PREFIX}custom_instructions"
        ],
    )


def _append_message(role: str, content: str) -> None:
    messages = list(st.session_state.get(AI_WORKSPACE_MESSAGES_KEY, []))
    messages.append({"role": role, "content": content})
    st.session_state[AI_WORKSPACE_MESSAGES_KEY] = messages[-12:]


def _handle_prompt_submit(prompt: str, workspace: dict, context_files: list[str]) -> None:
    cleaned = prompt.strip()
    if not cleaned:
        return

    settings = _read_settings()
    prior_messages = list(st.session_state.get(AI_WORKSPACE_MESSAGES_KEY, []))

    _append_message("user", cleaned)

    result = execute_workspace_request(
        prompt=cleaned,
        workspace=workspace,
        settings=settings,
        context_filenames=context_files,
        conversation_messages=prior_messages,
    )

    if result.inference:
        st.session_state[AI_WORKSPACE_LAST_INFERENCE_KEY] = {
            "display_label": result.inference.display_label,
            "confidence": result.inference.confidence,
            "inferred": result.inference.inferred,
        }

    _append_message("assistant", result.message)

    if result.success:
        st.session_state[AI_WORKSPACE_ATTACH_OPEN_KEY] = False


def _safe_chip_key(filename: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]", "_", filename)


def _render_workspace_styles() -> None:
    st.markdown(
        """
<style>
[data-testid="stForm"]:has(input[aria-label="AI Workspace prompt"])
[data-testid="stFormSubmitButton"] button {
    background: #2563EB !important;
    border: 2px solid #1D4ED8 !important;
    color: #FFFFFF !important;
    box-shadow: 0 8px 20px rgba(37, 99, 235, 0.28) !important;
}
[data-testid="stForm"]:has(input[aria-label="AI Workspace prompt"])
[data-testid="stFormSubmitButton"] button:hover {
    background: #1D4ED8 !important;
    border-color: #1E40AF !important;
}
[data-testid="stForm"]:has(input[aria-label="AI Workspace prompt"])
[data-testid="stFormSubmitButton"] button p,
[data-testid="stForm"]:has(input[aria-label="AI Workspace prompt"])
[data-testid="stFormSubmitButton"] button span,
[data-testid="stForm"]:has(input[aria-label="AI Workspace prompt"])
[data-testid="stFormSubmitButton"] button div {
    color: #FFFFFF !important;
}
.dde-ai-workspace-shell {
    max-width: 920px;
    margin: 0 auto;
}
.dde-ai-prompt-headline {
    font-size: 24px;
    font-weight: 800;
    color: #0F172A;
    line-height: 1.25;
    margin: 0 0 4px;
}
.dde-ai-prompt-subhead {
    font-size: 14px;
    color: #64748B;
    margin: 0 0 14px;
    line-height: 1.45;
}
.dde-ai-context-panel {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 14px;
    padding: 12px 14px;
    margin: 0 0 12px;
}
.dde-ai-context-panel-title {
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: #64748B;
    margin: 0 0 8px;
}
.dde-ai-context-line {
    font-size: 13px;
    color: #0F172A;
    margin: 0 0 4px;
    line-height: 1.4;
}
.dde-ai-inference-banner {
    background: #EFF6FF;
    border: 1px solid #BFDBFE;
    border-radius: 12px;
    padding: 10px 14px;
    margin: 0 0 12px;
    font-size: 13px;
    color: #1E3A8A;
    line-height: 1.45;
}
.dde-ai-chip-row {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin: 10px 0 0;
}
.dde-ai-thread {
    max-height: 180px;
    overflow-y: auto;
    margin: 0 0 14px;
}
.dde-ai-message-user,
.dde-ai-message-assistant {
    padding: 10px 14px;
    border-radius: 14px;
    margin: 0 0 8px;
    font-size: 14px;
    line-height: 1.45;
}
.dde-ai-message-user {
    background: #2563EB;
    color: #FFFFFF;
    margin-left: 48px;
}
.dde-ai-message-assistant {
    background: #FFFFFF;
    color: #0F172A;
    border: 1px solid #E2E8F0;
    margin-right: 48px;
}
.dde-ai-example-row {
    margin: 0 0 12px;
}
.dde-ai-composer-marker,
.dde-ai-attach-open-marker {
    display: none;
}
[data-testid="stHorizontalBlock"]:has(.dde-ai-composer-marker) .stButton > button {
    min-height: 46px;
    font-size: 18px;
    padding: 0 12px;
}
[data-testid="stVerticalBlock"]:has(.dde-ai-attach-open-marker) [data-testid="stFileUploader"] {
    margin: 0 0 10px;
    background: transparent;
    border: none;
    padding: 0;
}
[data-testid="stVerticalBlock"]:has(.dde-ai-attach-open-marker) [data-testid="stFileUploader"] label {
    display: none;
}
[data-testid="stHorizontalBlock"]:has(.dde-ai-chip-row-marker) .stButton > button {
    font-size: 12px;
    min-height: 34px;
    padding: 6px 12px;
    border-radius: 999px !important;
    background: #EFF6FF !important;
    border: 1px solid #BFDBFE !important;
    color: #1E3A8A !important;
    font-weight: 600;
}
[data-testid="stHorizontalBlock"]:has(.dde-ai-chip-row-marker) .stButton > button:hover {
    background: #DBEAFE !important;
    border-color: #93C5FD !important;
    color: #1E3A8A !important;
}
[data-testid="stHorizontalBlock"]:has(.dde-ai-example-marker) .stButton > button {
    font-size: 12px;
    min-height: 34px;
    padding: 4px 10px;
    border-radius: 999px !important;
}
</style>
""",
        unsafe_allow_html=True,
    )


def _render_prompt_intro() -> None:
    st.markdown(
        f"""
<div class="dde-ai-prompt-headline">{PROMPT_HEADLINE}</div>
<div class="dde-ai-prompt-subhead">{PROMPT_SUBHEAD}</div>
""",
        unsafe_allow_html=True,
    )


def _render_context_panel(summary: WorkspaceContextSummary) -> None:
    doc_line = f"✓ {summary.document_count} document{'s' if summary.document_count != 1 else ''}"
    report_line = (
        f"✓ {summary.prior_report_count} previous report"
        f"{'s' if summary.prior_report_count != 1 else ''}"
    )
    st.markdown(
        f"""
<div class="dde-ai-context-panel">
<div class="dde-ai-context-panel-title">Working with</div>
<div class="dde-ai-context-line">{doc_line}</div>
<div class="dde-ai-context-line">{report_line}</div>
<div class="dde-ai-context-line">✓ Project: <strong>{summary.project_name}</strong></div>
</div>
""",
        unsafe_allow_html=True,
    )


def _render_last_inference() -> None:
    inference = st.session_state.get(AI_WORKSPACE_LAST_INFERENCE_KEY)
    if not inference:
        return

    confidence = inference.get("confidence", "")
    confidence_html = (
        f'<div><strong>Confidence:</strong> {confidence}</div>'
        if confidence and confidence != "Manual"
        else '<div><strong>Source:</strong> Advanced options override</div>'
    )
    st.markdown(
        f"""
<div class="dde-ai-inference-banner">
<div><strong>Last detected task:</strong> {inference.get("display_label", "")}</div>
{confidence_html}
</div>
""",
        unsafe_allow_html=True,
    )


def _render_context_chips(workspace: dict, filenames: list[str]) -> None:
    if not filenames:
        return

    st.markdown('<div class="dde-ai-chip-row-marker"></div>', unsafe_allow_html=True)
    columns = st.columns(min(len(filenames), 3))
    for index, filename in enumerate(filenames):
        with columns[index % len(columns)]:
            if st.button(
                f"📄 {filename}  ✕",
                key=f"ai_chip_remove_{_safe_chip_key(filename)}",
                use_container_width=True,
                help="Remove from this conversation (keeps the file in your project)",
            ):
                exclude_filename(workspace["id"], filename)
                st.rerun()


def _render_conversation() -> None:
    messages = st.session_state.get(AI_WORKSPACE_MESSAGES_KEY, [])
    if not messages:
        return

    st.markdown('<div class="dde-ai-thread">', unsafe_allow_html=True)
    for message in messages:
        role = message.get("role", "assistant")
        css_class = "dde-ai-message-user" if role == "user" else "dde-ai-message-assistant"
        st.markdown(
            f'<div class="{css_class}">{message.get("content", "")}</div>',
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)


def _render_examples(on_select: Callable[[str], None]) -> None:
    st.markdown('<div class="dde-ai-example-marker"></div>', unsafe_allow_html=True)
    row_count = (len(PROMPT_EXAMPLES) + 1) // 2
    for row in range(row_count):
        examples = PROMPT_EXAMPLES[row * 2 : row * 2 + 2]
        columns = st.columns(len(examples))
        for column, example in zip(columns, examples):
            with column:
                if st.button(example, key=f"ai_example_{_safe_chip_key(example)}", use_container_width=True):
                    on_select(example)


def _render_attach_control(workspace: dict) -> None:
    if AI_WORKSPACE_ATTACH_KEY not in st.session_state:
        st.session_state[AI_WORKSPACE_ATTACH_KEY] = 0

    st.markdown('<div class="dde-ai-attach-open-marker"></div>', unsafe_allow_html=True)
    uploaded_files = st.file_uploader(
        "Attach files",
        type=SUPPORTED_TYPES,
        accept_multiple_files=True,
        label_visibility="collapsed",
        key=f"ai_workspace_attach_{st.session_state[AI_WORKSPACE_ATTACH_KEY]}",
    )
    if uploaded_files:
        process_workspace_uploads(
            uploaded_files,
            workspace,
            batch_key=AI_WORKSPACE_ATTACH_BATCH_KEY,
            uploader_state_key=AI_WORKSPACE_ATTACH_KEY,
        )
        st.session_state[AI_WORKSPACE_ATTACH_OPEN_KEY] = False


def _render_composer(
    workspace: dict,
    context_files: list[str],
    *,
    pending_prompt: str = "",
) -> None:
    _render_workspace_styles()

    placeholder = (
        "Summarize these documents…"
        if context_files
        else "Attach documents, then describe what you need…"
    )

    st.markdown('<div class="dde-ai-composer-marker"></div>', unsafe_allow_html=True)

    attach_col, composer_col = st.columns([0.08, 0.92], gap="small", vertical_alignment="bottom")

    with attach_col:
        if st.button("📎", key="ai_workspace_attach_toggle", help="Attach documents"):
            st.session_state[AI_WORKSPACE_ATTACH_OPEN_KEY] = not st.session_state.get(
                AI_WORKSPACE_ATTACH_OPEN_KEY, False
            )
            st.rerun()

    with composer_col:
        with st.form("ai_workspace_prompt_form", clear_on_submit=False):
            input_col, send_col = st.columns([8, 1], gap="small", vertical_alignment="bottom")

            with input_col:
                prompt = st.text_input(
                    "AI Workspace prompt",
                    value=pending_prompt,
                    placeholder=placeholder,
                    key="ai_workspace_prompt_input",
                    label_visibility="collapsed",
                )

            with send_col:
                submitted = st.form_submit_button(
                    "↑",
                    type="primary",
                    use_container_width=True,
                )

            if submitted:
                _handle_prompt_submit(prompt, workspace, context_files)
                st.session_state.pop(AI_WORKSPACE_PROMPT_KEY, None)
                st.rerun()


def _render_advanced_options() -> None:
    _init_settings_state()

    with st.expander("Advanced options", expanded=False):
        st.caption("Optional AI behavior overrides for this workspace.")

        st.selectbox(
            "Report type",
            available_report_type_options(),
            key=f"{AI_WORKSPACE_SETTINGS_PREFIX}report_type",
            help="Leave on Auto to infer the task from your prompt.",
        )
        st.selectbox("Output length", OUTPUT_LENGTHS, key=f"{AI_WORKSPACE_SETTINGS_PREFIX}output_length")
        st.selectbox("Tone", TONES, key=f"{AI_WORKSPACE_SETTINGS_PREFIX}tone")
        st.selectbox("Language", LANGUAGES, key=f"{AI_WORKSPACE_SETTINGS_PREFIX}language")
        st.checkbox("Include charts", key=f"{AI_WORKSPACE_SETTINGS_PREFIX}include_charts")
        st.text_area(
            "Custom instructions",
            key=f"{AI_WORKSPACE_SETTINGS_PREFIX}custom_instructions",
            placeholder="Optional guidance for structure, audience, or emphasis.",
            height=90,
        )


def _queue_example_prompt(example: str) -> None:
    st.session_state[AI_WORKSPACE_PROMPT_KEY] = example
    st.session_state["ai_workspace_prompt_input"] = example


def render_ai_workspace() -> None:
    """Render the conversational AI Workspace experience."""

    initialize_projects()
    workspace = get_active_workspace()

    if workspace.get("is_pending"):
        st.info(
            "Select **Project** in the sidebar and create your project to start working "
            "with your documents."
        )
        return

    context_files = active_context_filenames(workspace)
    summary = summarize_workspace_context(workspace, context_files)
    attach_open = st.session_state.get(AI_WORKSPACE_ATTACH_OPEN_KEY, False)
    pending_prompt = st.session_state.pop(AI_WORKSPACE_PROMPT_KEY, "")

    st.markdown('<div class="dde-ai-workspace-shell">', unsafe_allow_html=True)

    _render_prompt_intro()
    _render_context_panel(summary)
    _render_last_inference()
    _render_context_chips(workspace, context_files)
    _render_conversation()

    if attach_open or not context_files:
        _render_attach_control(workspace)

    _render_examples(_queue_example_prompt)
    _render_composer(workspace, context_files, pending_prompt=pending_prompt)
    _render_advanced_options()

    if st.session_state.get(AI_WORKSPACE_MESSAGES_KEY):
        if st.button("Clear conversation", key="ai_workspace_clear", type="secondary"):
            st.session_state.pop(AI_WORKSPACE_PROMPT_KEY, None)
            st.session_state[AI_WORKSPACE_MESSAGES_KEY] = []
            st.session_state[AI_WORKSPACE_ATTACH_OPEN_KEY] = False
            st.session_state.pop(AI_WORKSPACE_LAST_INFERENCE_KEY, None)
            st.session_state[_excluded_state_key(workspace["id"])] = []
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)
