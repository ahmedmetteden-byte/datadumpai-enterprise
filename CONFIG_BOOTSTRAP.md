# Environment bootstrap

DataDumpAI loads configuration from the project `.env` file and the OS
environment. Precedence depends on whether the process is running locally or
inside a production container.

## Local development (`.env` wins)

`load_dotenv(..., override=True)` when **local mode** is active.

Local mode is enabled when:

- `DATADUMPAI_LOCAL_DEV=true`, or
- the process is **not** in Docker and `ENVIRONMENT=development` (OS or `.env`), or
- the process is **not** in Docker and no explicit production signal is set
  (default host behaviour)

Set `DATADUMPAI_LOCAL_DEV=false` on a host to use production-style precedence
without Docker.

## Production containers (OS wins)

`load_dotenv(..., override=False)` when running inside Docker
(`/.dockerenv` or `RUNNING_IN_DOCKER=true`) unless `DATADUMPAI_LOCAL_DEV=true`.

Container orchestrators should inject secrets via the OS environment
(`docker compose env_file`, Kubernetes secrets, etc.). Existing OS variables are
never overwritten.

## Conflict logging

When both OS and `.env` define `ENVIRONMENT` or `AUTH_DEV_BYPASS` with different
values, a warning is logged indicating which source was used.

## Startup diagnostics

In `ENVIRONMENT=development` or `DEBUG=true`, the app prints configuration
sources once to stderr on startup.

## Tests

Set `DATADUMPAI_ENV_FILE` to point at a temporary `.env` when testing bootstrap
precedence (`tests/test_config_env_loading.py`).
