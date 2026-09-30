#!/usr/bin/env bash
# Build the static web app and serve it to the tailnet over HTTPS (run on the Mac mini).
# Needs: uv, Tailscale logged in, MagicDNS + HTTPS certificates enabled in the admin console.
set -euo pipefail
cd "$(dirname "$0")/.."
PORT="${PORT:-8550}"

uv sync
uv run flet publish src/main.py \
  --distpath "$PWD/dist" --assets src/assets \
  --route-url-strategy hash \
  --app-name fletMath --app-short-name fletMath \
  --app-description "Timed addition game" \
  --pwa-theme-color "#3F51B5" --pwa-background-color "#121212"

# tailnet HTTPS -> local static server; persists across reboots until `tailscale serve reset`
tailscale serve --bg "$PORT"
tailscale serve status
exec uv run flet serve dist --port "$PORT"
