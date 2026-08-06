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
from services.web_search_service import WebSearchService

logger = logging.getLogger(__name__)

CHAT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
WEB_SEARCH_MAX_RESULTS = 5

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

    def answer(
        self,
        *,
        workspace_id: str,
        question: str,
        mode: str = "ask",
    ) -> dict[str, Any]:
        hits = self.retrieve(workspace_id, question)
        web_sources, web_notice = self._search_web(question)

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
        )
        user = (
            f"Mode: {mode_key}\n"
            f"Instruction: {MODE_INSTRUCTIONS[mode_key]}\n\n"
            f"Question:\n{question.strip()}\n\n"
            "Evidence:\n"
            + "\n\n".join(context_blocks)
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

        notice = None
        if web_notice and not web_sources:
            notice = f"Web search unavailable for this answer: {web_notice}"

        return {
            "answer": answer,
            "evidence": evidence_note,
            "confidence": round(confidence_f, 3),
            "followUps": follow_ups,
            "citations": citations,
            "sources": sources,
            "linkedDocuments": list(linked_by_doc.values()),
            "notice": notice,
        }
