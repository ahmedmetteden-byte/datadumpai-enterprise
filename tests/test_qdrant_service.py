"""
Unit tests for QdrantService's query-filter construction — no real Qdrant
server involved, a fake client captures the filter passed to
query_points().
"""

from __future__ import annotations

from services.qdrant_service import QdrantService


class _FakeResponse:
    def __init__(self):
        self.points = []


class _FakeClient:
    def __init__(self):
        self.calls: list[dict] = []

    def get_collections(self):
        class _Collections:
            collections = [type("C", (), {"name": "datadumpai_chunks"})()]

        return _Collections()

    def query_points(self, **kwargs):
        self.calls.append(kwargs)
        return _FakeResponse()


def _service_with_fake_client() -> tuple[QdrantService, _FakeClient]:
    service = QdrantService()
    fake_client = _FakeClient()
    service._client = fake_client
    return service, fake_client


def test_search_filters_by_workspace_id_only_when_no_document_id_given():
    service, fake_client = _service_with_fake_client()
    service.search(workspace_id="ws1", query_vector=[0.1], limit=5)

    call = fake_client.calls[0]
    conditions = call["query_filter"].must
    assert len(conditions) == 1
    assert conditions[0].key == "workspace_id"
    assert conditions[0].match.value == "ws1"


def test_search_adds_document_id_as_an_additional_filter_not_a_replacement():
    """Document Coverage fix: the coverage-guarantee query must scope to
    one specific document WITHOUT ever loosening workspace isolation —
    both conditions must be present, AND'd together (Qdrant's `must` list
    semantics), never just the document_id alone."""

    service, fake_client = _service_with_fake_client()
    service.search(workspace_id="ws1", query_vector=[0.1], limit=5, document_id="doc-42")

    call = fake_client.calls[0]
    conditions = call["query_filter"].must
    assert len(conditions) == 2

    by_key = {c.key: c.match.value for c in conditions}
    assert by_key == {"workspace_id": "ws1", "document_id": "doc-42"}


def test_search_omits_document_id_filter_when_none():
    service, fake_client = _service_with_fake_client()
    service.search(workspace_id="ws1", query_vector=[0.1], limit=5, document_id=None)

    conditions = fake_client.calls[0]["query_filter"].must
    assert len(conditions) == 1
    assert conditions[0].key == "workspace_id"
