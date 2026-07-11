#!/usr/bin/env bash
# Create a temporary .env for docker compose config validation in CI.
# Production deploys use the real server .env — never commit secrets here.
set -euo pipefail

ROOT="${1:-.}"
CI_ENV_TEMPLATE="${ROOT}/.env.ci.example"
TARGET="${ROOT}/.env"

if [ -f "$TARGET" ]; then
  printf '[prepare-ci-compose-env] %s already exists; leaving it unchanged\n' "$TARGET" >&2
  exit 0
fi

if [ ! -f "$CI_ENV_TEMPLATE" ]; then
  printf '[prepare-ci-compose-env] missing template: %s\n' "$CI_ENV_TEMPLATE" >&2
  exit 1
fi

cp "$CI_ENV_TEMPLATE" "$TARGET"
printf '[prepare-ci-compose-env] created %s from %s for compose validation\n' "$TARGET" "$CI_ENV_TEMPLATE"
