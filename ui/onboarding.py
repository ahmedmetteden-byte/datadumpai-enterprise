"""
First-run onboarding wizard for new users.
"""

from __future__ import annotations

import streamlit as st

from config import APP_NAME
from core.workspace_navigation import set_workspace_section
from services.onboarding_service import ONBOARDING_STEPS, OnboardingService
from services.project_service import ProjectService
from ui.feedback import show_error, show_success


def render_onboarding_wizard() -> bool:
    """
    Render the onboarding wizard when the user has not completed setup.

    Returns True when the wizard is shown (caller should skip the old banner).
    """

    onboarding = OnboardingService()
    if not onboarding.needs_onboarding():
        return False

    progress = onboarding.get_progress()
    onboarding.sync_progress()

    if not onboarding.needs_onboarding():
        return False

    current_step = progress["current_step"]
    completed = progress["completed_steps"]

    st.markdown(
        f"""
<div class="dde-onboarding">
<h3>Welcome to {APP_NAME}</h3>
<p>Follow these four steps to get your first report.</p>
</div>
""",
        unsafe_allow_html=True,
    )

    for step in ONBOARDING_STEPS:
        step_number = step["step"]
        is_complete = completed.get(step_number, False)
        is_current = step_number == current_step and not is_complete
        marker = "✅" if is_complete else ("👉" if is_current else "⬜")

        st.markdown(f"**{marker} Step {step_number} — {step['title']}**")
        st.caption(step["description"])

        if is_current:
            _render_step_actions(step)

        if step_number < len(ONBOARDING_STEPS):
            st.markdown("↓")

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    cols = st.columns([1, 1, 2])
    with cols[0]:
        if st.button("Skip tour", use_container_width=True, key="onboarding_skip"):
            onboarding.skip_onboarding()
            st.rerun()
    with cols[1]:
        if st.button("Refresh progress", use_container_width=True, key="onboarding_refresh"):
            onboarding.sync_progress()
            st.rerun()

    st.divider()
    return True


def _render_step_actions(step: dict) -> None:
    step_number = step["step"]

    if step_number == 1:
        with st.form("onboarding_create_project"):
            project_name = st.text_input(
                "Project name",
                placeholder="Q3 Board Pack",
                key="onboarding_project_name",
            )
            submitted = st.form_submit_button(
                step["cta"],
                type="primary",
                use_container_width=True,
            )

        if submitted:
            name = project_name.strip()
            if not name:
                st.warning("Enter a project name.")
            else:
                try:
                    ProjectService().create_project(name)
                    OnboardingService().sync_progress()
                    show_success(f"Project '{name}' created.")
                    st.rerun()
                except Exception as exc:
                    show_error(exc)
        return

    if st.button(
        step["cta"],
        type="primary",
        use_container_width=True,
        key=f"onboarding_step_{step_number}",
    ):
        set_workspace_section(step["section"])
        st.rerun()


def render_onboarding_banner() -> None:
    """Legacy banner — only shown after onboarding is complete."""

    if st.session_state.get("onboarding_dismissed"):
        return

    if OnboardingService().needs_onboarding():
        return

    with st.container():
        st.info(
            f"Welcome to {APP_NAME}! Upload documents, generate your first report, "
            "then explore Ask AI for follow-up questions."
        )
        if st.button("Got it", key="dismiss_onboarding"):
            st.session_state.onboarding_dismissed = True
            st.rerun()
