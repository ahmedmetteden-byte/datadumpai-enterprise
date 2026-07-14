"""
DataDumpAI Enterprise
Document Pipeline
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from services.document_processor import DocumentProcessor
from services.document_service import DocumentService
from services.project_service import ProjectService
from core.workspace_context import is_quick_report


class DocumentPipeline:
    """
    Handles the complete document ingestion workflow.
    """

    def __init__(
        self,
        document_service: DocumentService | None = None,
        project_service: ProjectService | None = None,
    ) -> None:
        self.documents = document_service or DocumentService()
        self.projects = project_service or ProjectService()

    def get_project_with_documents(self, project_id: str) -> dict[str, Any]:
        """Return a project with its document list loaded from disk."""

        project = self.projects.get_project(project_id)
        project["documents"] = self.documents.get_documents(project_id)

        return project

    def ingest(
        self,
        *,
        project: dict[str, Any],
        uploaded_files: list,
        overwrite: bool = False,
        extract_text_on_upload: bool = True,
    ) -> tuple[str, list[dict[str, Any]], int]:
        """
        Save uploads, extract text, and persist project metadata.

        Returns:
            Combined extracted text, metadata for each processed file,
            and the number of newly uploaded files (replacements excluded).
        """

        existing = {
            document["filename"]: document
            for document in project.get("documents", [])
        }

        extracted: list[str] = []
        processed_documents: list[dict[str, Any]] = []
        new_upload_count = 0

        for uploaded_file in uploaded_files:
            filename = Path(uploaded_file.name).name
            is_new_file = filename not in existing

            if filename not in existing or overwrite:
                metadata = self.documents.save_document(
                    project["id"],
                    uploaded_file,
                    overwrite=overwrite,
                )

                project.setdefault("documents", [])

                if filename in existing:
                    project["documents"] = [
                        document
                        for document in project["documents"]
                        if document["filename"] != filename
                    ]
                elif is_new_file:
                    new_upload_count += 1

                project["documents"].append(metadata)
                existing[filename] = metadata
            else:
                metadata = existing[filename]

            if extract_text_on_upload:
                if hasattr(uploaded_file, "seek"):
                    uploaded_file.seek(0)

                text = DocumentProcessor.extract_text(uploaded_file)
                extracted.append(text)

            processed_documents.append(metadata)

        project["storage_used"] = sum(
            document["size"]
            for document in project["documents"]
        )

        if not is_quick_report(project["id"]):
            self.projects.update_project(project)

        return "\n\n".join(extracted), processed_documents, new_upload_count
