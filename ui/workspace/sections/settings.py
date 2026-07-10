"""
Project Workspace — Settings
"""

from __future__ import annotations

import streamlit as st

import config
from core.auth import get_current_user, sign_out
from services.notification_service import NotificationService, email_status_caption
from services.profile_service import ProfileService
from ui.auth.forms import render_change_password_form
from ui.billing import render_billing_section
from ui.support import render_about_section, render_feedback_form, render_support_form
from ui.usage import render_plan_comparison, render_plan_switcher, render_usage_meter

SETTINGS_TABS = [
    "profile",
    "notifications",
    "security",
    "plan",
    "activity",
    "feedback",
    "support",
    "about",
]


def render() -> None:
    st.markdown("## Settings")

    default_tab = st.session_state.pop("settings_tab", "profile")

    try:
        default_index = SETTINGS_TABS.index(default_tab)
    except ValueError:
        default_index = 0

    tab_labels = [
        "Profile",
        "Notifications",
        "Security",
        "Plan & Usage",
        "Activity",
        "Feedback",
        "Support",
        "About",
    ]
    tabs = st.tabs(tab_labels)

    with tabs[0]:
        _render_profile()

    with tabs[1]:
        _render_notifications()

    with tabs[2]:
        _render_security()

    with tabs[3]:
        _render_plan()

    with tabs[4]:
        _render_activity()

    with tabs[5]:
        render_feedback_form()

    with tabs[6]:
        render_support_form()

    with tabs[7]:
        render_about_section()


def _render_profile() -> None:
    user = get_current_user()
    profile_service = ProfileService()
    profile = profile_service.load()

    st.markdown("### Profile")

    if user is None:
        st.warning("Sign in to manage your profile.")
        return

    with st.form("profile_form"):
        full_name = st.text_input(
            "Full name",
            value=profile.get("full_name") or user.display_name,
        )
        st.text_input("Email", value=user.email, disabled=True)
        company = st.text_input("Company", value=profile.get("company", ""))
        job_title = st.text_input("Job title", value=profile.get("job_title", ""))
        photo_url = st.text_input(
            "Photo URL",
            value=profile.get("photo_url", ""),
            help="Optional image URL for your avatar.",
        )
        timezone_options = [
            "UTC",
            "Africa/Lagos",
            "Europe/London",
            "America/New_York",
            "America/Los_Angeles",
            "Asia/Dubai",
            "Asia/Singapore",
        ]
        current_tz = profile.get("timezone", "UTC")
        timezone = st.selectbox(
            "Timezone",
            options=timezone_options,
            index=timezone_options.index(current_tz)
            if current_tz in timezone_options
            else 0,
        )

        submitted = st.form_submit_button("Save profile", type="primary")

    if submitted:
        profile_service.save(
            {
                "full_name": full_name,
                "company": company,
                "job_title": job_title,
                "photo_url": photo_url,
                "timezone": timezone,
            }
        )
        st.success("Profile saved.")

    if not user.email_verified:
        st.warning("Your email is not verified yet. Check your inbox for the verification link.")

    st.divider()
    st.markdown("### API Key")
    st.info(
        "Set your OpenAI API key in a `.env` file as `OPENAI_API_KEY`. "
        "In-app key management is coming soon."
    )


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


def _render_security() -> None:
    st.markdown("### Security")
    render_change_password_form()

    st.divider()

    if st.button("Sign out everywhere", type="secondary"):
        sign_out()
        st.rerun()


def _render_plan() -> None:
    st.markdown("### Your plan")
    render_usage_meter()
    st.divider()
    render_billing_section()
    st.divider()
    st.markdown("### Compare plans")
    render_plan_comparison()
    if not config.PAYMENTS_ENABLED:
        st.divider()
        render_plan_switcher()


def _render_activity() -> None:
    from services.activity_service import ActivityService

    st.markdown("### Recent activity")
    st.caption("A timeline of your sign-ins, uploads, reports, and AI questions.")

    logs = ActivityService().list_recent(limit=50)
    if not logs:
        st.info("No activity recorded yet.")
        return

    for entry in logs:
        created_at = str(entry.get("created_at", ""))[:16].replace("T", " ")
        message = entry.get("message") or entry.get("action", "Activity")
        st.markdown(f"**{created_at}** — {message}")
