"""
Upload Documents Use Case
"""

from __future__ import annotations

from pathlib import Path

from application.document_pipeline import DocumentPipeline
from services.usage_service import UsageService


class UploadDocumentsUseCase:

    def __init__(
        self,
        pipeline: DocumentPipeline | None = None,
        usage_service: UsageService | None = None,
    ) -> None:
        self.pipeline = pipeline or DocumentPipeline()
        self.usage = usage_service or UsageService()

    def execute(
        self,
        *,
        project: dict,
        uploaded_files: list,
        overwrite: bool = False,
    ):
        existing = {
            document["filename"]
            for document in project.get("documents", [])
        }

        pending_new_uploads = sum(
            1
            for uploaded_file in uploaded_files
            if Path(uploaded_file.name).name not in existing
        )

        self.usage.check_can_upload(pending_new_uploads)

        document_text, processed_documents, new_upload_count = self.pipeline.ingest(
            project=project,
            uploaded_files=uploaded_files,
            overwrite=overwrite,
            extract_text_on_upload=False,
        )

        if new_upload_count:
            self.usage.record_uploads(new_upload_count)

        return document_text, processed_documents
