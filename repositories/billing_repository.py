"""
Lookup billing records by payment provider identifiers.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import config
from core import user_paths
from core.database import get_database_client, handle_response


def _billing_fields_from_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "payment_provider": row.get("payment_provider"),
        "payment_customer_id": row.get("payment_customer_id"),
        "payment_subscription_id": row.get("payment_subscription_id"),
        "payment_reference": row.get("payment_reference"),
        "cancel_at_period_end": bool(row.get("cancel_at_period_end", False)),
        "current_period_end": row.get("current_period_end"),
    }


def merge_billing_fields(state: dict[str, Any]) -> dict[str, Any]:
    return {
        **state,
        "payment_provider": state.get("payment_provider"),
        "payment_customer_id": state.get("payment_customer_id"),
        "payment_subscription_id": state.get("payment_subscription_id"),
        "payment_reference": state.get("payment_reference"),
        "cancel_at_period_end": bool(state.get("cancel_at_period_end", False)),
        "current_period_end": state.get("current_period_end"),
    }


def find_user_id_by_customer_id(customer_id: str) -> str | None:
    if not customer_id:
        return None

    if config.use_database():
        client = get_database_client()
        response = handle_response(
            client.table("user_usage")
            .select("user_id")
            .eq("payment_customer_id", customer_id)
            .maybe_single()
            .execute(),
            action="find user by customer id",
        )
        if response.data:
            return str(response.data["user_id"])

    users_root = user_paths.get_users_root()
    if not users_root.exists():
        return None

    for user_dir in users_root.iterdir():
        if not user_dir.is_dir():
            continue

        usage_path = user_dir / "usage.json"
        if not usage_path.exists():
            continue

        try:
            usage = json.loads(usage_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue

        if usage.get("payment_customer_id") == customer_id:
            return user_dir.name

    return None


def find_user_id_by_subscription_id(subscription_id: str) -> str | None:
    if not subscription_id:
        return None

    if config.use_database():
        client = get_database_client()
        response = handle_response(
            client.table("user_usage")
            .select("user_id")
            .eq("payment_subscription_id", subscription_id)
            .maybe_single()
            .execute(),
            action="find user by subscription id",
        )
        if response.data:
            return str(response.data["user_id"])

    users_root = user_paths.get_users_root()
    if not users_root.exists():
        return None

    for user_dir in users_root.iterdir():
        if not user_dir.is_dir():
            continue

        usage_path = user_dir / "usage.json"
        if not usage_path.exists():
            continue

        try:
            usage = json.loads(usage_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue

        if usage.get("payment_subscription_id") == subscription_id:
            return user_dir.name

    return None
