"""
Intelligence Studio RAG: retrieve (Qdrant) → generate (OpenAI) → structured answer.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from openai import OpenAI

from services.embedding_service import EmbeddingService
from services.qdrant_service import QdrantService

logger = logging.getLogger(__name__)

CHAT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"

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
    """Question → RAG retrieval → OpenAI → answer with confidence/citations/docs."""

    def __init__(self) -> None:
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required for Intelligence Studio.")
        self._client = OpenAI(api_key=api_key)
        self._embedder = EmbeddingService()
        self._qdrant = QdrantService()

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

    def answer(
        self,
        *,
        workspace_id: str,
        question: str,
        mode: str = "ask",
    ) -> dict[str, Any]:
        hits = self.retrieve(workspace_id, question)
        if not hits:
            return {
                "answer": (
                    "I could not find indexed documents for this workspace yet. "
                    "Upload and wait for indexing to finish, then ask again."
                ),
                "evidence": "No retrieved chunks were available in the vector index.",
                "confidence": 0.15,
                "followUps": [
                    "Upload a PDF, DOCX, or XLSX to the Library",
                    "Re-index existing documents",
                    "Ask again after indexing shows Done",
                ],
                "citations": [],
                "sources": [],
                "linkedDocuments": [],
                "notice": "No indexed evidence found.",
            }

        context_blocks: list[str] = []
        for index, hit in enumerate(hits, start=1):
            heading = hit.get("heading") or ""
            header = f"[{index}] {hit['filename']}"
            if heading:
                header += f" — {heading}"
            context_blocks.append(f"{header}\n{_clip(str(hit['text']), 1200)}")

        mode_key = mode if mode in MODE_INSTRUCTIONS else "ask"
        system = (
            "You are DataDumpAI Intelligence Studio, an enterprise RAG analyst. "
            "Use ONLY the numbered evidence blocks. Every factual claim should be "
            "supportable by those blocks. Respond with compact JSON only."
        )
        user = (
            f"Mode: {mode_key}\n"
            f"Instruction: {MODE_INSTRUCTIONS[mode_key]}\n\n"
            f"Question:\n{question.strip()}\n\n"
            "Evidence:\n"
            + "\n\n".join(context_blocks)
            + "\n\nReturn JSON with keys:\n"
            '- "answer": string (markdown-friendly plain text)\n'
            '- "evidence": string (why the answer is supported)\n'
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
            answer = _clip(str(hits[0].get("text") or ""), 600)

        evidence = str(parsed.get("evidence") or "").strip()
        if not evidence:
            evidence = "Answer grounded in the highest-ranked retrieved document chunks."

        confidence = parsed.get("confidence")
        try:
            confidence_f = float(confidence)
        except (TypeError, ValueError):
            confidence_f = min(0.92, 0.45 + (hits[0]["score"] * 0.45))
        confidence_f = max(0.05, min(0.99, confidence_f))

        follow_ups = parsed.get("followUps") or parsed.get("follow_ups") or []
        if not isinstance(follow_ups, list):
            follow_ups = []
        follow_ups = [str(item).strip() for item in follow_ups if str(item).strip()][:4]

        citation_indexes = (
            parsed.get("citationIndexes") or parsed.get("citation_indexes") or []
        )
        if not isinstance(citation_indexes, list) or not citation_indexes:
            citation_indexes = list(range(1, min(4, len(hits)) + 1))
        selected: list[int] = []
        for value in citation_indexes:
            try:
                idx = int(value)
            except (TypeError, ValueError):
                continue
            if 1 <= idx <= len(hits) and idx not in selected:
                selected.append(idx)
        if not selected:
            selected = [1]

        citations: list[dict[str, Any]] = []
        sources: list[dict[str, Any]] = []
        linked_by_doc: dict[str, dict[str, Any]] = {}

        for idx in selected:
            hit = hits[idx - 1]
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
                linked_by_doc[doc_key] = {
                    "id": source_id,
                    "kind": "document",
                    "title": hit["filename"],
                    "location": location,
                    "excerpt": _clip(str(hit["text"]), 320),
                    "previewUrl": None,
                    "documentId": hit["document_id"] or None,
                    "score": round(float(hit["score"]), 4),
                }

        return {
            "answer": answer,
            "evidence": evidence,
            "confidence": round(confidence_f, 3),
            "followUps": follow_ups,
            "citations": citations,
            "sources": sources,
            "linkedDocuments": list(linked_by_doc.values()),
            "notice": None,
        }
