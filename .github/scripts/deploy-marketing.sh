#!/usr/bin/env bash
# Production deployment for the Next.js marketing site (PM2).
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/datadumpai-enterprise}"
MARKETING_DIR="${MARKETING_DIR:-$APP_DIR/marketing-site}"
GIT_BRANCH="${GIT_BRANCH:-main}"
GIT_REMOTE="${GIT_REMOTE:-origin}"
PM2_PROCESS_NAME="${PM2_PROCESS_NAME:-datadump-marketing}"
MARKETING_PORT="${MARKETING_PORT:-3000}"
HEALTH_TIMEOUT_SECONDS="${HEALTH_TIMEOUT_SECONDS:-120}"
HEALTH_INTERVAL_SECONDS="${HEALTH_INTERVAL_SECONDS:-5}"

START_TIME="$SECONDS"

log() {
  printf '[deploy-marketing] %s\n' "$*"
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

require_command() {
  local cmd="$1"
  command -v "$cmd" >/dev/null 2>&1 || fail "required command not found: $cmd"
}

wait_for_marketing() {
  local url="http://127.0.0.1:${MARKETING_PORT}/"
  local deadline=$((SECONDS + HEALTH_TIMEOUT_SECONDS))

  log "Waiting for marketing site at $url"

  while ((SECONDS < deadline)); do
    local status
    status="$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "$url" || true)"
    if [ "$status" = "200" ] || [ "$status" = "301" ] || [ "$status" = "302" ]; then
      log "Marketing site responded with HTTP $status"
      return 0
    fi
    sleep "$HEALTH_INTERVAL_SECONDS"
  done

  fail "marketing site did not become healthy within ${HEALTH_TIMEOUT_SECONDS}s"
}

on_exit() {
  local exit_code=$?
  local duration=$((SECONDS - START_TIME))

  section "Marketing Deployment Summary"
  log "Directory: ${MARKETING_DIR}"
  log "Duration:  ${duration}s"
  log "PM2:       ${PM2_PROCESS_NAME}"

  if command -v pm2 >/dev/null 2>&1; then
    pm2 describe "$PM2_PROCESS_NAME" 2>/dev/null | sed -n '1,12p' || true
  fi

  if [ "$exit_code" -eq 0 ]; then
    log "Overall status: SUCCESS"
  else
    log "Overall status: FAILED (exit code $exit_code)"
  fi
}

trap on_exit EXIT

main() {
  require_command git
  require_command npm
  require_command pm2
  require_command curl

  if [ ! -d "$APP_DIR" ]; then
    fail "application directory does not exist: $APP_DIR"
  fi

  if [ ! -d "$MARKETING_DIR" ]; then
    fail "marketing directory does not exist: $MARKETING_DIR"
  fi

  section "Marketing Site Deployment"

  cd "$APP_DIR"
  log "Syncing repository to ${GIT_REMOTE}/${GIT_BRANCH}..."
  git fetch "$GIT_REMOTE" "$GIT_BRANCH" --prune
  git reset --hard "${GIT_REMOTE}/${GIT_BRANCH}"

  cd "$MARKETING_DIR"

  if [ ! -f .env.local ]; then
    fail "missing marketing-site/.env.local on the server"
  fi

  log "Installing dependencies..."
  npm ci

  log "Building production bundle..."
  npm run build

  log "Restarting PM2 process: $PM2_PROCESS_NAME"
  if pm2 describe "$PM2_PROCESS_NAME" >/dev/null 2>&1; then
    pm2 restart "$PM2_PROCESS_NAME"
  else
    pm2 start npm --name "$PM2_PROCESS_NAME" -- start
    pm2 save
  fi

  wait_for_marketing

  section "Marketing Deployment Complete"
}

main "$@"
