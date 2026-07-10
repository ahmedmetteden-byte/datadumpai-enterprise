"""
Database backend selection tests.
"""

from __future__ import annotations

from tests.conftest import TEST_USER_ID


def test_use_database_defaults_to_supabase_when_configured(monkeypatch):
    monkeypatch.delenv("DATABASE_BACKEND", raising=False)
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-key")

    import importlib

    import config

    importlib.reload(config)

    assert config.DATABASE_BACKEND == "supabase"
    assert config.use_database() is True


def test_use_database_falls_back_when_supabase_missing(monkeypatch):
    monkeypatch.delenv("DATABASE_BACKEND", raising=False)
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)

    import importlib

    import config

    importlib.reload(config)

    assert config.DATABASE_BACKEND == "supabase"
    assert config.use_database() is False


def test_use_database_enables_supabase_backend(monkeypatch):
    monkeypatch.setenv("DATABASE_BACKEND", "supabase")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-key")

    import importlib

    import config

    importlib.reload(config)

    assert config.use_database() is True


def test_project_repository_uses_json_backend_by_default(monkeypatch, isolated_env):
    monkeypatch.setattr("config.use_database", lambda: False)

    from repositories.json_project_repository import JsonProjectRepository
    from repositories.project_repository import ProjectRepository

    repository = ProjectRepository(user_id=TEST_USER_ID)

    assert isinstance(repository._impl, JsonProjectRepository)
