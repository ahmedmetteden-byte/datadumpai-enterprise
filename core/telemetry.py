"""
Product analytics — local event log with optional PostHog forwarding.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

import config


def track(
    event: str,
    *,
    user_id: str | None = None,
    properties: dict[str, Any] | None = None,
) -> None:
    """Record a product analytics event."""

    if not config.ANALYTICS_ENABLED:
        return

    payload = {
        "event": event,
        "user_id": user_id,
        "properties": properties or {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    _write_local_event(payload)

    if config.ANALYTICS_PROVIDER == "posthog" and config.POSTHOG_API_KEY:
        _send_posthog(payload)


def identify(user_id: str, *, traits: dict[str, Any] | None = None) -> None:
    if not config.ANALYTICS_ENABLED:
        return

    track(
        "$identify",
        user_id=user_id,
        properties=traits or {},
    )


def _write_local_event(payload: dict[str, Any]) -> None:
    path = Path(config.ANALYTICS_EVENTS_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)

    events: list[dict[str, Any]] = []
    if path.exists():
        try:
            events = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            events = []

    events.append(payload)
    if len(events) > 5000:
        events = events[-5000:]

    path.write_text(json.dumps(events, indent=2), encoding="utf-8")


def _send_posthog(payload: dict[str, Any]) -> None:
    try:
        requests.post(
            f"{config.POSTHOG_HOST.rstrip('/')}/capture/",
            json={
                "api_key": config.POSTHOG_API_KEY,
                "event": payload["event"],
                "distinct_id": payload.get("user_id") or "anonymous",
                "properties": payload.get("properties", {}),
                "timestamp": payload["timestamp"],
            },
            timeout=5,
        )
    except requests.RequestException:
        pass


def get_recent_events(limit: int = 100) -> list[dict[str, Any]]:
    path = Path(config.ANALYTICS_EVENTS_PATH)
    if not path.exists():
        return []

    try:
        events = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []

    return list(reversed(events[-limit:]))
