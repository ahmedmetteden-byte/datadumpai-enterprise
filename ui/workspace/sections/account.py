"""
Project Workspace — Account & Profile
"""

from __future__ import annotations

import html

import streamlit as st

import config
from config import PLANS
from core.auth import get_current_user, sign_out
from services.notification_service import email_status_caption
from services.profile_service import ProfileService
from services.usage_service import UsageService
from ui.auth.forms import render_change_password_form
from ui.billing import render_billing_section
from ui.usage import render_plan_comparison, render_plan_switcher, render_usage_meter

ACCOUNT_SECTIONS = ("profile", "subscription", "security", "activity")


def render() -> None:
    focus = st.session_state.pop("account_tab", "profile")
    if focus not in ACCOUNT_SECTIONS:
        focus = "profile"

    _render_profile_header()
    st.divider()

    with st.expander("Subscription", expanded=focus == "subscription"):
        _render_subscription()

    with st.expander("Security", expanded=focus == "security"):
        _render_security()

    with st.expander("Activity", expanded=focus == "activity"):
        _render_activity()


def _render_profile_header() -> None:
    user = get_current_user()
    profile_service = ProfileService()
    profile = profile_service.load()

    if user is None:
        st.warning("Sign in to manage your profile.")
        return

    snapshot = UsageService().get_snapshot()
    plan_label = PLANS.get(snapshot.plan, PLANS["free"])["label"]
    display_name = html.escape(profile.get("full_name") or user.display_name)
    company = html.escape(profile.get("company", "") or "—")
    timezone = html.escape(profile.get("timezone", "UTC") or "UTC")
    email = html.escape(user.email or "—")
    initials = html.escape(user.initials)

    st.markdown(
        f"""
<div class="dde-account-profile">
<div class="dde-account-profile-header">
<div class="dde-user-avatar dde-account-avatar">{initials}</div>
<div>
<div class="dde-account-name">{display_name}</div>
<div class="dde-account-plan">{html.escape(plan_label)}</div>
</div>
</div>
<div class="dde-account-details">
<div><span class="dde-account-label">Company</span>{company}</div>
<div><span class="dde-account-label">Timezone</span>{timezone}</div>
<div><span class="dde-account-label">Email</span>{email}</div>
</div>
</div>
""",
        unsafe_allow_html=True,
    )

    if not user.email_verified:
        st.warning("Your email is not verified yet. Check your inbox for the verification link.")

    with st.form("account_profile_form"):
        st.markdown("#### Edit profile")
        full_name = st.text_input(
            "Full name",
            value=profile.get("full_name") or user.display_name,
        )
        company_input = st.text_input("Company", value=profile.get("company", ""))
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
        timezone_input = st.selectbox(
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
                "company": company_input,
                "job_title": job_title,
                "photo_url": photo_url,
                "timezone": timezone_input,
            }
        )
        st.success("Profile saved.")
        st.rerun()

    st.caption(email_status_caption())


def _render_subscription() -> None:
    render_usage_meter()
    st.divider()
    render_billing_section()
    st.divider()
    st.markdown("#### Compare plans")
    render_plan_comparison()
    if not config.PAYMENTS_ENABLED:
        st.divider()
        render_plan_switcher()


def _render_security() -> None:
    render_change_password_form()

    st.divider()

    if st.button("Sign out everywhere", type="secondary", key="account_sign_out_everywhere"):
        sign_out()
        st.rerun()


def _render_activity() -> None:
    from services.activity_service import ActivityService

    st.caption("A timeline of your sign-ins, uploads, reports, and AI questions.")

    logs = ActivityService().list_recent(limit=50)
    if not logs:
        st.info("No activity recorded yet.")
        return

    for entry in logs:
        created_at = str(entry.get("created_at", ""))[:16].replace("T", " ")
        message = entry.get("message") or entry.get("action", "Activity")
        st.markdown(f"**{created_at}** — {message}")
