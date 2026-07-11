#!/usr/bin/env bash
# Remove unused Docker images safely without touching running containers.
set -euo pipefail

DRY_RUN="${DRY_RUN:-false}"

log() {
  printf '[cleanup] %s\n' "$*"
}

fail() {
  log "ERROR: $*"
  exit 1
}

require_command() {
  local cmd="$1"
  command -v "$cmd" >/dev/null 2>&1 || fail "required command not found: $cmd"
}

main() {
  require_command docker

  log "Collecting images used by running containers..."
  mapfile -t running_images < <(
    docker ps --format '{{.Image}}' | sort -u
  )

  if [ "${#running_images[@]}" -eq 0 ]; then
    log "No running containers detected."
  else
    log "Protected images (${#running_images[@]}):"
    for image in "${running_images[@]}"; do
      log "  - $image"
    done
  fi

  log "Removing dangling images only (safe; never deletes images in use)..."
  if [ "$DRY_RUN" = "true" ]; then
    docker image prune --force --filter "dangling=true"
    log "Dry run complete."
    exit 0
  fi

  docker image prune --force --filter "dangling=true"

  log "Docker disk usage after cleanup:"
  docker system df

  log "Cleanup complete."
}

main "$@"
