"""
Shared fake OpenAI chat-completion double for report-generation tests.

Extracted from tests/test_spa_report_generation_service.py's original
_FakeChatCompletion/_fake_openai_client (kept there too, unchanged, to
avoid an unrelated churn diff) so new tests (the baseline-regression
harness, future Step B/C/E/F/G tests) don't each reinvent it.
"""

from __future__ import annotations


class FakeChatCompletion:
    """Captures every prompt sent to chat.completions.create() and returns
    a canned response, so tests can inspect real prompt construction
    without needing an OPENAI_API_KEY or hitting the network."""

    def __init__(self, response_text: str = "## Executive Summary\nOK.\n"):
        self.response_text = response_text
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)

        class _Choice:
            def __init__(self, content: str):
                self.message = type("Msg", (), {"content": content})()

        class _Response:
            def __init__(self, content: str):
                self.choices = [_Choice(content)]

        return _Response(self.response_text)


def fake_openai_client(response_text: str = "## Executive Summary\nOK.\n"):
    completions = FakeChatCompletion(response_text)
    chat = type("Chat", (), {"completions": completions})()
    client = type("Client", (), {"chat": chat})()
    return client, completions
