"""
Regression tests for best-effort auth cookie persistence.
"""

from __future__ import annotations

import json

import pytest

import core.auth_persistence as auth_persistence
from core.auth_persistence import AUTH_COOKIE_NAME, clear_persisted_tokens


class _FakeCookieManager:
    def __init__(self, *, cookies: dict[str, str] | None = None, delete_error=None) -> None:
        self.cookies = dict(cookies or {})
        self.delete_error = delete_error
        self.deleted: list[str] = []

    def delete(self, name: str) -> None:
        if self.delete_error is not None:
            raise self.delete_error
        if name not in self.cookies:
            raise KeyError(name)
        del self.cookies[name]
        self.deleted.append(name)

    def get(self, name: str):
        return self.cookies.get(name)

    def get_all(self):
        return dict(self.cookies)

    def set(self, name, value, **_kwargs):
        self.cookies[name] = value


@pytest.fixture(autouse=True)
def reset_cookie_manager_cache():
    def _clear_cache(func_name: str) -> None:
        func = getattr(auth_persistence, func_name)
        cache_clear = getattr(func, "cache_clear", None)
        if cache_clear is not None:
            cache_clear()

    _clear_cache("_try_cookie_manager")
    _clear_cache("_cookie_manager")
    yield
    _clear_cache("_try_cookie_manager")
    _clear_cache("_cookie_manager")


def test_clear_persisted_tokens_missing_cookie_is_noop(monkeypatch):
    manager = _FakeCookieManager()
    monkeypatch.setattr("config.auth_dev_bypass_enabled", lambda: False)
    monkeypatch.setattr(auth_persistence, "_try_cookie_manager", lambda: manager)

    clear_persisted_tokens()
    clear_persisted_tokens()

    assert manager.deleted == []


def test_clear_persisted_tokens_deletes_existing_cookie(monkeypatch):
    manager = _FakeCookieManager(
        cookies={AUTH_COOKIE_NAME: json.dumps({"access": "a", "refresh": "r"})}
    )
    monkeypatch.setattr("config.auth_dev_bypass_enabled", lambda: False)
    monkeypatch.setattr(auth_persistence, "_try_cookie_manager", lambda: manager)

    clear_persisted_tokens()

    assert AUTH_COOKIE_NAME not in manager.cookies
    assert manager.deleted == [AUTH_COOKIE_NAME]


def test_clear_persisted_tokens_already_deleted_cookie_is_idempotent(monkeypatch):
    manager = _FakeCookieManager(
        cookies={AUTH_COOKIE_NAME: json.dumps({"access": "a", "refresh": "r"})}
    )
    monkeypatch.setattr("config.auth_dev_bypass_enabled", lambda: False)
    monkeypatch.setattr(auth_persistence, "_try_cookie_manager", lambda: manager)

    clear_persisted_tokens()
    clear_persisted_tokens()

    assert manager.deleted == [AUTH_COOKIE_NAME]


def test_clear_persisted_tokens_survives_cookie_manager_key_error(monkeypatch):
    manager = _FakeCookieManager(delete_error=KeyError(AUTH_COOKIE_NAME))
    monkeypatch.setattr("config.auth_dev_bypass_enabled", lambda: False)
    monkeypatch.setattr(auth_persistence, "_try_cookie_manager", lambda: manager)

    clear_persisted_tokens()


def test_clear_persisted_tokens_survives_unavailable_cookie_manager(monkeypatch):
    monkeypatch.setattr("config.auth_dev_bypass_enabled", lambda: False)
    monkeypatch.setattr(auth_persistence, "_try_cookie_manager", lambda: None)

    clear_persisted_tokens()


def test_clear_persisted_tokens_survives_cookie_manager_exception(monkeypatch):
    class BrokenManager:
        def delete(self, _name):
            raise RuntimeError("cookie manager unavailable")

    monkeypatch.setattr("config.auth_dev_bypass_enabled", lambda: False)
    monkeypatch.setattr(auth_persistence, "_try_cookie_manager", lambda: BrokenManager())

    clear_persisted_tokens()


def test_restore_persisted_tokens_clears_stale_cookie_without_crashing(monkeypatch):
    manager = _FakeCookieManager(cookies={AUTH_COOKIE_NAME: "not-json"})
    monkeypatch.setattr("config.auth_dev_bypass_enabled", lambda: False)
    monkeypatch.setattr(auth_persistence, "_try_cookie_manager", lambda: manager)
    monkeypatch.setattr(auth_persistence, "cookies_are_ready", lambda: True)

    tokens = auth_persistence.restore_persisted_tokens()

    assert tokens is None
    assert AUTH_COOKIE_NAME not in manager.cookies
