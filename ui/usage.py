"""
DataDumpAI v1.0
Usage display helpers.
"""

from __future__ import annotations

import streamlit as st

from config import PLANS
from services.plan_service import PlanService
from services.usage_service import UsageService, UsageSnapshot


def _usage_service() -> UsageService:
    return UsageService()


def _plan_service() -> PlanService:
    return PlanService(_usage_service())


def get_usage() -> UsageSnapshot:
    return _usage_service().get_snapshot()


def render_usage_meter(*, compact: bool = False) -> None:
    snapshot = get_usage()
    plan = PLANS.get(snapshot.plan, PLANS["free"])
    plan_label = plan["label"]

    if compact:
        if snapshot.is_trialing:
            days = snapshot.trial_days_remaining
            hint = f"Trial · {days} day{'s' if days != 1 else ''} left"
        elif snapshot.plan in {"professional", "enterprise"}:
            hint = "Analyst tier"
        elif snapshot.plan == "starter":
            hint = "Starter tier"
        else:
            hint = "Free tier"
        st.caption(f"**{plan_label}** · {hint}")
        return

    st.markdown(f"**Current plan:** {plan_label}")
    st.caption(plan.get("tagline", ""))

    if snapshot.is_trialing and snapshot.trial_days_remaining is not None:
        st.success(
            f"Professional trial active — {snapshot.trial_days_remaining} day"
            f"{'s' if snapshot.trial_days_remaining != 1 else ''} remaining. "
            "No credit card required."
        )

    limits = (
        snapshot.reports_limit is None
        and snapshot.uploads_limit is None
        and snapshot.projects_max is None
    )

    if limits:
        st.success("Unlimited usage on your current plan.")
        return

    reports_line = (
        f"{snapshot.reports_used} / {snapshot.reports_limit} reports this month"
        if snapshot.reports_limit is not None
        else f"{snapshot.reports_used} reports this month"
    )
    uploads_line = (
        f"{snapshot.uploads_used} / {snapshot.uploads_limit} uploads this month"
        if snapshot.uploads_limit is not None
        else f"{snapshot.uploads_used} uploads this month"
    )
    projects_line = (
        f"Up to {snapshot.projects_max} projects"
        if snapshot.projects_max is not None
        else "Unlimited projects"
    )

    st.markdown(
        f"""
- {reports_line}
- {uploads_line}
- {projects_line}
"""
    )


def render_plan_comparison() -> None:
    columns = st.columns(2)

    for index, plan_id in enumerate(("free", "starter", "professional", "enterprise")):
        plan = PLANS[plan_id]
        with columns[index % 2]:
            st.markdown(f"#### {plan['label']} — {plan.get('price_label', '')}")
            st.caption(f"*{plan['ideal_for']}*")
            st.markdown("\n".join(f"- {item}" for item in plan["includes"]))


def render_plan_switcher() -> None:
    """Local plan toggle for testing before billing is enabled."""

    snapshot = get_usage()
    options = [plan_id for plan_id in PLANS if plan_id != "enterprise"]
    labels = [PLANS[plan_id]["label"] for plan_id in options]

    billing_plan = snapshot.billing_plan if snapshot.billing_plan in options else "free"

    try:
        current_index = options.index(billing_plan)
    except ValueError:
        current_index = 0

    selected_label = st.selectbox(
        "Preview billing plan (local testing)",
        labels,
        index=current_index,
        help="Switch plans to preview feature tiers before Stripe billing is enabled.",
    )

    selected_plan = options[labels.index(selected_label)]

    if selected_plan != billing_plan:
        _usage_service().set_plan(selected_plan)
        st.rerun()
