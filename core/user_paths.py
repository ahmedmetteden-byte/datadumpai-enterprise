"""
Per-user filesystem layout for isolated projects, documents, and usage.
"""

from __future__ import annotations

from pathlib import Path


def get_users_root() -> Path:
    """Return the parent directory containing all user data folders."""

    root = Path("data/users")
    root.mkdir(parents=True, exist_ok=True)
    return root


def get_user_data_root(user_id: str) -> Path:
    """Return the root directory for one user's persisted data."""

    root = get_users_root() / user_id
    root.mkdir(parents=True, exist_ok=True)
    return root


def get_user_projects_json(user_id: str) -> Path:
    """Return the project index file for one user."""

    return get_user_data_root(user_id) / "projects.json"


def get_user_projects_root(user_id: str) -> Path:
    """Return the on-disk projects folder for one user."""

    root = get_user_data_root(user_id) / "projects"
    root.mkdir(parents=True, exist_ok=True)
    return root


def get_user_usage_json(user_id: str) -> Path:
    """Return the usage tracking file for one user."""

    return get_user_data_root(user_id) / "usage.json"


def get_user_profile_json(user_id: str) -> Path:
    """Return the local profile metadata file for one user."""

    return get_user_data_root(user_id) / "profile.json"
