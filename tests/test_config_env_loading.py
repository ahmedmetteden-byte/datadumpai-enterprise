"""
Regression tests for .env vs OS environment precedence during config bootstrap.
"""

from __future__ import annotations

import importlib
import sys

import config as config_module


def _reload_config(
    monkeypatch,
    *,
    env_file,
    env_file_content: str,
    docker: bool = False,
    local_dev_flag: str | None = None,
    os_environment: dict[str, str] | None = None,
):
    """Reload config with a controlled environment."""

    env_file.write_text(env_file_content, encoding="utf-8")

    for key in (
        "ENVIRONMENT",
        "AUTH_DEV_BYPASS",
        "DATADUMPAI_LOCAL_DEV",
        "RUNNING_IN_DOCKER",
        "DATADUMPAI_ENV_FILE",
    ):
        monkeypatch.delenv(key, raising=False)

    monkeypatch.setenv("DATADUMPAI_ENV_FILE", str(env_file.resolve()))

    if os_environment:
        for key, value in os_environment.items():
            monkeypatch.setenv(key, value)

    if local_dev_flag is not None:
        monkeypatch.setenv("DATADUMPAI_LOCAL_DEV", local_dev_flag)

    if docker:
        monkeypatch.setenv("RUNNING_IN_DOCKER", "true")
    else:
        monkeypatch.delenv("RUNNING_IN_DOCKER", raising=False)

    reloaded = importlib.reload(config_module)
    reloaded._STARTUP_DIAGNOSTICS_PRINTED = False
    return reloaded


def test_local_host_uses_dotenv_when_os_conflicts(tmp_path, monkeypatch, caplog):
    env_file = tmp_path / ".env"

    config = _reload_config(
        monkeypatch,
        env_file=env_file,
        env_file_content="ENVIRONMENT=development\nAUTH_DEV_BYPASS=false\n",
        os_environment={
            "ENVIRONMENT": "production",
            "AUTH_DEV_BYPASS": "true",
        },
        docker=False,
    )

    assert config.is_running_locally() is True
    assert config.ENVIRONMENT == "development"
    assert config.AUTH_DEV_BYPASS is False
    assert config.config_source("ENVIRONMENT") == ".env"
    assert config.config_source("AUTH_DEV_BYPASS") == ".env"
    assert any("ENVIRONMENT differs" in record.message for record in caplog.records)


def test_docker_uses_os_environment_when_conflicts(tmp_path, monkeypatch, caplog):
    env_file = tmp_path / ".env"

    config = _reload_config(
        monkeypatch,
        env_file=env_file,
        env_file_content="ENVIRONMENT=development\nAUTH_DEV_BYPASS=false\n",
        os_environment={
            "ENVIRONMENT": "production",
            "AUTH_DEV_BYPASS": "true",
        },
        docker=True,
    )

    assert config.is_running_locally() is False
    assert config.ENVIRONMENT == "production"
    assert config.AUTH_DEV_BYPASS is True
    assert config.config_source("ENVIRONMENT") == "OS Environment"
    assert config.config_source("AUTH_DEV_BYPASS") == "OS Environment"
    assert any("Using:\nOS Environment" in record.message for record in caplog.records)


def test_local_without_os_uses_dotenv_values(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"

    config = _reload_config(
        monkeypatch,
        env_file=env_file,
        env_file_content="ENVIRONMENT=development\nAUTH_DEV_BYPASS=false\n",
        docker=False,
    )

    assert config.ENVIRONMENT == "development"
    assert config.AUTH_DEV_BYPASS is False
    assert config.config_source("ENVIRONMENT") == ".env"


def test_host_forces_production_precedence_with_local_dev_false(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"

    config = _reload_config(
        monkeypatch,
        env_file=env_file,
        env_file_content="ENVIRONMENT=development\nAUTH_DEV_BYPASS=false\n",
        os_environment={
            "ENVIRONMENT": "production",
            "AUTH_DEV_BYPASS": "true",
        },
        docker=False,
        local_dev_flag="false",
    )

    assert config.is_running_locally() is False
    assert config.ENVIRONMENT == "production"
    assert config.AUTH_DEV_BYPASS is True


def test_validation_message_uses_runtime_values(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"

    config = _reload_config(
        monkeypatch,
        env_file=env_file,
        env_file_content="ENVIRONMENT=production\nAUTH_DEV_BYPASS=true\n",
        docker=True,
        os_environment={
            "ENVIRONMENT": "production",
            "AUTH_DEV_BYPASS": "true",
        },
    )

    warnings = config.validate_production_auth_configuration()
    config_errors = [message for message in warnings if message.startswith("Configuration Error")]

    assert len(config_errors) == 1
    assert "ENVIRONMENT:\nproduction" in config_errors[0]
    assert "AUTH_DEV_BYPASS:\ntrue" in config_errors[0]
    assert "AUTH_DEV_BYPASS=true is only permitted" not in config_errors[0]


def test_startup_diagnostics_print_once(tmp_path, monkeypatch, capsys):
    env_file = tmp_path / ".env"

    config = _reload_config(
        monkeypatch,
        env_file=env_file,
        env_file_content="ENVIRONMENT=development\nAUTH_DEV_BYPASS=false\n",
        docker=False,
    )

    config.print_startup_configuration_diagnostics()
    config.print_startup_configuration_diagnostics()

    captured = capsys.readouterr()
    assert captured.err.count("Configuration") == 1
    assert "development" in captured.err
    assert "AUTH_DEV_BYPASS" in captured.err
    assert str(env_file.resolve()) in captured.err


def test_running_locally_true_on_host_with_development_dotenv(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"

    config = _reload_config(
        monkeypatch,
        env_file=env_file,
        env_file_content="ENVIRONMENT=development\n",
        docker=False,
    )

    assert config.running_locally() is True


def test_auth_dev_bypass_enabled_only_in_development(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"

    config = _reload_config(
        monkeypatch,
        env_file=env_file,
        env_file_content="ENVIRONMENT=development\nAUTH_DEV_BYPASS=true\n",
        docker=False,
    )

    assert config.auth_dev_bypass_enabled() is True

    config = _reload_config(
        monkeypatch,
        env_file=env_file,
        env_file_content="ENVIRONMENT=production\nAUTH_DEV_BYPASS=true\n",
        docker=True,
        os_environment={
            "ENVIRONMENT": "production",
            "AUTH_DEV_BYPASS": "true",
        },
    )

    assert config.auth_dev_bypass_enabled() is False
