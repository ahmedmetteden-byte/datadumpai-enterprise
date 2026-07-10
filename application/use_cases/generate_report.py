"""
DataDumpAI Enterprise
Generate Report Use Case
"""

from __future__ import annotations

from application.report_pipeline import ReportPipeline


class GenerateReportUseCase:

    def __init__(self) -> None:

        self.pipeline = ReportPipeline()

    def execute(
        self,
        *,
        project: dict,
        document_text: str,
        report_type: str,
        writing_style: str,
        audience: str,
        include_charts: bool,
        include_recommendations: bool,
    ):

        return self.pipeline.generate(
            project=project,
            document_text=document_text,
            report_type=report_type,
            writing_style=writing_style,
            audience=audience,
            include_charts=include_charts,
            include_recommendations=include_recommendations,
        )