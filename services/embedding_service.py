"""
OpenAI embedding helper for document chunks.
"""

from __future__ import annotations

import logging
import os
from typing import Sequence

from openai import OpenAI

logger = logging.getLogger(__name__)

DEFAULT_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small").strip()


class EmbeddingService:
    def __init__(self, *, model: str | None = None) -> None:
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required for embeddings.")
        self._client = OpenAI(api_key=api_key)
        self._model = model or DEFAULT_MODEL

    def embed_texts(self, texts: Sequence[str], *, batch_size: int = 64) -> list[list[float]]:
        vectors: list[list[float]] = []
        cleaned = [text.replace("\x00", " ").strip() or " " for text in texts]
        for start in range(0, len(cleaned), batch_size):
            batch = cleaned[start : start + batch_size]
            response = self._client.embeddings.create(model=self._model, input=batch)
            ordered = sorted(response.data, key=lambda row: row.index)
            vectors.extend([list(row.embedding) for row in ordered])
        return vectors
