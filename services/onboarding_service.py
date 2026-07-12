"""
First-run onboarding progress for new users.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from core.auth import get_current_user_id
from core.workspace_context import QUICK_REPORT_PROJECT_ID
from services.profile_service import ProfileService
from services.project_service import ProjectService


ONBOARDING_STEPS = (
    {
        "step": 1,
        "title": "Create your first project",
        "description": "Projects keep documents, reports, and AI conversations organized.",
        "section": "overview",
        "cta": "Create project",
    },
    {
        "step": 2,
        "title": "Upload documents",
        "description": "Add PDFs, Word files, Excel sheets, or PowerPoint decks.",
        "section": "documents",
        "cta": "Open AI Workspace",
    },
    {
        "step": 3,
        "title": "Generate your first report",
        "description": "Turn your documents into board-ready intelligence in minutes.",
        "section": "documents",
        "cta": "Generate report",
    },
    {
        "step": 4,
        "title": "Ask AI questions",
        "description": "Follow up on your reports and documents with grounded answers.",
        "section": "copilot",
        "cta": "Open Ask AI",
    },
)


class OnboardingService:
    """Track and complete the first-run onboarding wizard."""

    def __init__(self, user_id: str | None = None) -> None:
        self._user_id = user_id or get_current_user_id()
        self._profile = ProfileService(self._user_id)

    def needs_onboarding(self) -> bool:
        profile = self._profile.load()
        return not bool(profile.get("onboarding_completed"))

    def get_current_step(self) -> int:
        profile = self._profile.load()
        return max(int(profile.get("onboarding_step", 1)), 1)

    def get_progress(self) -> dict[str, Any]:
        completed = self._detect_completed_steps()
        current_step = self.get_current_step()

        for step in ONBOARDING_STEPS:
            if not completed.get(step["step"], False) and step["step"] >= current_step:
                current_step = step["step"]
                break

        if all(completed.get(step["step"], False) for step in ONBOARDING_STEPS):
            current_step = ONBOARDING_STEPS[-1]["step"]

        return {
            "current_step": current_step,
            "completed_steps": completed,
            "steps": ONBOARDING_STEPS,
        }

    def sync_progress(self) -> int:
        """Advance the stored step based on workspace activity."""

        if not self.needs_onboarding():
            return 0

        completed = self._detect_completed_steps()
        next_step = 1
        for step in ONBOARDING_STEPS:
            if completed.get(step["step"]):
                next_step = step["step"] + 1
            else:
                next_step = step["step"]
                break

        profile = self._profile.load()
        profile["onboarding_step"] = next_step
        self._profile.save(profile)

        if all(completed.get(step["step"], False) for step in ONBOARDING_STEPS):
            self.complete_onboarding()
            return ONBOARDING_STEPS[-1]["step"]

        return next_step

    def complete_onboarding(self) -> None:
        profile = self._profile.load()
        profile["onboarding_completed"] = True
        profile["onboarding_step"] = ONBOARDING_STEPS[-1]["step"]
        profile["onboarding_completed_at"] = datetime.now(timezone.utc).isoformat()
        self._profile.save(profile)

    def skip_onboarding(self) -> None:
        self.complete_onboarding()

    def _detect_completed_steps(self) -> dict[int, bool]:
        projects = [
            project
            for project in ProjectService(self._user_id).get_projects()
            if project.get("id") not in {QUICK_REPORT_PROJECT_ID, ""}
        ]

        has_project = len(projects) > 0
        document_count = sum(len(project.get("documents") or []) for project in projects)
        report_count = sum(len(project.get("reports") or []) for project in projects)

        from services.activity_service import ActivityService

        activity = ActivityService(self._user_id).list_recent(limit=100)
        asked_ai = any(entry.get("action") == "copilot.asked" for entry in activity)

        return {
            1: has_project,
            2: document_count > 0,
            3: report_count > 0,
            4: asked_ai,
        }
