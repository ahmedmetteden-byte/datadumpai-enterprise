"""
Regression test: an Intelligence Studio conversation must survive past the
request that created it.

Conversations used to live only in project["studio_conversations"], which
the Supabase project repository never actually persisted (it only syncs
documents/reports/exports) — so POST /conversations returned 201, but the
very next request (POST .../messages) 404'd with "Conversation not found."
"""

from __future__ import annotations

from api.auth_jwt import AuthenticatedPrincipal
from api.routers.intelligence import (
    get_conversation,
    list_conversations,
    send_message,
    start_conversation,
)
from api.schemas import SendMessageBody, StartConversationBody
from services.project_service import ProjectService
from tests.conftest import TEST_USER


def test_conversation_is_retrievable_after_the_request_ends(
    isolated_env, project_service: ProjectService
):
    project = project_service.create_project("Conversation Persistence Project")
    principal = AuthenticatedPrincipal(user=TEST_USER, access_token="test-token")

    created = start_conversation(
        project["id"],
        StartConversationBody(),
        principal,
        TEST_USER,
    )

    # Simulate a brand-new request: call the next endpoint fresh, with no
    # shared state except what's on disk/in Supabase.
    fetched = get_conversation(project["id"], created.id, principal, TEST_USER)
    assert fetched.id == created.id

    updated = send_message(
        project["id"],
        created.id,
        SendMessageBody(content="What changed since last quarter?"),
        principal,
        TEST_USER,
    )
    assert updated.id == created.id
    assert len(updated.messages) == 2  # user message + assistant reply
    assert updated.messages[0].content == "What changed since last quarter?"

    # And it should show up in the conversation list afterwards too.
    listed = list_conversations(project["id"], principal, TEST_USER)
    assert any(item.id == created.id for item in listed)
