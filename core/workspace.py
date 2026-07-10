"""
DataDumpAI Enterprise
Workspace Core
"""

from __future__ import annotations

from services.workspace_service import WorkspaceService


class Workspace:

    """
    Represents one complete enterprise workspace.
    """

    def __init__(
        self,
        project_id: str,
    ) -> None:

        self.project_id = project_id

        self.service = WorkspaceService()

        self.refresh()

    def refresh(self):

        self.data = self.service.load_workspace(
            self.project_id
        )

    @property
    def project(self):

        return self.data.project

    @property
    def documents(self):

        return self.data.documents

    @property
    def reports(self):

        return self.data.reports

    @property
    def storage(self):

        return self.data.storage_used

    @property
    def document_count(self):

        return len(self.documents)

    @property
    def report_count(self):

        return len(self.reports)

    @property
    def name(self):

        return self.data.name

    @property
    def timeline(self):

        return self.data.timeline

    @property
    def health(self):

        return self.data.health

    @property
    def recent_documents(self):

        return self.data.recent_documents

    @property
    def recent_reports(self):

        return self.data.recent_reports

    @property
    def ai(self):

        return self.data.ai

    @property
    def analytics(self):

        return self.data.analytics

    @property
    def exports(self):

        return self.data.exports

    @property
    def knowledge(self):

        return self.data.knowledge

    @property
    def created_at(self):

        return self.data.created_at

    @property
    def last_activity(self):

        return self.data.last_activity

    @property
    def export_count(self):

        return self.data.export_count
