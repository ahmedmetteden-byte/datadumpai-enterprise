"""
Intelligence Studio RAG: retrieve (Qdrant + live web) → generate (OpenAI) → structured answer.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from openai import OpenAI

from models.web_source import WebSource
from services.embedding_service import EmbeddingService
from services.qdrant_service import QdrantService
from services.quantitative_analysis_service import (
    classify_metrics_by_movement,
    detect_movement_classification_question,
    detect_multi_period_question,
    extract_metric_tables,
    format_metrics_for_evidence,
    render_movement_classification_answer,
)
from services.report_qc_service import apply_deterministic_corrections
from services.report_retrieval_service import retrieve_grouped_sources
from services.web_search_service import WebSearchService

logger = logging.getLogger(__name__)

CHAT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
WEB_SEARCH_MAX_RESULTS = 5

VERIFIED_EVIDENCE_INSTRUCTIONS = (
    "A 'Verified Quantitative Evidence' block may follow the numbered evidence below. "
    "Those figures are computed programmatically, not estimated — they are authoritative. "
    "If the block contains a figure relevant to the question, you MUST cite it exactly as "
    "given rather than recalculating or estimating your own percentage, percentage-point, or "
    "absolute change from the raw numbers in the numbered evidence. Each line in that block is "
    "labeled with the EXACT two periods it covers (e.g. 'January 2026 -> March 2026 total') — "
    "when you state a change for a given period span, cite the line labeled with that exact "
    "span, never a different line (e.g. a single month's own stated month-on-month figure, "
    "which covers only that month against the month before it) just because it is nearby or "
    "easy to find. Distinguish a percentage change from a percentage-point change — never state "
    "one when the block gives the other. Distinguish the overall (first-to-last) change from an "
    "intermediate period's change — do not answer a 'January to March' question with a "
    "'February to March' figure or vice versa. If the block shows a Peak or Trough for a "
    "metric, mention it when it materially changes how the overall trend should be understood "
    "(e.g. an intermediate spike followed by moderation, rather than a smooth trend). Only "
    "describe a change as an 'improvement' or 'deterioration' when the evidence supports that "
    "judgment for that specific metric — otherwise use neutral language ('increased'/"
    "'decreased'). Present any causal explanation for a numeric change as a possibility the "
    "evidence does not establish, not as a stated fact, unless a source explicitly states the "
    "cause."
)

MODE_INSTRUCTIONS: dict[str, str] = {
    "ask": "Answer the question directly using only the evidence.",
    "summarise": "Provide a concise executive summary grounded in the evidence.",
    "compare": "Compare themes across the cited sources; call out agreements and gaps.",
    "analyse": "Provide an analytical breakdown with drivers, risks, and implications.",
    "generate_report": "Draft a short report outline with findings and recommended sections.",
    "recommend": "Recommend concrete next actions with owners/timeframes when evidence supports them.",
}


def _safe_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            return {}
        try:
            data = json.loads(match.group(0))
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            return {}


def _clip(text: str, limit: int = 900) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "…"


class IntelligenceRagService:
    """Question → workspace RAG + live web search → OpenAI → answer with
    confidence/citations/sources, blending document and web evidence."""

    def __init__(self) -> None:
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required for Intelligence Studio.")
        self._client = OpenAI(api_key=api_key)
        self._embedder = EmbeddingService()
        self._qdrant = QdrantService()
        self._web = WebSearchService()

    def retrieve(
        self, workspace_id: str, question: str, *, limit: int = 8
    ) -> list[dict[str, Any]]:
        vectors = self._embedder.embed_texts([question])
        if not vectors:
            return []
        return self._qdrant.search(
            workspace_id=workspace_id,
            query_vector=vectors[0],
            limit=limit,
        )

    def _search_web(self, question: str) -> tuple[list[WebSource], str | None]:
        """Best-effort live web search. Never raises — a search outage should
        degrade to document-only answers, not break the whole request."""

        if not WebSearchService.is_available():
            return [], "Web search package is not installed in this environment."
        try:
            return self._web.search(question, max_results=WEB_SEARCH_MAX_RESULTS), None
        except Exception as exc:
            logger.warning("Web search failed for %r: %s", question, exc)
            return [], str(exc)

    def _quantitative_sources(
        self,
        *,
        workspace_id: str,
        question: str,
        hits: list[dict[str, Any]],
        documents: list[dict[str, Any]] | None,
    ) -> list[dict[str, str]]:
        """Document-level {filename, excerpt} sources for the deterministic
        quantitative layer (services.quantitative_analysis_service —
        Phase A's engine, reused unchanged here, never duplicated).

        For a question that plausibly needs more than one period/document
        (see detect_multi_period_question), this reuses report_retrieval_
        service.retrieve_grouped_sources()'s document-coverage guarantee —
        the SAME mechanism report generation already relies on — passing
        the full workspace document list so a period Qdrant's top-K
        happened not to surface still gets pulled in with its own
        document-scoped query. For a single-fact question, it's cheaper
        and sufficient to just group the chunks the normal retrieve()
        pass already returned, one excerpt per filename — always
        attempted (not gated) since it's pure Python, no extra network
        or LLM cost, and lets deterministic evidence surface even for a
        question that wasn't detected as multi-period."""

        if documents and detect_multi_period_question(question):
            try:
                return retrieve_grouped_sources(
                    workspace_id,
                    [question],
                    embedder=self._embedder,
                    qdrant=self._qdrant,
                    documents=documents,
                )
            except Exception:
                logger.exception(
                    "Coverage-guaranteed retrieval failed workspace=%s; "
                    "falling back to grouping the existing chunk hits",
                    workspace_id,
                )

        by_filename: dict[str, list[str]] = {}
        for hit in hits:
            filename = str(hit.get("filename") or "")
            if not filename:
                continue
            by_filename.setdefault(filename, []).append(str(hit.get("text") or ""))
        return [
            {"filename": filename, "excerpt": "\n\n".join(texts)}
            for filename, texts in by_filename.items()
        ]

    @staticmethod
    def _document_periods(
        documents: list[dict[str, Any]] | None,
    ) -> dict[str, dict[str, Any]]:
        return {
            str(document.get("filename") or ""): {
                "period_date": document.get("period_date"),
                "uploaded_at": document.get("uploaded_at"),
            }
            for document in (documents or [])
            if document.get("filename")
        }

    @staticmethod
    def _verify_and_correct_answer(
        answer_text: str, metric_tables: list[dict[str, Any]]
    ) -> tuple[str, bool | None, str | None]:
        """Whether the answer's numerical claims are consistent with the
        Verified Quantitative Evidence it was given — and, per Section 7's
        "deterministic result -> grounded narrative" requirement, corrects
        a detected direction/sentiment contradiction in place BEFORE
        returning it, rather than shipping the wrong answer next to a
        warning the reader has to notice and reconcile themselves. Reuses
        report_qc_service.apply_deterministic_corrections() unchanged —
        the same correction pass report generation's QC step runs — so
        there is exactly one place that knows how to fix this class of
        error, not a second implementation for Q&A.

        Returns (answer_text, calculation_verified, notice):
        - (unchanged, None, None): no metric table's distinctive words
          appear anywhere in the answer — the deterministic evidence
          wasn't engaged, so there is nothing to verify (a purely
          qualitative answer, or one that didn't end up using the
          supplied figures).
        - (unchanged or corrected, True, None): every contradiction found
          was corrected — the returned answer is now numerically
          consistent with the verified calculations.
        - (corrected as far as possible, False, notice): a contradiction
          survived correction (e.g. a paraphrase with no literal figure
          or direction word to rewrite) — must not be presented as
          numerically verified.
        """

        if not metric_tables:
            return answer_text, None, None

        lowered = answer_text.lower()
        engaged = any(
            str(table.get("title") or "").strip().lower() in lowered
            for table in metric_tables
            if str(table.get("title") or "").strip()
        )
        if not engaged:
            return answer_text, None, None

        corrected_text, remaining_issues = apply_deterministic_corrections(
            answer_text, metric_tables
        )
        high_severity = [issue for issue in remaining_issues if issue.severity == "high"]
        if not high_severity:
            return corrected_text, True, None

        summary = "; ".join(issue.message for issue in high_severity)
        notice = (
            "This answer's numerical claims could not be fully verified against "
            f"deterministic calculations ({summary}). Treat the specific figures with "
            "caution and consider asking again or checking the source documents directly."
        )
        return corrected_text, False, notice

    @staticmethod
    def _supplement_citations_for_verified_metrics(
        *,
        answer_text: str,
        metric_tables: list[dict[str, Any]],
        citations: list[dict[str, Any]],
        sources: list[dict[str, Any]],
        linked_by_doc: dict[str, dict[str, Any]],
    ) -> None:
        """A metric series' verified change is often derived across MORE
        documents than the LLM's self-selected citationIndexes happen to
        reference (e.g. a Jan-to-March total whose Peak was established
        by February) — mutates citations/sources/linked_by_doc in place
        so every document that actually contributed to a metric the
        answer engages with is citable, not just whichever chunks the
        model picked."""

        lowered = answer_text.lower()
        cited_filenames = {str(item.get("label") or "") for item in citations}

        for table in metric_tables:
            title = str(table.get("title") or "").strip()
            if not title or title.lower() not in lowered:
                continue

            filenames = [
                name.strip()
                for name in str(table.get("source_document") or "").split(",")
                if name.strip()
            ]
            for filename in filenames:
                if filename in cited_filenames:
                    continue
                cited_filenames.add(filename)
                source_id = f"src_verified_{filename}"
                citations.append(
                    {
                        "id": f"cite_verified_{len(citations) + 1}",
                        "index": 0,
                        "sourceId": source_id,
                        "label": filename,
                        "quote": f"Contributed to the verified '{title}' calculation.",
                        "location": filename,
                    }
                )
                source = {
                    "id": source_id,
                    "kind": "document",
                    "title": filename,
                    "location": filename,
                    "excerpt": f"Contributed to the verified '{title}' calculation.",
                    "previewUrl": None,
                    "documentId": None,
                    "score": None,
                }
                sources.append(source)
                if filename not in linked_by_doc:
                    linked_by_doc[filename] = source

    def answer(
        self,
        *,
        workspace_id: str,
        question: str,
        mode: str = "ask",
        web_research_enabled: bool = True,
        documents: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        hits = self.retrieve(workspace_id, question)
        web_sources, web_notice = (
            self._search_web(question) if web_research_enabled else ([], None)
        )

        if not hits and not web_sources:
            notice = (
                "No indexed workspace evidence, and web search "
                + (web_notice if web_notice else "returned no results.")
            )
            return {
                "answer": (
                    "I could not find indexed documents for this workspace, and "
                    "a live web search did not turn up anything relevant either. "
                    "Try rephrasing the question, upload documents that may cover "
                    "it, or try again in a moment if the web search failed."
                ),
                "evidence": "No retrieved document chunks or web results were available.",
                "confidence": 0.1,
                "calculationVerified": None,
                "followUps": [
                    "Upload a PDF, DOCX, or XLSX to the Library",
                    "Rephrase the question with different keywords",
                    "Try again — the web search may have timed out",
                ],
                "citations": [],
                "sources": [],
                "linkedDocuments": [],
                "notice": notice,
            }

        # Deterministic quantitative grounding (Phase 3 Step 4, Phase B) —
        # reuses Phase A's quantitative_analysis_service.py unchanged; see
        # _quantitative_sources()'s docstring for why/when broader,
        # coverage-guaranteed retrieval is used instead of just the chunks
        # already retrieved above.
        quantitative_sources = self._quantitative_sources(
            workspace_id=workspace_id, question=question, hits=hits, documents=documents
        )
        document_periods = self._document_periods(documents)
        metric_tables = (
            extract_metric_tables(quantitative_sources, document_periods=document_periods)
            if quantitative_sources
            else []
        )
        verified_evidence_block = format_metrics_for_evidence(metric_tables) if metric_tables else ""

        # Unify document chunks and web results into one evidence list so the
        # model can cite either by the same [n] numbering scheme.
        evidence: list[dict[str, Any]] = [
            {"kind": "document", "hit": hit} for hit in hits
        ] + [{"kind": "web", "web": src} for src in web_sources]

        context_blocks: list[str] = []
        for index, item in enumerate(evidence, start=1):
            if item["kind"] == "document":
                hit = item["hit"]
                heading = hit.get("heading") or ""
                header = f"[{index}] DOCUMENT — {hit['filename']}"
                if heading:
                    header += f" — {heading}"
                context_blocks.append(f"{header}\n{_clip(str(hit['text']), 1200)}")
            else:
                src = item["web"]
                header = f"[{index}] WEB — {src.title} ({src.url})"
                context_blocks.append(f"{header}\n{_clip(src.snippet, 800)}")

        mode_key = mode if mode in MODE_INSTRUCTIONS else "ask"
        system = (
            "You are DataDumpAI Intelligence Studio, an enterprise RAG analyst. "
            "You have two kinds of evidence blocks: DOCUMENT blocks come from the "
            "user's own uploaded workspace files — treat them as authoritative for "
            "internal facts, decisions, and figures. WEB blocks are live public "
            "search results — use them for recent, external, or public-record "
            "information the documents can't cover (e.g. current events, "
            "regulatory updates, market data), and note plainly when your answer "
            "relies on the web rather than the workspace. If document and web "
            "evidence conflict, say so rather than picking one silently. Use "
            "ONLY the numbered evidence blocks — never invent a fact that isn't "
            "in one of them. If the evidence only partially answers the question, "
            "say what's missing rather than padding with generic text. Respond "
            "with compact JSON only."
            + (f" {VERIFIED_EVIDENCE_INSTRUCTIONS}" if verified_evidence_block else "")
        )
        user = (
            f"Mode: {mode_key}\n"
            f"Instruction: {MODE_INSTRUCTIONS[mode_key]}\n\n"
            f"Question:\n{question.strip()}\n\n"
            "Evidence:\n"
            + "\n\n".join(context_blocks)
            + verified_evidence_block
            + "\n\nReturn JSON with keys:\n"
            '- "answer": string (markdown-friendly plain text)\n'
            '- "evidence": string (why the answer is supported, and whether it '
            "relies on workspace documents, the web, or both)\n"
            '- "confidence": number from 0 to 1\n'
            '- "followUps": array of 2-4 short follow-up questions\n'
            '- "citationIndexes": array of integers matching evidence [n] numbers you relied on\n'
        )

        response = self._client.chat.completions.create(
            model=CHAT_MODEL,
            temperature=0.2,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content or "{}"
        parsed = _safe_json(raw)

        answer = str(parsed.get("answer") or "").strip()
        if not answer:
            first = evidence[0]
            fallback_text = (
                str(first["hit"].get("text") or "")
                if first["kind"] == "document"
                else first["web"].snippet
            )
            answer = _clip(fallback_text, 600)

        evidence_note = str(parsed.get("evidence") or "").strip()
        if not evidence_note:
            evidence_note = "Answer grounded in the highest-ranked retrieved evidence."

        confidence = parsed.get("confidence")
        try:
            confidence_f = float(confidence)
        except (TypeError, ValueError):
            base_score = hits[0]["score"] if hits else 0.5
            confidence_f = min(0.92, 0.45 + (base_score * 0.45))
        confidence_f = max(0.05, min(0.99, confidence_f))

        follow_ups = parsed.get("followUps") or parsed.get("follow_ups") or []
        if not isinstance(follow_ups, list):
            follow_ups = []
        follow_ups = [str(item).strip() for item in follow_ups if str(item).strip()][:4]

        citation_indexes = (
            parsed.get("citationIndexes") or parsed.get("citation_indexes") or []
        )
        if not isinstance(citation_indexes, list) or not citation_indexes:
            citation_indexes = list(range(1, min(4, len(evidence)) + 1))
        selected: list[int] = []
        for value in citation_indexes:
            try:
                idx = int(value)
            except (TypeError, ValueError):
                continue
            if 1 <= idx <= len(evidence) and idx not in selected:
                selected.append(idx)
        if not selected:
            selected = [1]

        citations: list[dict[str, Any]] = []
        sources: list[dict[str, Any]] = []
        linked_by_doc: dict[str, dict[str, Any]] = {}

        for idx in selected:
            item = evidence[idx - 1]

            if item["kind"] == "document":
                hit = item["hit"]
                source_id = f"src_{hit['document_id'] or hit['id']}"
                location = f"{hit['filename']} · chunk {hit['chunk_index'] + 1}"
                if hit.get("heading"):
                    location += f" · {hit['heading']}"
                citations.append(
                    {
                        "id": f"cite_{idx}",
                        "index": idx,
                        "sourceId": source_id,
                        "label": hit["filename"],
                        "quote": _clip(str(hit["text"]), 280),
                        "location": location,
                    }
                )
                source = {
                    "id": source_id,
                    "kind": "document",
                    "title": hit["filename"],
                    "location": location,
                    "excerpt": _clip(str(hit["text"]), 320),
                    "previewUrl": None,
                    "documentId": hit["document_id"] or None,
                    "score": round(float(hit["score"]), 4),
                }
                sources.append(source)
                doc_key = hit["document_id"] or hit["filename"]
                if doc_key not in linked_by_doc:
                    linked_by_doc[doc_key] = source
            else:
                src = item["web"]
                source_id = f"src_web_{idx}"
                citations.append(
                    {
                        "id": f"cite_{idx}",
                        "index": idx,
                        "sourceId": source_id,
                        "label": src.title,
                        "quote": _clip(src.snippet, 280),
                        "location": src.url,
                    }
                )
                sources.append(
                    {
                        "id": source_id,
                        "kind": "web",
                        "title": src.title,
                        "location": src.url,
                        "excerpt": _clip(src.snippet, 320),
                        "previewUrl": src.url,
                        "documentId": None,
                        "score": None,
                    }
                )

        # Phase C.1: a question shaped like "Compare January and March.
        # Which metrics improved and which deteriorated?" asks for a
        # SORTING of metrics into buckets — a mistake there is a wrong
        # bucket assignment, not a wrong word a text correction pass can
        # fix in place. Answered directly from classify_metrics_by_
        # movement()'s deterministic buckets rather than trusting the
        # LLM's own classification.
        movement_buckets = (
            classify_metrics_by_movement(metric_tables)
            if metric_tables and detect_movement_classification_question(question)
            else None
        )
        if movement_buckets and (movement_buckets["improved"] or movement_buckets["deteriorated"]):
            answer = render_movement_classification_answer(movement_buckets)
            calculation_verified: bool | None = True
            verification_notice: str | None = None
        else:
            answer, calculation_verified, verification_notice = self._verify_and_correct_answer(
                answer, metric_tables
            )

        if metric_tables:
            self._supplement_citations_for_verified_metrics(
                answer_text=answer,
                metric_tables=metric_tables,
                citations=citations,
                sources=sources,
                linked_by_doc=linked_by_doc,
            )

        notice = None
        if web_notice and not web_sources:
            notice = f"Web search unavailable for this answer: {web_notice}"
        if verification_notice:
            notice = f"{notice} {verification_notice}" if notice else verification_notice

        return {
            "answer": answer,
            "evidence": evidence_note,
            "confidence": round(confidence_f, 3),
            "calculationVerified": calculation_verified,
            "followUps": follow_ups,
            "citations": citations,
            "sources": sources,
            "linkedDocuments": list(linked_by_doc.values()),
            "notice": notice,
        }
