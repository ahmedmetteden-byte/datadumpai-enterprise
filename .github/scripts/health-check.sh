#!/usr/bin/env bash
# Wait for Docker services and verify Streamlit + webhook health endpoints.
set -euo pipefail

STREAMLIT_HEALTH_URL="${STREAMLIT_HEALTH_URL:-http://127.0.0.1:8501/_stcore/health}"
WEBHOOK_HEALTH_URL="${WEBHOOK_HEALTH_URL:-http://127.0.0.1:8001/health}"
HEALTH_TIMEOUT_SECONDS="${HEALTH_TIMEOUT_SECONDS:-180}"
HEALTH_INTERVAL_SECONDS="${HEALTH_INTERVAL_SECONDS:-5}"
COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-}"

log() {
  printf '[health-check] %s\n' "$*"
}

require_command() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    log "ERROR: required command not found: $cmd"
    exit 1
  fi
}

check_endpoint() {
  local name="$1"
  local url="$2"

  if curl -fsS --max-time 10 "$url" >/dev/null; then
    log "OK: $name ($url)"
    return 0
  fi

  log "UNHEALTHY: $name ($url)"
  return 1
}

wait_for_compose_health() {
  local compose_cmd=("$@")
  local deadline=$((SECONDS + HEALTH_TIMEOUT_SECONDS))

  log "Waiting up to ${HEALTH_TIMEOUT_SECONDS}s for Docker health checks..."

  while ((SECONDS < deadline)); do
    mapfile -t health_states < <(
      "${compose_cmd[@]}" ps --format '{{.Health}}' 2>/dev/null | sed '/^$/d'
    )

    if [ "${#health_states[@]}" -eq 0 ]; then
      log "Compose health metadata not available yet; continuing with HTTP checks."
      return 0
    fi

    local all_healthy=1
    for state in "${health_states[@]}"; do
      if [ "$state" != "healthy" ]; then
        log "Container health state: $state"
        all_healthy=0
        break
      fi
    done

    if [ "$all_healthy" -eq 1 ]; then
      log "All Docker health checks report healthy."
      return 0
    fi

    sleep "$HEALTH_INTERVAL_SECONDS"
  done

  log "WARNING: Timed out waiting for Docker health checks; falling back to HTTP probes."
}

main() {
  require_command curl

  local compose_cmd=(docker compose)
  if [ -n "$COMPOSE_PROJECT_NAME" ]; then
    compose_cmd+=(--project-name "$COMPOSE_PROJECT_NAME")
  fi

  if [ -f docker-compose.yml ]; then
    wait_for_compose_health "${compose_cmd[@]}"
  fi

  local deadline=$((SECONDS + HEALTH_TIMEOUT_SECONDS))
  local streamlit_ok=0
  local webhook_ok=0

  log "Probing application endpoints..."

  while ((SECONDS < deadline)); do
    streamlit_ok=0
    webhook_ok=0

    if check_endpoint "Streamlit" "$STREAMLIT_HEALTH_URL"; then
      streamlit_ok=1
    fi

    if check_endpoint "Webhook API" "$WEBHOOK_HEALTH_URL"; then
      webhook_ok=1
    fi

    if [ "$streamlit_ok" -eq 1 ] && [ "$webhook_ok" -eq 1 ]; then
      log "All health checks passed."
      exit 0
    fi

    sleep "$HEALTH_INTERVAL_SECONDS"
  done

  log "ERROR: Health checks failed after ${HEALTH_TIMEOUT_SECONDS}s."
  log "Streamlit: ${STREAMLIT_HEALTH_URL}"
  log "Webhook:   ${WEBHOOK_HEALTH_URL}"
  exit 1
}

main "$@"
