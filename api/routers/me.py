"""
Current-user profile and organisation membership routes for the React SPA.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from api.auth_jwt import AuthenticatedPrincipal
from api.deps import get_current_user, get_principal, user_request_scope
from api.schemas import (
    OrganisationMembershipOut,
    UpdateProfileBody,
    UserProfileOut,
)
from models.user import User
from services.profile_service import ProfileService
from services.project_service import ProjectService

router = APIRouter(prefix="/me", tags=["me"])


def _is_archived(project: dict[str, Any]) -> bool:
    return bool(project.get("archived_at"))


def _memberships(principal: AuthenticatedPrincipal) -> list[OrganisationMembershipOut]:
    with user_request_scope(principal):
        projects = ProjectService(access_token=principal.access_token).get_projects()
    return [
        OrganisationMembershipOut(
            workspace_id=str(project.get("id") or ""),
            workspace_name=str(project.get("name") or "Workspace"),
            role="owner",
            user_id=principal.user.id,
        )
        for project in projects
        if not _is_archived(project) and project.get("id")
    ]


def _to_profile_out(
    principal: AuthenticatedPrincipal,
    raw: dict[str, Any],
    memberships: list[OrganisationMembershipOut],
) -> UserProfileOut:
    company = str(raw.get("company") or "").strip()
    full_name = str(raw.get("full_name") or principal.user.full_name or "").strip()
    email = str(raw.get("email") or principal.user.email or "").strip()
    return UserProfileOut(
        user_id=principal.user.id,
        email=email,
        full_name=full_name,
        company=company,
        job_title=str(raw.get("job_title") or "").strip(),
        photo_url=str(raw.get("photo_url") or "").strip(),
        role=str(raw.get("role") or "user").strip() or "user",
        email_verified=bool(principal.user.email_verified),
        organisation_name=company or "Personal",
        memberships=memberships,
        updated_at=str(raw.get("updated_at") or "") or None,
    )


@router.get("/profile", response_model=UserProfileOut)
def get_my_profile(
    principal: AuthenticatedPrincipal = Depends(get_principal),
    _current_user: User = Depends(get_current_user),
) -> UserProfileOut:
    with user_request_scope(principal):
        service = ProfileService()
        raw = service.load()
        seed: dict[str, Any] = {}
        if not raw.get("email") and principal.user.email:
            seed["email"] = principal.user.email
        if not raw.get("full_name") and principal.user.full_name:
            seed["full_name"] = principal.user.full_name
        if seed:
            raw = service.save({**raw, **seed})
    return _to_profile_out(principal, raw, _memberships(principal))


@router.patch("/profile", response_model=UserProfileOut)
def update_my_profile(
    body: UpdateProfileBody,
    principal: AuthenticatedPrincipal = Depends(get_principal),
    _current_user: User = Depends(get_current_user),
) -> UserProfileOut:
    with user_request_scope(principal):
        service = ProfileService()
        current = service.load()
        patch: dict[str, Any] = dict(current)
        if body.full_name is not None:
            patch["full_name"] = body.full_name.strip()
        if body.company is not None:
            patch["company"] = body.company.strip()
        if body.job_title is not None:
            patch["job_title"] = body.job_title.strip()
        if not patch.get("email") and principal.user.email:
            patch["email"] = principal.user.email
        raw = service.save(patch)
    return _to_profile_out(principal, raw, _memberships(principal))


@router.get("/memberships", response_model=list[OrganisationMembershipOut])
def list_my_memberships(
    principal: AuthenticatedPrincipal = Depends(get_principal),
    _current_user: User = Depends(get_current_user),
) -> list[OrganisationMembershipOut]:
    return _memberships(principal)
