"""
Project Workspace — Application Settings
"""

from __future__ import annotations

import streamlit as st

from services.notification_service import NotificationService, email_status_caption
from ui.support import render_about_section, render_feedback_form, render_support_form

SETTINGS_TABS = [
    "notifications",
    "preferences",
    "feedback",
    "support",
    "about",
]


def render() -> None:
    st.markdown("## Settings")
    st.caption("Application preferences for this device and workspace.")

    default_tab = st.session_state.pop("settings_tab", "notifications")

    try:
        default_index = SETTINGS_TABS.index(default_tab)
    except ValueError:
        default_index = 0

    tab_labels = [
        "Notifications",
        "Preferences",
        "Feedback",
        "Support",
        "About",
    ]
    tabs = st.tabs(tab_labels)

    with tabs[0]:
        _render_notifications()

    with tabs[1]:
        _render_preferences()

    with tabs[2]:
        render_feedback_form()

    with tabs[3]:
        render_support_form()

    with tabs[4]:
        render_about_section()


def _render_notifications() -> None:
    st.markdown("### Email notifications")
    st.caption(email_status_caption())

    notification_service = NotificationService()
    prefs = notification_service.get_preferences()

    with st.form("notification_preferences_form"):
        report_ready = st.checkbox("Report ready", value=prefs["report_ready"])
        usage_alerts = st.checkbox("Usage limit alerts", value=prefs["usage_alerts"])
        billing = st.checkbox("Billing and subscription updates", value=prefs["billing"])
        product_updates = st.checkbox("Product updates", value=prefs["product_updates"])
        submitted = st.form_submit_button("Save preferences", type="primary")

    if submitted:
        notification_service.save_preferences(
            {
                "report_ready": report_ready,
                "usage_alerts": usage_alerts,
                "billing": billing,
                "product_updates": product_updates,
            }
        )
        st.success("Notification preferences saved.")


def _render_preferences() -> None:
    st.markdown("### Application preferences")

    st.selectbox(
        "Theme",
        ["System", "Dark", "Light"],
        index=0,
        disabled=True,
        help="Theme selection is coming soon.",
    )
    st.selectbox(
        "Language",
        ["English"],
        index=0,
        disabled=True,
        help="Additional languages are coming soon.",
    )
    st.checkbox(
        "Include charts in generated reports by default",
        value=True,
        disabled=True,
        help="Export and AI defaults will be configurable here soon.",
    )
    st.checkbox(
        "Show keyboard shortcut hints",
        value=True,
        disabled=True,
        help="Keyboard shortcuts are coming soon.",
    )

    st.info(
        "Theme, AI preferences, export defaults, and keyboard shortcuts will be "
        "available in a future update."
    )
