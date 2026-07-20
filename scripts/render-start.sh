#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# Capture Render's public port for the launcher, then remove the generic PORT
# variable so Pokemon Showdown does not mistakenly bind to the same socket.
export LAUNCHER_PORT="${PORT:-10000}"
unset PORT
export SHOWDOWN_PORT="${SHOWDOWN_PORT:-8000}"
export FOUL_PLAY_FORMAT="${FOUL_PLAY_FORMAT:-gen9nationaldexallgenerationsbss}"
export DEFAULT_PLAYER_NAME="${DEFAULT_PLAYER_NAME:-Dolphin23}"

# Fresh Docker images do not contain empty runtime directories. Showdown's REPL
# cleanup expects this path to exist before the server process starts.
mkdir -p .runtime logs/repl

cleanup() {
    if [[ -n "${TAIL_PID:-}" ]]; then
        kill "$TAIL_PID" 2>/dev/null || true
    fi
    bash scripts/showdown-ai.sh stop >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

bash scripts/showdown-ai.sh start

touch .runtime/showdown.log .runtime/foul-play.log .runtime/launcher.log
tail -n 30 -F .runtime/showdown.log .runtime/foul-play.log .runtime/launcher.log &
TAIL_PID=$!

# Keep the Docker container attached to the three application processes. Render
# will restart the service if one of them exits unexpectedly.
while sleep 5; do
    for component in showdown foul-play launcher; do
        pid_file=".runtime/${component}.pid"
        if [[ ! -f "$pid_file" ]] || ! kill -0 "$(cat "$pid_file")" 2>/dev/null; then
            echo "$component stopped unexpectedly; exiting so Render can restart the service." >&2
            exit 1
        fi
    done
done
