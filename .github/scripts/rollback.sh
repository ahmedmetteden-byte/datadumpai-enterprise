#!/usr/bin/env bash
# Roll back the application stack to a previously recorded commit.
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/datadumpai-enterprise}"
ROLLBACK_COMMIT="${1:-}"
DEPLOY_STATE_DIR="${DEPLOY_STATE_DIR:-.deploy}"
PRE_DEPLOY_FILE="${DEPLOY_STATE_DIR}/pre-deploy-commit"
LAST_SUCCESS_FILE="${DEPLOY_STATE_DIR}/last-successful-commit"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

log() {
  printf '[rollback] %s\n' "$*"
}

fail() {
  log "ERROR: $*"
  exit 1
}

resolve_commit() {
  if [ -n "$ROLLBACK_COMMIT" ]; then
    printf '%s\n' "$ROLLBACK_COMMIT"
    return 0
  fi

  if [ -f "$PRE_DEPLOY_FILE" ]; then
    tr -d '[:space:]' <"$PRE_DEPLOY_FILE"
    return 0
  fi

  if [ -f "$LAST_SUCCESS_FILE" ]; then
    tr -d '[:space:]' <"$LAST_SUCCESS_FILE"
    return 0
  fi

  return 1
}

main() {
  if [ ! -d "$APP_DIR" ]; then
    fail "application directory does not exist: $APP_DIR"
  fi

  cd "$APP_DIR"

  local target_commit
  if ! target_commit="$(resolve_commit)"; then
    fail "no rollback commit provided and no state files found in $DEPLOY_STATE_DIR"
  fi

  if ! git cat-file -e "${target_commit}^{commit}" 2>/dev/null; then
    fail "rollback commit is not available locally: $target_commit"
  fi

  log "Rolling back repository to $target_commit"
  git reset --hard "$target_commit"

  log "Rebuilding Docker images from rolled-back commit..."
  docker compose -f "$COMPOSE_FILE" build

  log "Restarting services..."
  docker compose -f "$COMPOSE_FILE" up -d

  log "Running post-rollback health checks..."
  if ! bash "$SCRIPT_DIR/health-check.sh"; then
    fail "rollback completed but health checks still failing — manual intervention required"
  fi

  printf '%s\n' "$target_commit" >"$LAST_SUCCESS_FILE"
  log "Rollback successful. Active commit: $(git rev-parse --short HEAD)"
}

main "$@"
