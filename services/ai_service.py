"""
DataDumpAI Enterprise
AI Service
"""

from __future__ import annotations

import logging
import os

from openai import OpenAI

logger = logging.getLogger(__name__)

from config import (
    AI_MODEL,
    AI_REPORT_MODEL,
    AI_FULL_REPORT_MAX_OUTPUT_TOKENS,
    AI_INTELLIGENCE_REPORT_MAX_OUTPUT_TOKENS,
    AI_REPORT_CHUNK_SUMMARY_OUTPUT_TOKENS,
    AI_REPORT_MAX_OUTPUT_TOKENS,
    AI_SYSTEM_PROMPT,
    AI_MAX_OUTPUT_TOKENS,
    AI_REQUEST_TIMEOUT_SECONDS,
)
from services.executive_report_prompt import (
    build_executive_report_prompt,
    uses_intelligence_format,
)
from services.full_report_prompt import build_full_report_prompt, is_full_report
from services.report_assembler import canonical_metrics_prompt
from services.report_section_templates import SectionPlan
from models.report_data import ReportData


class AIService:
    """
    Central AI engine used throughout DataDumpAI.
    """

    def __init__(self) -> None:

        api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY was not found in your .env file."
            )

        self.client = OpenAI(
            api_key=api_key,
            timeout=AI_REQUEST_TIMEOUT_SECONDS,
        )

    def generate_report(
        self,
        *,
        document_text: str,
        report_type: str,
        writing_style: str,
        audience: str,
        include_charts: bool,
        include_recommendations: bool,
        source_document_count: int | None = None,
        report_context: dict | None = None,
        use_intelligence_format: bool | None = None,
        report_data: ReportData | None = None,
    ) -> str:

        document_count = source_document_count
        if document_count is None:
            document_count = document_text.count("=== SOURCE DOCUMENT:")

        report_context = report_context or {}
        section_plan = None
        include_theme_metrics = True

        if report_data is not None and report_data.metadata.get("section_plan"):
            section_plan = SectionPlan.from_dict(report_data.metadata["section_plan"])
            include_theme_metrics = section_plan.include_canonical_theme_metrics

        metrics_section = (
            canonical_metrics_prompt(
                report_data,
                include_theme_metrics=include_theme_metrics,
            )
            if include_charts and report_data is not None
            else ""
        )
        synthesis_note = ""
        if "=== SOURCE CHUNK:" in document_text:
            synthesis_note = (
                "\nThe source material below is a complete set of section summaries from "
                "every analysed document chunk. Synthesize all sections — do not ignore "
                "later chunks.\n"
            )
        narrative_source = f"{synthesis_note}{document_text}" if synthesis_note else document_text

        if is_full_report(report_type):
            user_prompt = build_full_report_prompt(
                document_text=narrative_source,
                writing_style=writing_style,
                audience=audience,
                include_recommendations=include_recommendations,
                include_charts=include_charts,
                source_document_count=document_count,
                report_context=report_context,
                canonical_metrics_section=metrics_section,
                section_plan=section_plan,
            )
            max_output_tokens = AI_FULL_REPORT_MAX_OUTPUT_TOKENS
        elif (
            use_intelligence_format
            if use_intelligence_format is not None
            else uses_intelligence_format(report_type)
        ):
            intelligence_format = True
            user_prompt = build_executive_report_prompt(
                report_type=report_type,
                document_text=narrative_source,
                writing_style=writing_style,
                audience=audience,
                include_recommendations=include_recommendations,
                include_charts=include_charts,
                source_document_count=document_count,
                report_context=report_context,
                canonical_metrics_section=metrics_section,
                section_plan=section_plan,
            )
            max_output_tokens = AI_INTELLIGENCE_REPORT_MAX_OUTPUT_TOKENS
        else:
            intelligence_format = False
            count_instruction = ""
            if document_count > 1:
                count_instruction = (
                    f"\nYou are synthesizing {document_count} separate source documents. "
                    "Each section marked with === SOURCE DOCUMENT: ... === must be "
                    "reviewed and reflected in the final report.\n"
                )

            user_prompt = f"""
Create a professional {report_type} that synthesizes ALL source documents below.
{count_instruction}
Important:
- Read and analyze every document section provided
- Combine findings across documents into one cohesive report
- Do not base the report on only the first document
- When documents overlap, merge the information rather than repeating it

Audience:
{audience}

Writing Style:
{writing_style}

Requirements:

• Executive Summary
• Key Findings
• Analysis
• Risks
• Opportunities
"""

            if include_recommendations:
                user_prompt += "\n• Strategic Recommendations"

            if include_charts:
                user_prompt += "\n• Recommend suitable charts and visualisations"

            user_prompt += f"""

Source Material
===============================

{narrative_source}
"""
            max_output_tokens = AI_REPORT_MAX_OUTPUT_TOKENS

        logger.info(
            "Calling OpenAI for report generation model=%s report_type=%s "
            "max_output_tokens=%s prompt_chars=%s",
            AI_REPORT_MODEL,
            report_type,
            max_output_tokens,
            len(user_prompt),
        )

        response = self.client.responses.create(
            model=AI_REPORT_MODEL,
            instructions=AI_SYSTEM_PROMPT,
            input=user_prompt,
            max_output_tokens=max_output_tokens,
        )

        report_text = response.output_text.strip()
        logger.info(
            "OpenAI returned %d characters for report_type=%s",
            len(report_text),
            report_type,
        )
        return report_text

    def summarize_source_chunk(
        self,
        *,
        source_document: str,
        heading: str,
        chunk_text: str,
        report_type: str,
        max_summary_chars: int = 600,
    ) -> str:
        """Generate a concise summary for one analysed chunk."""

        prompt = f"""
Summarize this source-material section for later synthesis into a {report_type}.

Rules:
- Capture material facts, figures, risks, decisions, and themes from this section only.
- Do not invent information that is not present in the section.
- Write {max(3, max_summary_chars // 120)}–{max(4, max_summary_chars // 80)} concise sentences.
- Stay under {max_summary_chars} characters.
- Name the source document when citing specifics.

Source document: {source_document}
Section: {heading}

Section text:
{chunk_text[:12000]}
"""

        response = self.client.responses.create(
            model=AI_REPORT_MODEL,
            instructions=AI_SYSTEM_PROMPT,
            input=prompt,
            max_output_tokens=min(
                AI_REPORT_CHUNK_SUMMARY_OUTPUT_TOKENS,
                max(200, max_summary_chars // 2),
            ),
        )

        summary = response.output_text.strip()
        if len(summary) > max_summary_chars:
            summary = summary[: max_summary_chars - 1].rstrip() + "…"

        return summary

    def answer_question(
        self,
        *,
        context: str,
        question: str,
        project_name: str = "",
        web_context: str = "",
        deep_context: bool = False,
    ) -> str:
        """
        Answer a question using workspace context and optional web search results.
        """

        project_line = (
            f"Active Project: {project_name}\n\n"
            if project_name
            else ""
        )

        workspace_section = (
            f"Workspace Knowledge\n\n{context}\n\n"
            if context.strip()
            else "Workspace Knowledge\n\n(No project documents or reports matched this question.)\n\n"
        )

        web_section = (
            f"{web_context}\n\n"
            if web_context.strip()
            else "Web Search Results\n\n(No web results were returned.)\n\n"
        )

        if deep_context:
            capability_rules = """
Rules:
- Prefer workspace knowledge when it directly answers the question
- Use web search results for current events, statistics, regulatory updates, or facts not in the workspace
- Identify contradictions across documents when they exist
- Compare multiple reporting periods when prior reports are available
- Recommend specific strategic actions when the evidence supports them
- Explain why you reached each conclusion
- Cite supporting evidence with document or report names
- When using web information, cite the source title and URL in the answer
- Be concise, clear, and professional
- If neither source contains enough information, say what is missing
"""
        else:
            capability_rules = """
Rules:
- Prefer workspace knowledge when it directly answers the question
- Answer using the most relevant excerpts from the workspace
- Be concise, clear, and professional
- Cite document or report names when referencing specific details
- Do not perform live web research — answer from workspace knowledge only
- If the workspace does not contain enough information, say what is missing
"""

        prompt = f"""
You are DataDumpAI Copilot.

You help users understand their business documents and generated reports.

Use the sources below to answer the question:
1. Workspace knowledge from uploaded documents and saved reports
2. Web search results for current or external facts (when provided)

{capability_rules}

{project_line}{workspace_section}{web_section}Question

{question}

Provide a concise, professional answer with inline source citations.
"""

        response = self.client.responses.create(
            model=AI_MODEL,
            input=prompt,
            max_output_tokens=AI_MAX_OUTPUT_TOKENS,
        )

        return response.output_text

    def answer_from_excerpts(
        self,
        *,
        question: str,
        excerpts: list[dict],
    ) -> str:
        """
        Answer a question using only the supplied document excerpts.
        """

        context_blocks = []

        for index, excerpt in enumerate(excerpts, start=1):
            context_blocks.append(
                f"[{index}] Source: {excerpt['filename']}\n"
                f"{excerpt['excerpt']}"
            )

        context = "\n\n".join(context_blocks)

        user_prompt = f"""
Answer the user's question using ONLY the excerpts below.

Rules:
- Base your answer strictly on the supplied excerpts.
- If the excerpts do not contain enough information, say so clearly.
- Cite source filenames when referencing specific details.
- Be concise, professional, and objective.

Question:
{question}

Excerpts:
{context}
"""

        response = self.client.responses.create(
            model=AI_MODEL,
            instructions=AI_SYSTEM_PROMPT,
            input=user_prompt,
            max_output_tokens=AI_MAX_OUTPUT_TOKENS,
        )

        return response.output_text.strip()