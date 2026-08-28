"""
Regression tests for the "Report not found" bug hit on the golden path:
the frontend calls generate() then immediately save() on the same report
id. On an eventually-consistent storage backend, a fresh listing taken by
the save() request can briefly lag behind the write generate() just made,
surfacing a false 404 on a report that was, in fact, just created.
api.routers.reports._find_report() now retries a few times before giving
up — these tests prove the retry actually recovers from that race, and
that a genuinely missing report still 404s (just after the retry window).
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from api.auth_jwt import AuthenticatedPrincipal
from api.routers import reports as reports_router
from api.routers.reports import generate_report, get_report, save_report
from api.schemas import GenerateReportBody, SaveReportBody
from services.project_service import ProjectService
from tests.conftest import TEST_USER


@pytest.fixture
def principal() -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(user=TEST_USER, access_token="test-token")


def test_save_immediately_after_generate_succeeds(
    isolated_env, project_service: ProjectService, principal, monkeypatch
):
    """The exact golden-path sequence the frontend runs on every report
    generation: generate() then save(id, 'ready') right after, with no
    delay in between."""

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    project = project_service.create_project("Golden Path Project")

    body = GenerateReportBody(template_id="executive_summary", period_id="custom")
    created = generate_report(project["id"], body, principal, TEST_USER)

    saved = save_report(
        project["id"], created.id, SaveReportBody(status="ready"), principal, TEST_USER
    )
    assert saved.id == created.id
    assert saved.status == "ready"


def test_find_report_retries_through_a_transient_listing_gap(
    isolated_env, project_service: ProjectService, principal, monkeypatch
):
    """Simulates an eventually-consistent storage backend: the first call
    to list reports comes back empty (as if the just-written file hasn't
    propagated to a fresh listing yet), and only a later call sees it.
    The retry loop in _find_report must recover rather than 404."""

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(reports_router.time, "sleep", lambda _seconds: None)
    project = project_service.create_project("Race Condition Project")

    body = GenerateReportBody(template_id="executive_summary", period_id="custom")
    created = generate_report(project["id"], body, principal, TEST_USER)

    real_reports = reports_router._reports
    calls = {"count": 0}

    def _flaky_reports(workspace_id, principal_arg):
        calls["count"] += 1
        if calls["count"] == 1:
            return []  # first listing "misses" the just-written report
        return real_reports(workspace_id, principal_arg)

    monkeypatch.setattr(reports_router, "_reports", _flaky_reports)

    result = get_report(project["id"], created.id, principal, TEST_USER)

    assert result.id == created.id
    assert calls["count"] >= 2  # confirms the retry path was actually exercised


def test_find_report_still_404s_for_a_genuinely_missing_report(
    isolated_env, project_service: ProjectService, principal, monkeypatch
):
    monkeypatch.setattr(reports_router.time, "sleep", lambda _seconds: None)
    project = project_service.create_project("Missing Report Project")

    with pytest.raises(HTTPException) as exc_info:
        get_report(project["id"], "rpt_does_not_exist", principal, TEST_USER)
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Report not found."


def test_find_report_retry_gives_up_after_the_full_delay_sequence(
    isolated_env, project_service: ProjectService, principal, monkeypatch
):
    """A listing that never recovers within the retry window must still
    404 — the retry is a bounded mitigation for a transient race, not an
    unbounded wait."""

    monkeypatch.setattr(reports_router.time, "sleep", lambda _seconds: None)
    project = project_service.create_project("Always Empty Project")
    monkeypatch.setattr(reports_router, "_reports", lambda *a, **kw: [])

    with pytest.raises(HTTPException) as exc_info:
        get_report(project["id"], "rpt_never_appears", principal, TEST_USER)
    assert exc_info.value.status_code == 404


def test_find_report_retries_through_a_transient_listing_exception(
    isolated_env, project_service: ProjectService, principal, monkeypatch
):
    """Regression test for a bug hit in production (2026-08-28): the retry
    loop only protected against _reports() coming back empty, not against
    it raising (a transient Storage/DB error). A raise on the first
    attempt used to abort the whole loop immediately, surfacing a bare,
    unlogged 500 to the caller even though a plain retry of the same
    request succeeded a moment later. The loop must now retry through an
    exception exactly like it already retries through "not found yet"."""

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(reports_router.time, "sleep", lambda _seconds: None)
    project = project_service.create_project("Transient Error Project")

    body = GenerateReportBody(template_id="executive_summary", period_id="custom")
    created = generate_report(project["id"], body, principal, TEST_USER)

    real_reports = reports_router._reports
    calls = {"count": 0}

    def _flaky_reports(workspace_id, principal_arg):
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("simulated transient storage error")
        return real_reports(workspace_id, principal_arg)

    monkeypatch.setattr(reports_router, "_reports", _flaky_reports)

    result = get_report(project["id"], created.id, principal, TEST_USER)

    assert result.id == created.id
    assert calls["count"] >= 2


def test_find_report_raises_a_clean_500_when_listing_never_recovers(
    isolated_env, project_service: ProjectService, principal, monkeypatch
):
    """When every retry attempt raises, the caller must get a proper
    HTTPException with an honest, logged detail — not a bare unhandled
    exception (which used to reach the client as a JSON-less 500 with no
    diagnostic trail in the server logs)."""

    monkeypatch.setattr(reports_router.time, "sleep", lambda _seconds: None)
    project = project_service.create_project("Always Failing Project")

    def _always_raises(*_args, **_kwargs):
        raise RuntimeError("simulated persistent storage error")

    monkeypatch.setattr(reports_router, "_reports", _always_raises)

    with pytest.raises(HTTPException) as exc_info:
        get_report(project["id"], "rpt_whatever", principal, TEST_USER)
    assert exc_info.value.status_code == 500
    assert "try again" in exc_info.value.detail.lower()
