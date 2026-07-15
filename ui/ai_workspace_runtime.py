"""
AI Workspace runtime — resolve document context and run report workflows.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from application.report_pipeline import ReportPipeline
from config import FULL_REPORT_PERIODS
from core.current_user import require_current_user
from models.report_processing_mode import ReportProcessingMode
from services.document_service import DocumentService
from services.executive_report_context import ExecutiveReportContextBuilder
from services.plan_service import PlanService
from services.report_service import ReportService
from ui.feedback import advance_generation_status, progressive_generation, show_error
from ui.projects import get_user_projects
from ui.report_generation import REPORT_TYPE_META, _selection_source_labels
from ui.report_preview import set_draft_report

logger = logging.getLogger(__name__)

AUTO_REPORT_TYPE = "Auto (from prompt)"
OUTPUT_LENGTHS = ("Brief", "Standard", "Detailed")
TONES = ("Professional", "Concise", "Formal", "Conversational")
LANGUAGES = ("English", "French", "Spanish", "German", "Arabic")

COMING_SOON_TASKS = frozenset(
    {
        "PowerPoint Presentation",
        "Visual Insights",
    }
)


@dataclass(frozen=True)
class AIWorkspaceSettings:
    report_type_override: str = AUTO_REPORT_TYPE
    output_length: str = "Standard"
    tone: str = "Professional"
    language: str = "English"
    include_charts: bool = True
    custom_instructions: str = ""


@dataclass(frozen=True)
class TaskInference:
    report_type: str
    display_label: str
    confidence: str
    inferred: bool


@dataclass(frozen=True)
class WorkspaceRequestResult:
    success: bool
    message: str
    inference: TaskInference | None = None


@dataclass(frozen=True)
class WorkspaceContextSummary:
    project_name: str
    document_count: int
    prior_report_count: int
    active_filenames: list[str]


def _report_pipeline() -> ReportPipeline:
    from core.auth import get_access_token

    return ReportPipeline(
        current_user=require_current_user(),
        access_token=get_access_token(),
    )


def _document_service() -> DocumentService:
    from core.auth import get_access_token

    return DocumentService(
        current_user=require_current_user(),
        access_token=get_access_token(),
    )


def _plan_service() -> PlanService:
    return PlanService()


_context_builder = ExecutiveReportContextBuilder()


def list_workspace_context_filenames(workspace: dict[str, Any]) -> list[str]:
    """All documents stored in the active project or Quick Report workspace."""

    return [
        document["filename"]
        for document in _document_service().get_documents(workspace["id"])
    ]


def count_prior_reports(workspace_id: str) -> int:
    return len(ReportService.get_reports(workspace_id))


def build_document_selection(
    workspace: dict[str, Any],
    filenames: list[str],
) -> list[dict[str, str]]:
    """Map filenames to the selection shape expected by the report pipeline."""

    allowed = set(list_workspace_context_filenames(workspace))
    return [
        {"project_id": workspace["id"], "filename": filename}
        for filename in filenames
        if filename in allowed
    ]


def infer_task(prompt: str, settings: AIWorkspaceSettings) -> TaskInference:
    from ui.ai_workspace import parse_prompt_intent

    if settings.report_type_override != AUTO_REPORT_TYPE:
        label = settings.report_type_override
        return TaskInference(
            report_type=settings.report_type_override,
            display_label=label,
            confidence="Manual",
            inferred=False,
        )

    cleaned = prompt.strip()

    if _matches_coming_soon(cleaned):
        label = _coming_soon_label(cleaned)
        return TaskInference(
            report_type=label,
            display_label=label,
            confidence="High",
            inferred=True,
        )

    report_type, _ = parse_prompt_intent(cleaned)
    if report_type:
        return TaskInference(
            report_type=report_type,
            display_label=_display_label_for_report_type(report_type, cleaned),
            confidence="High",
            inferred=True,
        )

    return TaskInference(
        report_type="Executive Summary",
        display_label="Executive Summary",
        confidence="Medium",
        inferred=True,
    )


def _display_label_for_report_type(report_type: str, prompt: str) -> str:
    lowered = prompt.lower()
    if report_type == "Executive Summary" and "summar" in lowered:
        return "One-page Summary"
    if report_type == "Board Report":
        return "Board Paper"
    if report_type == "Risk Assessment Report" and "register" in lowered:
        return "Risk Register"
    if report_type == "Strategic Planning Report" and (
        "m&e" in lowered or "monitoring" in lowered or "evaluation" in lowered
    ):
        return "M&E Framework"
    if report_type == "Full Report" and "compare" in lowered:
        return "Document Comparison"
    return report_type


def _matches_coming_soon(prompt: str) -> bool:
    lowered = prompt.lower()
    return any(
        token in lowered
        for token in ("powerpoint", "presentation deck", "ppt", "slide deck")
    )


def _coming_soon_label(prompt: str) -> str:
    return "PowerPoint Presentation"


def _processing_mode(settings: AIWorkspaceSettings) -> ReportProcessingMode:
    if settings.output_length == "Brief":
        return ReportProcessingMode.FAST
    return ReportProcessingMode.COMPREHENSIVE


def _conversation_context(
    conversation_messages: list[dict[str, str]] | None,
) -> str:
    if not conversation_messages:
        return ""

    lines: list[str] = []
    for message in conversation_messages[-8:]:
        role = message.get("role", "user").title()
        content = (message.get("content") or "").strip()
        if content:
            lines.append(f"{role}: {content}")

    if not lines:
        return ""

    return "Prior conversation in this session:\n" + "\n".join(lines)


def _additional_guidance(
    settings: AIWorkspaceSettings,
    prompt: str,
    conversation_messages: list[dict[str, str]] | None = None,
) -> str:
    parts: list[str] = []

    history = _conversation_context(conversation_messages)
    if history:
        parts.append(history)

    if settings.custom_instructions.strip():
        parts.append(settings.custom_instructions.strip())

    if settings.language != "English":
        parts.append(f"Write the report in {settings.language}.")

    if settings.output_length == "Brief":
        parts.append("Keep the report concise and focused on the highest-priority insights.")
    elif settings.output_length == "Detailed":
        parts.append("Provide thorough coverage with rich detail across all major themes.")

    parts.append(f"Latest user request: {prompt.strip()}")

    return "\n".join(parts)


def _format_inference_message(inference: TaskInference, *, generating: bool = False) -> str:
    prefix = "Generating" if generating else "Detected task"
    confidence_line = (
        f"**Confidence:** {inference.confidence}"
        if inference.confidence != "Manual"
        else "**Source:** Advanced options override"
    )
    return (
        f"**{prefix}:** {inference.display_label}  \n"
        f"{confidence_line}"
    )


def execute_workspace_request(
    *,
    prompt: str,
    workspace: dict[str, Any],
    settings: AIWorkspaceSettings,
    context_filenames: list[str],
    conversation_messages: list[dict[str, str]] | None = None,
) -> WorkspaceRequestResult:
    """Run the appropriate workflow for a conversational AI Workspace request."""

    cleaned = prompt.strip()
    if not cleaned:
        return WorkspaceRequestResult(
            success=False,
            message="Describe what you would like DataDumpAI to do.",
        )

    inference = infer_task(cleaned, settings)

    if inference.display_label in COMING_SOON_TASKS or _matches_coming_soon(cleaned):
        return WorkspaceRequestResult(
            success=False,
            message=(
                f"{_format_inference_message(inference)}\n\n"
                "**PowerPoint export** is on the roadmap. For now, generate your content "
                "here and export from the report viewer."
            ),
            inference=inference,
        )

    if not context_filenames:
        return WorkspaceRequestResult(
            success=False,
            message=(
                "Attach documents with **📎** or upload them in **My Documents** "
                f"for **{workspace['name']}**."
            ),
        )

    report_type = inference.report_type

    if not _plan_service().is_report_type_available(report_type):
        return WorkspaceRequestResult(
            success=False,
            message=(
                f"{_format_inference_message(inference)}\n\n"
                f"**{report_type}** requires a plan upgrade. "
                "Open **Account → Subscription** to unlock it."
            ),
            inference=inference,
        )

    document_selection = build_document_selection(workspace, context_filenames)
    if not document_selection:
        return WorkspaceRequestResult(
            success=False,
            message="No readable documents are in the current conversation context.",
            inference=inference,
        )

    processing_mode = _processing_mode(settings)
    include_charts = settings.include_charts and _plan_service().include_professional_charts()
    reporting_period = FULL_REPORT_PERIODS[0]

    try:
        with progressive_generation() as status:
            advance_generation_status(status, "✓ Understanding request")
            advance_generation_status(status, "✓ Detecting task")

            load_result = _report_pipeline().load_document_text_from_selection(
                document_selection,
                processing_mode=processing_mode,
            )
            advance_generation_status(status, "✓ Reading documents")

            document_text = load_result["combined_text"].strip()
            source_labels = _selection_source_labels(document_selection, get_user_projects())

            if not document_text:
                logger.error(
                    "AI Workspace empty document text loaded=%s skipped=%s "
                    "selection=%s processing_mode=%s",
                    load_result.get("loaded"),
                    load_result.get("skipped"),
                    document_selection,
                    processing_mode,
                )
                advance_generation_status(
                    status,
                    "Could not read selected documents",
                    state="error",
                )
                return WorkspaceRequestResult(
                    success=False,
                    message=(
                        f"{_format_inference_message(inference)}\n\n"
                        "Could not read text from the selected documents. "
                        "Try re-uploading readable PDF, Word, or Excel files in **My Documents**."
                    ),
                    inference=inference,
                )

            report_context = _context_builder.build(
                workspace_id=workspace["id"],
                source_documents=source_labels,
                report_type=report_type,
                include_prior_reports=(
                    _plan_service().include_cross_document_intelligence()
                    or _plan_service().uses_full_report_format(report_type)
                ),
                reporting_period=reporting_period,
            )
            report_context["additional_guidance"] = _additional_guidance(
                settings,
                cleaned,
                conversation_messages,
            )

            advance_generation_status(status, "✓ Extracting evidence")
            advance_generation_status(status, "✓ Building report")

            report = _report_pipeline().generate(
                document_text=document_text,
                report_type=report_type,
                writing_style=settings.tone,
                include_charts=include_charts,
                source_document_count=len(load_result["loaded"]),
                report_context=report_context,
                processing_mode=processing_mode,
            )

            logger.info(
                "AI Workspace generate complete report_type=%s narrative_chars=%s "
                "(preview draft only — not saved until user clicks Save)",
                report.report_type,
                len(report.narrative or ""),
            )
            advance_generation_status(status, "✓ Creating recommendations")
            advance_generation_status(status, "✓ Preparing downloads", state="complete")

            set_draft_report(
                report=report,
                source_documents=source_labels,
                workspace=workspace,
                document_selection=document_selection,
                processing_mode=processing_mode.value,
            )
            from ui.report_session_trace import log_report_session_state

            log_report_session_state("after_ai_workspace_set_draft")
    except Exception as exc:
        show_error(exc)
        return WorkspaceRequestResult(
            success=False,
            message=(
                f"{_format_inference_message(inference, generating=True)}\n\n"
                "Something went wrong while generating your report. Please try again."
            ),
            inference=inference,
        )

    doc_count = len(load_result["loaded"])
    return WorkspaceRequestResult(
        success=True,
        message=(
            f"{_format_inference_message(inference, generating=True)}\n\n"
            f"Your **{inference.display_label}** is ready — built from **{doc_count}** "
            f"document{'s' if doc_count != 1 else ''}. Review it below, or ask a follow-up "
            "(for example, _make it more concise_ or _add a SWOT analysis_)."
        ),
        inference=inference,
    )


def available_report_type_options() -> list[str]:
    plan = _plan_service()
    available = [
        report_type
        for report_type in REPORT_TYPE_META
        if plan.is_report_type_available(report_type)
    ]
    return [AUTO_REPORT_TYPE, *available]


def summarize_workspace_context(
    workspace: dict[str, Any],
    active_filenames: list[str],
) -> WorkspaceContextSummary:
    return WorkspaceContextSummary(
        project_name=workspace["name"],
        document_count=len(active_filenames),
        prior_report_count=count_prior_reports(workspace["id"]),
        active_filenames=active_filenames,
    )
