"""
Quick Report workspace service.

Quick Report is a first-class workspace mode. It is never stored as a row in
``public.projects`` and must never be sent to PostgreSQL as a UUID.
"""

from __future__ import annotations

from core.workspace_context import (
    QUICK_REPORT_WORKSPACE_ID,
    build_quick_report_record,
    is_quick_report,
    quick_report_storage_scope,
    resolve_storage_scope,
)


class QuickReportService:
    """User-scoped Quick Report workspace operations."""

    @staticmethod
    def workspace_id() -> str:
        return QUICK_REPORT_WORKSPACE_ID

    @staticmethod
    def is_quick_report(project_id: str | None) -> bool:
        return is_quick_report(project_id)

    @staticmethod
    def storage_scope() -> str:
        return quick_report_storage_scope()

    @staticmethod
    def resolve_storage_scope(project_id: str) -> str:
        return resolve_storage_scope(project_id)

    @staticmethod
    def build_workspace_record() -> dict:
        return build_quick_report_record()
