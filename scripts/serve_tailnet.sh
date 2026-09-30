#!/usr/bin/env bash
# Build the static web app and serve it to the tailnet over HTTPS (run on the Mac mini).
# Needs: uv, Tailscale logged in, MagicDNS + HTTPS certificates enabled in the admin console.
set -euo pipefail
cd "$(dirname "$0")/.."
PORT="${PORT:-8550}"

uv sync
# publish from the project root so pyproject deps (flet-audio) and src/assets are picked up
uv run flet publish . \
  --distpath "$PWD/dist" \
  --route-url-strategy hash \
  --app-name "Give math a chance" --app-short-name Mathy \
  --app-description "Timed addition game" \
  --pwa-theme-color "#3F51B5" --pwa-background-color "#121212"
uv run python scripts/patch_web.py dist  # Web Audio sound engine (src/assets/sfx.js)

# tailnet HTTPS -> local static server; persists across reboots until `tailscale serve reset`
tailscale serve --bg "$PORT"
tailscale serve status
exec uv run flet serve dist --port "$PORT"
