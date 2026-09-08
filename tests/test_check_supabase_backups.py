"""
Tests for scripts/check_supabase_backups.py — the read-only Supabase
backup-freshness check. Covers evaluate()'s decision logic against fixture
payloads shaped like the real Management API's backups-list response
(healthy, stale, missing, failed-backup, PITR-disabled cases) and
fetch_backups()/main()'s handling of network and HTTP failures, all via
mocked requests calls — none of this touches a real Supabase project.

Also asserts the script never references the restore/PITR endpoint at
all, since that's the one thing this script must never call.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from scripts.check_supabase_backups import (
    BackupCheckError,
    evaluate,
    fetch_backups,
    main,
)


def _iso(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def test_evaluate_healthy_with_pitr_and_recent_backup():
    now = datetime.now(timezone.utc)
    payload = {
        "pitr_enabled": True,
        "backups": [
            {"status": "COMPLETED", "inserted_at": _iso(now - timedelta(hours=2))},
        ],
        "physical_backup_data": {},
    }

    result = evaluate(payload, max_age_hours=26)

    assert result["healthy"] is True
    assert result["problems"] == []
    assert result["pitr_enabled"] is True
    assert result["backup_count"] == 1


def test_evaluate_unhealthy_when_pitr_disabled():
    now = datetime.now(timezone.utc)
    payload = {
        "pitr_enabled": False,
        "backups": [{"status": "COMPLETED", "inserted_at": _iso(now)}],
        "physical_backup_data": {},
    }

    result = evaluate(payload, max_age_hours=26)

    assert result["healthy"] is False
    assert any("PITR" in p or "recovery" in p for p in result["problems"])


def test_evaluate_unhealthy_when_latest_backup_is_stale():
    now = datetime.now(timezone.utc)
    payload = {
        "pitr_enabled": True,
        "backups": [
            {"status": "COMPLETED", "inserted_at": _iso(now - timedelta(hours=48))},
        ],
        "physical_backup_data": {},
    }

    result = evaluate(payload, max_age_hours=26)

    assert result["healthy"] is False
    assert any("old" in p for p in result["problems"])


def test_evaluate_unhealthy_when_no_backups_at_all():
    payload = {"pitr_enabled": True, "backups": [], "physical_backup_data": {}}

    result = evaluate(payload, max_age_hours=26)

    assert result["healthy"] is False
    assert any("No completed backup" in p for p in result["problems"])
    assert result["latest_completed_at"] is None


def test_evaluate_unhealthy_when_a_backup_failed():
    now = datetime.now(timezone.utc)
    payload = {
        "pitr_enabled": True,
        "backups": [
            {"status": "COMPLETED", "inserted_at": _iso(now - timedelta(hours=1))},
            {"status": "FAILED", "inserted_at": _iso(now - timedelta(hours=25))},
        ],
        "physical_backup_data": {},
    }

    result = evaluate(payload, max_age_hours=26)

    assert result["healthy"] is False
    assert any("FAILED" in p for p in result["problems"])


def test_evaluate_uses_physical_backup_data_when_more_recent():
    now = datetime.now(timezone.utc)
    physical_recent = now - timedelta(hours=1)
    payload = {
        "pitr_enabled": True,
        "backups": [
            {"status": "COMPLETED", "inserted_at": _iso(now - timedelta(hours=48))},
        ],
        "physical_backup_data": {
            "latest_physical_backup_date_unix": int(physical_recent.timestamp()),
        },
    }

    result = evaluate(payload, max_age_hours=26)

    assert result["healthy"] is True


def test_evaluate_ignores_backups_missing_inserted_at():
    payload = {
        "pitr_enabled": True,
        "backups": [{"status": "COMPLETED"}],
        "physical_backup_data": {},
    }

    result = evaluate(payload, max_age_hours=26)

    assert result["healthy"] is False
    assert result["latest_completed_at"] is None


def test_fetch_backups_raises_on_network_error(monkeypatch):
    import requests

    import scripts.check_supabase_backups as check_module

    def _raise(*args, **kwargs):
        raise requests.ConnectionError("boom")

    monkeypatch.setattr(check_module.requests, "get", _raise)

    with pytest.raises(BackupCheckError, match="Could not reach"):
        fetch_backups("proj123", "token123")


def test_fetch_backups_raises_on_non_2xx(monkeypatch):
    import scripts.check_supabase_backups as check_module

    mock_response = MagicMock(ok=False, status_code=401, text="Unauthorized")
    monkeypatch.setattr(
        check_module.requests, "get", MagicMock(return_value=mock_response)
    )

    with pytest.raises(BackupCheckError, match="401"):
        fetch_backups("proj123", "token123")


def test_fetch_backups_raises_on_non_json_body(monkeypatch):
    import scripts.check_supabase_backups as check_module

    mock_response = MagicMock(ok=True, status_code=200)
    mock_response.json.side_effect = ValueError("not json")
    monkeypatch.setattr(
        check_module.requests, "get", MagicMock(return_value=mock_response)
    )

    with pytest.raises(BackupCheckError, match="non-JSON"):
        fetch_backups("proj123", "token123")


def test_fetch_backups_returns_parsed_payload_on_success(monkeypatch):
    import scripts.check_supabase_backups as check_module

    mock_response = MagicMock(ok=True, status_code=200)
    mock_response.json.return_value = {"pitr_enabled": True, "backups": []}
    monkeypatch.setattr(
        check_module.requests, "get", MagicMock(return_value=mock_response)
    )

    result = fetch_backups("proj123", "token123")

    assert result == {"pitr_enabled": True, "backups": []}


def test_main_exits_2_when_env_config_is_missing(monkeypatch, capsys):
    monkeypatch.delenv("SUPABASE_PROJECT_REF", raising=False)
    monkeypatch.delenv("SUPABASE_ACCESS_TOKEN", raising=False)
    monkeypatch.setattr("sys.argv", ["check_supabase_backups.py"])

    exit_code = main()

    assert exit_code == 2
    assert "SUPABASE_PROJECT_REF" in capsys.readouterr().out


def test_main_exits_0_when_healthy(monkeypatch, capsys):
    import scripts.check_supabase_backups as check_module

    monkeypatch.setenv("SUPABASE_PROJECT_REF", "proj123")
    monkeypatch.setenv("SUPABASE_ACCESS_TOKEN", "token123")
    monkeypatch.setattr("sys.argv", ["check_supabase_backups.py"])

    now = datetime.now(timezone.utc)
    mock_response = MagicMock(ok=True, status_code=200)
    mock_response.json.return_value = {
        "pitr_enabled": True,
        "backups": [{"status": "COMPLETED", "inserted_at": _iso(now)}],
        "physical_backup_data": {},
    }
    monkeypatch.setattr(
        check_module.requests, "get", MagicMock(return_value=mock_response)
    )

    exit_code = main()

    assert exit_code == 0
    assert "OK" in capsys.readouterr().out


def test_main_exits_1_when_unhealthy(monkeypatch, capsys):
    import scripts.check_supabase_backups as check_module

    monkeypatch.setenv("SUPABASE_PROJECT_REF", "proj123")
    monkeypatch.setenv("SUPABASE_ACCESS_TOKEN", "token123")
    monkeypatch.setattr("sys.argv", ["check_supabase_backups.py"])

    mock_response = MagicMock(ok=True, status_code=200)
    mock_response.json.return_value = {
        "pitr_enabled": False,
        "backups": [],
        "physical_backup_data": {},
    }
    monkeypatch.setattr(
        check_module.requests, "get", MagicMock(return_value=mock_response)
    )

    exit_code = main()

    assert exit_code == 1
    assert "UNHEALTHY" in capsys.readouterr().out


def test_main_exits_2_on_fetch_error(monkeypatch, capsys):
    import scripts.check_supabase_backups as check_module

    monkeypatch.setenv("SUPABASE_PROJECT_REF", "proj123")
    monkeypatch.setenv("SUPABASE_ACCESS_TOKEN", "token123")
    monkeypatch.setattr("sys.argv", ["check_supabase_backups.py"])

    import requests

    monkeypatch.setattr(
        check_module.requests,
        "get",
        MagicMock(side_effect=requests.ConnectionError("boom")),
    )

    exit_code = main()

    assert exit_code == 2
    assert "ERROR" in capsys.readouterr().out


def test_script_never_references_the_restore_pitr_endpoint():
    """The one thing this script must never do: call the destructive
    restore/PITR endpoint. Guard against that being reintroduced later."""

    script_path = Path(__file__).resolve().parents[1] / "scripts" / "check_supabase_backups.py"
    source = script_path.read_text()

    # The docstring explains why restore-pitr must never be called — only
    # check actual code (past the module docstring) never calls it.
    code = source.split('"""', 2)[2]
    assert "restore-pitr" not in code
    for mutating_call in ("requests.post", "requests.put", "requests.patch", "requests.delete"):
        assert mutating_call not in code, f"{mutating_call} found — this script must stay read-only"
