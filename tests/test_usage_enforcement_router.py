"""
Tests that plan/usage limits are actually enforced on the FastAPI routes —
not just implemented in PlanService/UsageService. Follows
tests/test_billing_router.py's style: call router functions directly with a
hand-built AuthenticatedPrincipal under isolated_env.
"""

from __future__ import annotations

import asyncio
import io

import pytest
from fastapi import BackgroundTasks, HTTPException, UploadFile

from fastapi.datastructures import Headers

from api.auth_jwt import AuthenticatedPrincipal
from api.routers.intelligence import check_readiness
from api.routers.knowledge import upload_knowledge
from api.routers.me import delete_branding_logo, get_branding_logo, upload_branding_logo
from api.routers.reports import export_report, generate_report, get_report, list_templates
from api.routers.workspaces import create_workspace
from api.schemas import CreateWorkspaceBody, GenerateReportBody
from services.project_service import ProjectService
from services.usage_service import UsageService
from tests.conftest import TEST_USER

# 1x1 transparent PNG — small enough to exercise BrandingService's real
# validation/storage path without a binary test fixture file.
_TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _image_upload_file(
    name: str = "logo.png", content: bytes = _TINY_PNG, content_type: str = "image/png"
) -> UploadFile:
    return UploadFile(
        file=io.BytesIO(content),
        filename=name,
        headers=Headers({"content-type": content_type}),
    )


@pytest.fixture
def principal() -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(user=TEST_USER, access_token="test-token")


def _upload_file(name: str = "doc.txt", content: bytes = b"hello world") -> UploadFile:
    return UploadFile(file=io.BytesIO(content), filename=name)


def test_upload_blocked_when_over_free_limit(
    isolated_env, project_service: ProjectService, principal
):
    project = project_service.create_project("Upload Limit Project")
    UsageService().record_uploads(10)  # free plan's monthly cap

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            upload_knowledge(
                project["id"],
                BackgroundTasks(),
                _upload_file(),
                None,
                None,
                principal,
                TEST_USER,
            )
        )
    assert exc_info.value.status_code == 403


def test_upload_allowed_under_free_limit(
    isolated_env, project_service: ProjectService, principal
):
    project = project_service.create_project("Upload Allowed Project")

    result = asyncio.run(
        upload_knowledge(
            project["id"],
            BackgroundTasks(),
            _upload_file(),
            None,
            None,
            principal,
            TEST_USER,
        )
    )

    assert result.title
    assert UsageService().get_snapshot().uploads_used == 1


def test_generate_report_blocked_when_over_free_limit(
    isolated_env, project_service: ProjectService, principal, monkeypatch
):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    project = project_service.create_project("Report Limit Project")
    usage = UsageService()
    for _ in range(5):  # free plan's monthly cap
        usage.record_report_generated()

    body = GenerateReportBody(template_id="executive_summary", period_id="custom")
    with pytest.raises(HTTPException) as exc_info:
        generate_report(project["id"], body, principal, TEST_USER)
    assert exc_info.value.status_code == 403


def test_generate_report_blocked_for_locked_template(
    isolated_env, project_service: ProjectService, principal, monkeypatch
):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    project = project_service.create_project("Locked Template Project")

    body = GenerateReportBody(template_id="risk_assessment", period_id="custom")
    with pytest.raises(HTTPException) as exc_info:
        generate_report(project["id"], body, principal, TEST_USER)
    assert exc_info.value.status_code == 403
    assert "Risk Assessment Report" in exc_info.value.detail


def test_generate_report_allowed_for_unlocked_template(
    isolated_env, project_service: ProjectService, principal, monkeypatch
):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    project = project_service.create_project("Unlocked Template Project")

    body = GenerateReportBody(template_id="executive_summary", period_id="custom")
    report = generate_report(project["id"], body, principal, TEST_USER)

    assert report.id
    assert UsageService().get_snapshot().reports_used == 1


def test_list_templates_reports_locked_flag(
    isolated_env, project_service: ProjectService, principal
):
    project = project_service.create_project("List Templates Project")

    templates = list_templates(project["id"], principal, TEST_USER)
    by_id = {t.id: t for t in templates}

    assert by_id["executive_summary"].locked is False
    assert by_id["risk_assessment"].locked is True
    assert by_id["risk_assessment"].required_plan == "professional"
    assert by_id["board_report"].locked is True
    assert by_id["board_report"].required_plan == "starter"


def test_export_docx_blocked_on_free_export_pptx_blocked_on_starter_pdf_always_ok(
    isolated_env, project_service: ProjectService, principal, monkeypatch
):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    project = project_service.create_project("Export Gating Project")
    body = GenerateReportBody(template_id="executive_summary", period_id="custom")
    report = generate_report(project["id"], body, principal, TEST_USER)

    with pytest.raises(HTTPException) as exc_info:
        export_report(project["id"], report.id, "docx", principal, TEST_USER)
    assert exc_info.value.status_code == 403

    with pytest.raises(HTTPException) as exc_info:
        export_report(project["id"], report.id, "pptx", principal, TEST_USER)
    assert exc_info.value.status_code == 403

    # PDF stays available on the free plan.
    response = export_report(project["id"], report.id, "pdf", principal, TEST_USER)
    assert response.status_code == 200

    # Starter unlocks docx but not pptx.
    UsageService().set_plan("starter")
    docx_response = export_report(project["id"], report.id, "docx", principal, TEST_USER)
    assert docx_response.status_code == 200
    with pytest.raises(HTTPException) as exc_info:
        export_report(project["id"], report.id, "pptx", principal, TEST_USER)
    assert exc_info.value.status_code == 403


def test_report_responses_expose_locked_export_formats_for_plan(
    isolated_env, project_service: ProjectService, principal, monkeypatch
):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    project = project_service.create_project("Locked Export Formats Project")
    body = GenerateReportBody(template_id="executive_summary", period_id="custom")

    generated = generate_report(project["id"], body, principal, TEST_USER)
    assert generated.locked_export_formats == {"docx": "Starter", "pptx": "Professional"}

    fetched = get_report(project["id"], generated.id, principal, TEST_USER)
    assert fetched.locked_export_formats == {"docx": "Starter", "pptx": "Professional"}

    UsageService().set_plan("professional")
    fetched_pro = get_report(project["id"], generated.id, principal, TEST_USER)
    assert fetched_pro.locked_export_formats == {}


def test_create_workspace_blocked_at_free_project_max(
    isolated_env, project_service: ProjectService, principal
):
    project_service.create_project("P1")
    project_service.create_project("P2")
    project_service.create_project("P3")

    with pytest.raises(HTTPException) as exc_info:
        create_workspace(CreateWorkspaceBody(name="P4"), principal, TEST_USER)
    assert exc_info.value.status_code == 403


def test_create_workspace_not_blocked_on_starter(
    isolated_env, project_service: ProjectService, principal
):
    project_service.create_project("P1")
    project_service.create_project("P2")
    project_service.create_project("P3")
    UsageService().set_plan("starter")

    created = create_workspace(CreateWorkspaceBody(name="P4"), principal, TEST_USER)
    assert created.name == "P4"


def test_web_research_readiness_reflects_plan(
    isolated_env, project_service: ProjectService, principal
):
    project = project_service.create_project("Readiness Project")

    free_readiness = check_readiness(project["id"], principal, TEST_USER)
    assert free_readiness.web_research_available is False

    UsageService().set_plan("professional")
    pro_readiness = check_readiness(project["id"], principal, TEST_USER)
    assert pro_readiness.web_research_available is True


def test_branding_logo_upload_blocked_on_starter_plan(isolated_env, principal):
    UsageService().set_plan("starter")

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(upload_branding_logo(_image_upload_file(), principal, TEST_USER))
    assert exc_info.value.status_code == 403


def test_branding_logo_upload_allowed_on_professional_plan(isolated_env, principal):
    UsageService().set_plan("professional")

    uploaded = asyncio.run(upload_branding_logo(_image_upload_file(), principal, TEST_USER))
    assert uploaded.has_logo is True
    assert uploaded.data_url and uploaded.data_url.startswith("data:image/png;base64,")

    fetched = get_branding_logo(principal, TEST_USER)
    assert fetched.has_logo is True

    removed = delete_branding_logo(principal, TEST_USER)
    assert removed.has_logo is False
    assert get_branding_logo(principal, TEST_USER).has_logo is False


def test_branding_logo_upload_rejects_non_image_content(isolated_env, principal):
    UsageService().set_plan("professional")

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            upload_branding_logo(
                _image_upload_file(
                    name="logo.txt", content=b"not an image", content_type="text/plain"
                ),
                principal,
                TEST_USER,
            )
        )
    assert exc_info.value.status_code == 400
