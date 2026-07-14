"""
DataDumpAI v1.0
User-facing feedback helpers — loading states and friendly errors.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Generator

import streamlit as st


def friendly_message(exc: Exception) -> str:
    """Turn an exception into a clear, user-facing message."""

    from services.usage_service import UsageLimitError

    if isinstance(exc, UsageLimitError):
        return str(exc)

    from services.auth_service import AuthError

    if isinstance(exc, AuthError):
        title = getattr(exc, "title", None)
        if title:
            return f"{title}\n\n{exc}"
        return str(exc)

    detail = str(exc).strip()

    if isinstance(exc, ValueError):
        if detail:
            return detail
        return "Please check your input and try again."

    if isinstance(exc, FileNotFoundError):
        if detail:
            return f"File not found. {detail}"
        return "That file could not be found. It may have been deleted."

    if isinstance(exc, PermissionError):
        return "Permission denied. Close the file if it is open elsewhere and try again."

    if isinstance(exc, ConnectionError) or type(exc).__name__ == "APIConnectionError":
        return (
            "Could not reach the AI service. Check your internet connection, "
            "VPN or proxy settings, and that OPENAI_API_KEY is set in .env. "
            "On Windows, run `pip install -r requirements.txt` and restart the app "
            "if SSL certificate errors block OpenAI."
        )

    detail_lower = detail.lower()
    if "timeout" in detail_lower or "timed out" in detail_lower:
        return (
            "Report generation took too long. Try selecting fewer documents "
            "or use smaller files, then try again."
        )

    if detail:
        return f"Something went wrong: {detail}"

    return "Something went wrong. Please try again."


def show_error(exc: Exception) -> None:
    """Display a user-friendly error banner."""

    st.error(friendly_message(exc))


def show_success(message: str) -> None:
    """Display a success banner."""

    st.success(message)


def show_empty_state(
    *,
    title: str,
    message: str,
    icon: str = "📭",
) -> None:
    """Display a consistent empty-state panel."""

    st.markdown(
        f"""
<div class="dde-empty-state">
<div class="dde-empty-icon">{icon}</div>
<div class="dde-empty-title">{title}</div>
<div class="dde-empty-message">{message}</div>
</div>
""",
        unsafe_allow_html=True,
    )


@contextmanager
def loading(message: str) -> Generator[None, None, None]:
    """Show a spinner while work is in progress."""

    with st.spinner(message):
        yield


@contextmanager
def progressive_generation(
    *,
    initial_label: str = "Understanding request...",
) -> Generator[Any, None, None]:
    """Show progressive AI status updates during report generation."""

    with st.status(initial_label, expanded=True) as status:
        yield status


def advance_generation_status(
    status: Any,
    label: str,
    *,
    state: str = "running",
) -> None:
    """Update a progressive generation status step."""

    status.update(label=label, state=state)
