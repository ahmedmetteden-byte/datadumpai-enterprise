#!/usr/bin/env bash
# Pre-deployment validation for the production application stack.
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/datadumpai-enterprise}"
REQUIRED_BRANCH="${REQUIRED_BRANCH:-main}"
DEPLOY_REF="${DEPLOY_REF:-}"
GIT_REMOTE="${GIT_REMOTE:-origin}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"
COMPOSE_MIN_VERSION="${COMPOSE_MIN_VERSION:-2.0.0}"
DOCKER_MIN_VERSION="${DOCKER_MIN_VERSION:-20.10.0}"

log() {
  printf '[verify] %s\n' "$*"
}

fail() {
  log "ERROR: $*"
  exit 1
}

require_command() {
  local cmd="$1"
  command -v "$cmd" >/dev/null 2>&1 || fail "required command not found: $cmd"
}

version_ge() {
  local current="${1#v}"
  local minimum="${2#v}"
  [ "$(printf '%s\n' "$minimum" "$current" | sort -V | head -n1)" = "$minimum" ]
}

read_compose_version() {
  if docker compose version --short >/dev/null 2>&1; then
    docker compose version --short
    return 0
  fi

  docker compose version 2>/dev/null | awk 'NF { version=$NF } END { print version }'
}

validate_docker_toolchain() {
  require_command docker

  if ! docker compose version >/dev/null 2>&1; then
    fail "docker compose plugin is not available (install Docker Compose v2)"
  fi

  if ! docker info >/dev/null 2>&1; then
    fail "docker daemon is not running or is not accessible to the deploy user"
  fi

  local compose_version docker_version
  compose_version="$(read_compose_version)"
  docker_version="$(docker version --format '{{.Server.Version}}' 2>/dev/null || true)"

  if [ -z "$compose_version" ]; then
    fail "unable to determine docker compose version"
  fi

  if ! version_ge "$compose_version" "$COMPOSE_MIN_VERSION"; then
    fail "docker compose ${compose_version} is below minimum v${COMPOSE_MIN_VERSION}"
  fi

  if [ -n "$docker_version" ] && ! version_ge "$docker_version" "$DOCKER_MIN_VERSION"; then
    fail "docker engine ${docker_version} is below minimum v${DOCKER_MIN_VERSION}"
  fi

  log "Docker Engine version: ${docker_version:-unknown}"
  log "Docker Compose version: ${compose_version}"
}

main() {
  require_command git
  validate_docker_toolchain

  if [ ! -d "$APP_DIR" ]; then
    fail "application directory does not exist: $APP_DIR"
  fi

  cd "$APP_DIR"

  if [ ! -d .git ]; then
    fail "not a git repository: $APP_DIR"
  fi

  if [ ! -f "$COMPOSE_FILE" ]; then
    fail "missing compose file: $APP_DIR/$COMPOSE_FILE"
  fi

  if [ ! -f .env ]; then
    fail "missing .env file (secrets are required for production deploys)"
  fi

  if [ ! -r .env ]; then
    fail ".env exists but is not readable by the deploy user"
  fi

  log "Validating Docker Compose configuration..."
  docker compose -f "$COMPOSE_FILE" config >/dev/null

  if ! git remote get-url origin >/dev/null 2>&1; then
    fail "git remote 'origin' is not configured"
  fi

  log "Fetching origin to verify connectivity..."
  if [ -n "$DEPLOY_REF" ]; then
    git fetch "$GIT_REMOTE" --prune
    if ! git rev-parse --verify --quiet "${DEPLOY_REF}^{commit}" >/dev/null; then
      fail "deploy ref is not available after fetch: $DEPLOY_REF"
    fi
  else
    git fetch "$GIT_REMOTE" "$REQUIRED_BRANCH" --prune
    if ! git show-ref --verify --quiet "refs/remotes/${GIT_REMOTE}/${REQUIRED_BRANCH}"; then
      fail "${GIT_REMOTE}/${REQUIRED_BRANCH} does not exist"
    fi
  fi

  log "Verification passed for $APP_DIR"
}

main "$@"
