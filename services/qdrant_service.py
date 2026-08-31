"""
Qdrant vector store for document chunks.
"""

from __future__ import annotations

import logging
import os
import uuid
from typing import Any

logger = logging.getLogger(__name__)

COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "datadumpai_chunks").strip()
VECTOR_SIZE = int(os.getenv("QDRANT_VECTOR_SIZE", "1536"))


class QdrantService:
    """Thin wrapper around qdrant-client."""

    def __init__(self, url: str | None = None) -> None:
        self._url = (url or os.getenv("QDRANT_URL", "http://127.0.0.1:6333")).strip()
        self._api_key = os.getenv("QDRANT_API_KEY", "").strip() or None
        self._client = None

    def _get_client(self):
        if self._client is not None:
            return self._client
        from qdrant_client import QdrantClient

        self._client = QdrantClient(url=self._url, api_key=self._api_key, timeout=60)
        return self._client

    def ensure_collection(self) -> None:
        from qdrant_client.http import models as qmodels

        client = self._get_client()
        try:
            names = {c.name for c in client.get_collections().collections}
        except Exception as exc:
            logger.warning("Qdrant get_collections failed: %s", exc)
            raise

        if COLLECTION_NAME in names:
            return

        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=qmodels.VectorParams(
                size=VECTOR_SIZE,
                distance=qmodels.Distance.COSINE,
            ),
        )
        client.create_payload_index(
            collection_name=COLLECTION_NAME,
            field_name="document_id",
            field_schema=qmodels.PayloadSchemaType.KEYWORD,
        )
        client.create_payload_index(
            collection_name=COLLECTION_NAME,
            field_name="workspace_id",
            field_schema=qmodels.PayloadSchemaType.KEYWORD,
        )

    def upsert_chunks(
        self,
        *,
        workspace_id: str,
        document_id: str,
        user_id: str,
        filename: str,
        chunks: list[dict[str, Any]],
        vectors: list[list[float]],
    ) -> int:
        from qdrant_client.http import models as qmodels

        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors length mismatch")

        self.ensure_collection()
        self.delete_document(document_id)

        points = []
        for chunk, vector in zip(chunks, vectors):
            point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{document_id}:{chunk['chunk_index']}"))
            points.append(
                qmodels.PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={
                        "document_id": document_id,
                        "workspace_id": workspace_id,
                        "user_id": user_id,
                        "filename": filename,
                        "chunk_index": chunk["chunk_index"],
                        "heading": chunk.get("heading") or "",
                        "text": chunk["text"],
                    },
                )
            )

        if points:
            self._get_client().upsert(collection_name=COLLECTION_NAME, points=points)
        return len(points)

    def delete_document(self, document_id: str) -> None:
        from qdrant_client.http import models as qmodels

        try:
            self.ensure_collection()
            self._get_client().delete(
                collection_name=COLLECTION_NAME,
                points_selector=qmodels.FilterSelector(
                    filter=qmodels.Filter(
                        must=[
                            qmodels.FieldCondition(
                                key="document_id",
                                match=qmodels.MatchValue(value=document_id),
                            )
                        ]
                    )
                ),
            )
        except Exception as exc:
            logger.warning("Qdrant delete_document failed: %s", exc)

    def search(
        self,
        *,
        workspace_id: str,
        query_vector: list[float],
        limit: int = 8,
        document_id: str | None = None,
        document_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Return ranked chunk hits for a workspace query vector.

        `document_id`, when given, is an ADDITIONAL filter (AND'd with the
        workspace_id filter, never a replacement for it) — used by the
        document-coverage-guarantee query in report_retrieval_service.py
        to pull a specific document's top chunks without ever loosening
        workspace isolation.

        `document_ids`, when given, is the same kind of additional filter
        but matches any document in the list — used to scope a report's
        entire retrieval pass to a user-selected document subset rather
        than the whole workspace."""

        from qdrant_client.http import models as qmodels

        self.ensure_collection()
        must_conditions = [
            qmodels.FieldCondition(
                key="workspace_id",
                match=qmodels.MatchValue(value=workspace_id),
            )
        ]
        if document_id:
            must_conditions.append(
                qmodels.FieldCondition(
                    key="document_id",
                    match=qmodels.MatchValue(value=document_id),
                )
            )
        if document_ids:
            must_conditions.append(
                qmodels.FieldCondition(
                    key="document_id",
                    match=qmodels.MatchAny(any=document_ids),
                )
            )

        response = self._get_client().query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            limit=limit,
            query_filter=qmodels.Filter(must=must_conditions),
            with_payload=True,
        )

        hits: list[dict[str, Any]] = []
        for point in response.points:
            payload = dict(point.payload or {})
            hits.append(
                {
                    "id": str(point.id),
                    "score": float(point.score or 0.0),
                    "document_id": str(payload.get("document_id") or ""),
                    "filename": str(payload.get("filename") or "document"),
                    "chunk_index": int(payload.get("chunk_index") or 0),
                    "heading": str(payload.get("heading") or ""),
                    "text": str(payload.get("text") or ""),
                }
            )
        return hits

    def delete_workspace(self, workspace_id: str) -> None:
        from qdrant_client.http import models as qmodels

        try:
            self.ensure_collection()
            self._get_client().delete(
                collection_name=COLLECTION_NAME,
                points_selector=qmodels.FilterSelector(
                    filter=qmodels.Filter(
                        must=[
                            qmodels.FieldCondition(
                                key="workspace_id",
                                match=qmodels.MatchValue(value=workspace_id),
                            )
                        ]
                    )
                ),
            )
        except Exception as exc:
            logger.warning("Qdrant delete_workspace failed: %s", exc)
