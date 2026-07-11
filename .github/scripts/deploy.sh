#!/usr/bin/env bash
# Production deployment for DataDumpAI Enterprise (Docker Compose stack).
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/datadumpai-enterprise}"
GIT_BRANCH="${GIT_BRANCH:-main}"
GIT_REMOTE="${GIT_REMOTE:-origin}"
DEPLOY_REF="${DEPLOY_REF:-}"
export DEPLOY_REF
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"
DEPLOY_STATE_DIR="${DEPLOY_STATE_DIR:-.deploy}"
AUTO_ROLLBACK="${AUTO_ROLLBACK:-true}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

START_TIME="$SECONDS"
ROLLBACK_COMMIT=""
NEW_COMMIT=""
DEPLOY_STATUS="failed"

log() {
  printf '[deploy] %s\n' "$*"
}

section() {
  printf '\n========================================\n'
  printf '%s\n' "$*"
  printf '========================================\n'
}

fail() {
  log "ERROR: $*"
  exit 1
}

on_exit() {
  local exit_code=$?
  local duration=$((SECONDS - START_TIME))

  section "Deployment Summary"
  log "Repository:  ${GIT_REMOTE}/${GIT_BRANCH}"
  log "Directory:   ${APP_DIR}"
  log "Duration:    ${duration}s"

  if [ -n "$ROLLBACK_COMMIT" ]; then
    log "Pre-deploy:  ${ROLLBACK_COMMIT}"
  fi

  if [ -n "$NEW_COMMIT" ]; then
    log "Target:      ${NEW_COMMIT}"
  fi

  if [ -d "$APP_DIR" ]; then
    (
      cd "$APP_DIR"
      log "Active HEAD: $(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
      log "Container status:"
      docker compose -f "$COMPOSE_FILE" ps || true
    )
  fi

  if [ "$exit_code" -eq 0 ]; then
    DEPLOY_STATUS="success"
    log "Overall status: SUCCESS"
  else
    DEPLOY_STATUS="failed"
    log "Overall status: FAILED (exit code $exit_code)"
  fi
}

trap on_exit EXIT

attempt_rollback() {
  if [ "$AUTO_ROLLBACK" != "true" ]; then
    log "AUTO_ROLLBACK=false — skipping automatic rollback."
    return 1
  fi

  if [ -z "$ROLLBACK_COMMIT" ]; then
    log "No pre-deploy commit recorded — cannot roll back automatically."
    return 1
  fi

  section "Automatic Rollback"
  log "Deployment failed after container restart. Rolling back to $ROLLBACK_COMMIT"
  log "Automatic rollback is used here because only application containers are replaced;"
  log "no database migrations are performed during deploy. See .github/README.md for limits."

  if bash "$SCRIPT_DIR/rollback.sh" "$ROLLBACK_COMMIT"; then
    log "Automatic rollback completed successfully."
    return 0
  fi

  log "Automatic rollback failed — follow manual recovery in .github/README.md"
  return 1
}

main() {
  section "DataDumpAI Enterprise Deployment"

  bash "$SCRIPT_DIR/verify.sh"

  cd "$APP_DIR"
  mkdir -p "$DEPLOY_STATE_DIR"

  ROLLBACK_COMMIT="$(git rev-parse HEAD)"
  printf '%s\n' "$ROLLBACK_COMMIT" >"$DEPLOY_STATE_DIR/pre-deploy-commit"

  log "Pre-deploy commit: $ROLLBACK_COMMIT"

  section "Sync Repository"
  local target_ref="${DEPLOY_REF:-${GIT_REMOTE}/${GIT_BRANCH}}"
  log "Fetching ${target_ref}..."
  git fetch "$GIT_REMOTE" --prune

  log "Resetting to ${target_ref} (no merge commits)..."
  git reset --hard "$target_ref"

  NEW_COMMIT="$(git rev-parse HEAD)"
  log "Deployed commit: $NEW_COMMIT"

  # Use scripts from the freshly synced repository for post-deploy steps.
  SCRIPT_DIR="$APP_DIR/.github/scripts"

  if [ "$ROLLBACK_COMMIT" = "$NEW_COMMIT" ]; then
    log "No new commits since last deployment."
  fi

  section "Build and Restart"
  log "Building Docker images..."
  docker compose -f "$COMPOSE_FILE" build

  log "Restarting containers..."
  docker compose -f "$COMPOSE_FILE" up -d

  section "Health Checks"
  if ! bash "$SCRIPT_DIR/health-check.sh"; then
    attempt_rollback || true
    fail "health checks failed"
  fi

  printf '%s\n' "$NEW_COMMIT" >"$DEPLOY_STATE_DIR/last-successful-commit"

  section "Cleanup"
  bash "$SCRIPT_DIR/cleanup.sh"

  section "Deployment Complete"
  log "Commit ${NEW_COMMIT} is live."
}

main "$@"
