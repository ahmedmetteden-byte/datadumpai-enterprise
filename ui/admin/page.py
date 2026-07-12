"""
Admin panel UI.
"""

from __future__ import annotations

import streamlit as st

import config
from core.current_user import current_user_id
from services.admin_service import AdminService


def _admin_service() -> AdminService:
    return AdminService()


def render_admin_page() -> None:
    st.markdown("## Admin")

    service = _admin_service()
    stats = service.get_platform_stats()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Users", stats["total_users"])
    c2.metric("Active subs", stats["active_subscriptions"])
    c3.metric("Trialing", stats["trialing_users"])
    c4.metric("Feedback", stats["feedback_count"])

    tabs = st.tabs(["Users", "Feedback", "Support", "Audit log"])

    with tabs[0]:
        _render_users(service)

    with tabs[1]:
        _render_feedback(service)

    with tabs[2]:
        _render_support(service)

    with tabs[3]:
        _render_audit(service)


def _render_users(service: AdminService) -> None:
    st.markdown("### Users")
    users = service.list_users()

    if not users:
        st.info("No users found.")
        return

    for user in users:
        with st.expander(
            f"{user.get('full_name') or user['user_id'][:8]} · "
            f"{user.get('effective_plan', 'free')} · {user.get('subscription_status', 'none')}"
        ):
            st.write(f"**User ID:** `{user['user_id']}`")
            st.write(f"**Company:** {user.get('company') or '—'}")
            st.write(f"**Role:** {user.get('role', 'user')}")
            st.write(
                f"**Usage:** {user.get('uploads', 0)} uploads · "
                f"{user.get('reports_generated', 0)} reports this period"
            )

            plan_options = list(config.PLANS.keys())
            current = user.get("billing_plan", config.DEFAULT_PLAN)
            new_plan = st.selectbox(
                "Set billing plan",
                options=plan_options,
                index=plan_options.index(current) if current in plan_options else 0,
                key=f"admin_plan_{user['user_id']}",
            )
            if st.button("Apply plan", key=f"admin_apply_{user['user_id']}"):
                service.set_user_plan(
                    user["user_id"],
                    new_plan,
                    actor_user_id=current_user_id(),
                )
                st.success(f"Plan updated to {config.PLANS[new_plan]['label']}.")
                st.rerun()


def _render_feedback(service: AdminService) -> None:
    st.markdown("### Feedback inbox")
    items = service.list_feedback()
    if not items:
        st.caption("No feedback yet.")
        return

    for item in items[:50]:
        st.markdown(
            f"**{item.get('category', 'general').title()}** · "
            f"{item.get('created_at', '')[:10]}"
        )
        st.write(item.get("message", ""))
        if item.get("email"):
            st.caption(f"From: {item['email']}")
        st.divider()


def _render_support(service: AdminService) -> None:
    st.markdown("### Support requests")
    items = service.list_support_requests()
    if not items:
        st.caption("No support requests yet.")
        return

    for item in items[:50]:
        st.markdown(f"**{item.get('subject', 'Support')}** · {item.get('created_at', '')[:10]}")
        st.write(item.get("message", ""))
        st.caption(f"{item.get('name', '')} · {item.get('email', '')}")
        st.divider()


def _render_audit(service: AdminService) -> None:
    st.markdown("### Audit log")
    logs = service.list_audit_logs(limit=50)
    if not logs:
        st.caption("No audit events recorded.")
        return

    for entry in logs:
        st.markdown(
            f"`{entry.get('created_at', '')[:19]}` · "
            f"**{entry.get('action', '')}** · "
            f"{entry.get('target_type', '')}:{entry.get('target_id', '')}"
        )
