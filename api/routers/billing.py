"""
Billing routes for the React SPA — plan catalog, checkout, portal, cancel.
"""

from __future__ import annotations

import config
from fastapi import APIRouter, Depends, HTTPException, status

from api.auth_jwt import AuthenticatedPrincipal
from api.deps import get_current_user, get_principal, user_request_scope
from api.schemas import (
    BillingSummaryOut,
    CheckoutUrlOut,
    CompleteCheckoutBody,
    PlanOut,
    PortalUrlOut,
    StartCheckoutBody,
    UsageSnapshotOut,
)
from models.user import User
from services.billing_service import (
    BillingService,
    PaystackBillingError,
    StripeBillingError,
)
from services.usage_service import UsageService

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/plans", response_model=list[PlanOut])
def list_plans(
    _principal: AuthenticatedPrincipal = Depends(get_principal),
    _current_user: User = Depends(get_current_user),
) -> list[PlanOut]:
    return [
        PlanOut(
            id=plan_id,
            label=plan["label"],
            price_label=plan["price_label"],
            tagline=plan.get("tagline", ""),
            ideal_for=plan.get("ideal_for", ""),
            reports_per_month=plan.get("reports_per_month"),
            uploads_per_month=plan.get("uploads_per_month"),
            projects_max=plan.get("projects_max"),
            includes=plan.get("includes", []),
            billable=plan_id in config.BILLABLE_PLANS,
        )
        for plan_id, plan in config.PLANS.items()
    ]


def _summary_out(principal: AuthenticatedPrincipal) -> BillingSummaryOut:
    billing = BillingService(access_token=principal.access_token)
    usage = UsageService(
        current_user=principal.user, access_token=principal.access_token
    )
    summary = billing.get_summary()
    snapshot = usage.get_snapshot()
    return BillingSummaryOut(
        enabled=BillingService.is_enabled(),
        available_providers=BillingService.available_providers(),
        billing_plan=summary["billing_plan"],
        effective_plan=summary["effective_plan"],
        subscription_status=summary["subscription_status"],
        payment_provider=summary.get("payment_provider"),
        cancel_at_period_end=summary.get("cancel_at_period_end", False),
        current_period_end=summary.get("current_period_end"),
        trial_days_remaining=summary.get("trial_days_remaining"),
        usage=UsageSnapshotOut(
            reports_used=snapshot.reports_used,
            reports_limit=snapshot.reports_limit,
            uploads_used=snapshot.uploads_used,
            uploads_limit=snapshot.uploads_limit,
            projects_max=snapshot.projects_max,
        ),
    )


@router.get("/summary", response_model=BillingSummaryOut)
def get_billing_summary(
    principal: AuthenticatedPrincipal = Depends(get_principal),
    _current_user: User = Depends(get_current_user),
) -> BillingSummaryOut:
    with user_request_scope(principal):
        return _summary_out(principal)


@router.post("/checkout", response_model=CheckoutUrlOut)
def start_checkout(
    body: StartCheckoutBody,
    principal: AuthenticatedPrincipal = Depends(get_principal),
    _current_user: User = Depends(get_current_user),
) -> CheckoutUrlOut:
    with user_request_scope(principal):
        billing = BillingService(access_token=principal.access_token)
        try:
            url = billing.start_checkout(body.plan_id, provider=body.provider)
        except (ValueError, StripeBillingError, PaystackBillingError) as exc:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, detail=str(exc)
            ) from exc
    return CheckoutUrlOut(checkout_url=url)


@router.post("/checkout/complete", response_model=BillingSummaryOut)
def complete_checkout(
    body: CompleteCheckoutBody,
    principal: AuthenticatedPrincipal = Depends(get_principal),
    _current_user: User = Depends(get_current_user),
) -> BillingSummaryOut:
    with user_request_scope(principal):
        billing = BillingService(access_token=principal.access_token)
        try:
            billing.complete_checkout(
                provider=body.provider,
                session_id=body.session_id,
                reference=body.reference,
            )
        except (ValueError, StripeBillingError, PaystackBillingError) as exc:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, detail=str(exc)
            ) from exc
        return _summary_out(principal)


@router.post("/portal", response_model=PortalUrlOut)
def open_portal(
    principal: AuthenticatedPrincipal = Depends(get_principal),
    _current_user: User = Depends(get_current_user),
) -> PortalUrlOut:
    with user_request_scope(principal):
        billing = BillingService(access_token=principal.access_token)
        try:
            url = billing.open_customer_portal()
        except (ValueError, StripeBillingError) as exc:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, detail=str(exc)
            ) from exc
    return PortalUrlOut(portal_url=url)


@router.post("/cancel", response_model=BillingSummaryOut)
def cancel_subscription(
    principal: AuthenticatedPrincipal = Depends(get_principal),
    _current_user: User = Depends(get_current_user),
) -> BillingSummaryOut:
    with user_request_scope(principal):
        billing = BillingService(access_token=principal.access_token)
        billing.cancel_at_period_end()
        return _summary_out(principal)
