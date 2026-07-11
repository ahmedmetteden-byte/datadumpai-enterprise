"""
DataDumpAI
Plan feature gating across Free, Starter, Professional, and Enterprise.
"""

from __future__ import annotations

from config import (
    DEFAULT_PLAN,
    PLANS,
    REPORT_TYPES,
    resolve_plan_id,
)
from services.executive_report_prompt import INTELLIGENCE_REPORT_TYPES
from services.full_report_prompt import is_full_report
from services.usage_service import UsageService


class PlanLimitError(Exception):
    """Raised when a plan limit or feature gate blocks an action."""

    def __init__(self, message: str, *, limit_type: str) -> None:
        super().__init__(message)
        self.limit_type = limit_type


class PlanService:
    """Resolve plan capabilities for the active account."""

    def __init__(self, usage_service: UsageService | None = None) -> None:
        self._usage = usage_service or UsageService()

    def get_plan_id(self) -> str:
        return self._usage.get_plan()

    def get_plan_config(self) -> dict:
        plan_id = resolve_plan_id(self.get_plan_id())
        return PLANS.get(plan_id, PLANS[DEFAULT_PLAN])

    @property
    def is_professional(self) -> bool:
        return self.get_plan_id() in {"professional", "enterprise", "pro"}

    @property
    def is_starter_or_above(self) -> bool:
        return self.get_plan_id() in {"starter", "professional", "enterprise", "pro"}

    def has_feature(self, feature: str) -> bool:
        features = self.get_plan_config().get("features", {})
        return bool(features.get(feature, False))

    def get_available_report_types(self) -> list[str]:
        configured = self.get_plan_config().get("report_types")
        if configured:
            return list(configured)
        if self.is_professional:
            return list(REPORT_TYPES)
        return list(self.get_plan_config().get("report_types", []))

    def is_report_type_available(self, report_type: str) -> bool:
        return report_type in self.get_available_report_types()

    def uses_intelligence_format(self, report_type: str) -> bool:
        if is_full_report(report_type):
            return False
        if not self.has_feature("intelligence_reports"):
            return False
        return report_type in INTELLIGENCE_REPORT_TYPES

    def uses_full_report_format(self, report_type: str) -> bool:
        return is_full_report(report_type)

    def include_professional_charts(self) -> bool:
        return self.has_feature("professional_charts")

    def include_cross_document_intelligence(self) -> bool:
        return self.has_feature("cross_document_intelligence")

    def can_use_web_research(self) -> bool:
        return self.has_feature("web_research")

    def can_use_deep_copilot(self) -> bool:
        return self.has_feature("deep_copilot")

    def can_use_saved_ai_knowledge(self) -> bool:
        return self.has_feature("saved_ai_knowledge")

    def can_use_custom_branding(self) -> bool:
        return self.has_feature("custom_branding")

    def can_use_professional_exports(self) -> bool:
        return self.has_feature("professional_exports")

    def can_use_pptx_export(self) -> bool:
        return self.has_feature("pptx_export")

    def projects_max(self) -> int | None:
        return self.get_plan_config().get("projects_max")

    def check_can_create_project(self, current_count: int) -> None:
        maximum = self.projects_max()
        if maximum is None:
            return

        if current_count >= maximum:
            label = self.get_plan_config()["label"]
            raise PlanLimitError(
                f"The {label} plan supports up to {maximum} projects. "
                "Upgrade to Starter for unlimited projects.",
                limit_type="projects",
            )

    def locked_report_types(self) -> list[str]:
        available = set(self.get_available_report_types())
        return [report_type for report_type in REPORT_TYPES if report_type not in available]
