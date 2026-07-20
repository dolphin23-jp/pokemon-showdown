#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_DIR="$ROOT_DIR/.runtime"
SHOWDOWN_PID_FILE="$RUNTIME_DIR/showdown.pid"
BOT_PID_FILE="$RUNTIME_DIR/foul-play.pid"
LAUNCHER_PID_FILE="$RUNTIME_DIR/launcher.pid"
SHOWDOWN_LOG="$RUNTIME_DIR/showdown.log"
BOT_LOG="$RUNTIME_DIR/foul-play.log"
LAUNCHER_LOG="$RUNTIME_DIR/launcher.log"
MODE_FILE="$RUNTIME_DIR/battle-format"
BSS_TEAM_DIR="$RUNTIME_DIR/bss-teams/gen9bssregi-curated"
BSS_METADATA="$ROOT_DIR/config/bss-team-sources.tsv"
ALL_GENERATIONS_TEAM_DIR="$RUNTIME_DIR/bss-teams/gen9nationaldexallgenerationsbss"
ALL_GENERATIONS_METADATA="$RUNTIME_DIR/bss-teams/gen9nationaldexallgenerationsbss.tsv"
SHOWDOWN_PORT="${SHOWDOWN_PORT:-8000}"
LAUNCHER_PORT="${LAUNCHER_PORT:-3000}"
ALL_GENERATIONS_FORMAT="gen9nationaldexallgenerationsbss"

mkdir -p "$RUNTIME_DIR"

pid_is_running() {
    local pid_file="$1"
    [[ -f "$pid_file" ]] || return 1
    local pid
    pid="$(cat "$pid_file")"
    [[ "$pid" =~ ^[0-9]+$ ]] || return 1
    kill -0 "$pid" 2>/dev/null
}

stop_pid() {
    local pid_file="$1"
    local label="$2"
    if ! pid_is_running "$pid_file"; then
        rm -f "$pid_file"
        return 0
    fi

    local pid
    pid="$(cat "$pid_file")"
    echo "Stopping $label (PID $pid)..."
    kill "$pid" 2>/dev/null || true
    for _ in {1..20}; do
        if ! kill -0 "$pid" 2>/dev/null; then
            rm -f "$pid_file"
            return 0
        fi
        sleep 0.25
    done
    kill -9 "$pid" 2>/dev/null || true
    rm -f "$pid_file"
}

normalized_bot_username() {
    if [[ -n "${FOUL_PLAY_USERNAME:-}" ]]; then
        printf '%s' "$FOUL_PLAY_USERNAME"
        return
    fi

    local seed base digest
    seed="${GITHUB_USER:-${GITHUB_ACTOR:-${RENDER_SERVICE_NAME:-${CODESPACE_NAME:-localserver}}}}"
    base="$(printf '%s' "$seed" | tr -cd '[:alnum:]' | tr '[:upper:]' '[:lower:]' | cut -c1-10)"
    [[ -n "$base" ]] || base="local"
    digest="$(printf '%s' "$seed" | sha256sum | cut -c1-6)"
    printf 'FP%s%s' "$base" "$digest"
}

effective_format() {
    if [[ -n "${FOUL_PLAY_FORMAT:-}" ]]; then
        printf '%s' "$FOUL_PLAY_FORMAT"
        return
    fi
    if [[ -f "$MODE_FILE" ]]; then
        case "$(cat "$MODE_FILE")" in
            "$ALL_GENERATIONS_FORMAT"|gen9bssregi|gen9randombattle)
                cat "$MODE_FILE"
                return
                ;;
        esac
    fi
    printf '%s' "$ALL_GENERATIONS_FORMAT"
}

format_label() {
    case "$1" in
        "$ALL_GENERATIONS_FORMAT") printf 'All Generations BSS' ;;
        gen9bssregi) printf 'BSS Regulation I' ;;
        gen9randombattle) printf 'Gen 9 Random Battle' ;;
        *) printf '%s' "$1" ;;
    esac
}

team_dir_for_format() {
    case "$1" in
        "$ALL_GENERATIONS_FORMAT") printf '%s' "$ALL_GENERATIONS_TEAM_DIR" ;;
        gen9bssregi) printf '%s' "$BSS_TEAM_DIR" ;;
        *) printf '' ;;
    esac
}

metadata_for_format() {
    case "$1" in
        "$ALL_GENERATIONS_FORMAT") printf '%s' "$ALL_GENERATIONS_METADATA" ;;
        gen9bssregi) printf '%s' "$BSS_METADATA" ;;
        *) printf '' ;;
    esac
}

client_url() {
    if [[ -n "${RENDER_EXTERNAL_URL:-}" ]]; then
        printf '%s/client.html' "${RENDER_EXTERNAL_URL%/}"
    elif [[ -n "${CODESPACE_NAME:-}" ]]; then
        printf 'https://%s-%s.app.github.dev/client.html' "$CODESPACE_NAME" "$LAUNCHER_PORT"
    else
        printf 'http://localhost:%s/client.html' "$LAUNCHER_PORT"
    fi
}

keep_showdown_port_private() {
    [[ -n "${CODESPACE_NAME:-}" ]] || return 0
    command -v gh >/dev/null 2>&1 || return 0
    gh codespace ports visibility "$SHOWDOWN_PORT:private" -c "$CODESPACE_NAME" >/dev/null 2>&1 || true
    echo "Codespaces port $SHOWDOWN_PORT is kept private; browser traffic is proxied through port $LAUNCHER_PORT."
}

start_showdown() {
    if pid_is_running "$SHOWDOWN_PID_FILE"; then
        echo "Pokemon Showdown is already running."
        return
    fi

    cd "$ROOT_DIR"
    bash scripts/ensure-codespaces-config.sh

    local -a command
    command=(node pokemon-showdown start --no-security)
    if [[ -d "$ROOT_DIR/dist" ]]; then
        command+=(--skip-build)
    fi

    echo "Starting Pokemon Showdown..."
    nohup "${command[@]}" >"$SHOWDOWN_LOG" 2>&1 &
    echo $! > "$SHOWDOWN_PID_FILE"

    for _ in {1..180}; do
        if curl -fs -o /dev/null "http://127.0.0.1:$SHOWDOWN_PORT/" 2>/dev/null; then
            return 0
        fi
        if ! pid_is_running "$SHOWDOWN_PID_FILE"; then
            echo "Pokemon Showdown exited during startup." >&2
            tail -n 100 "$SHOWDOWN_LOG" >&2 || true
            return 1
        fi
        sleep 1
    done

    echo "Pokemon Showdown did not become ready on port $SHOWDOWN_PORT." >&2
    tail -n 100 "$SHOWDOWN_LOG" >&2 || true
    return 1
}

prepare_teams() {
    local format="$1"
    cd "$ROOT_DIR"
    case "$format" in
        "$ALL_GENERATIONS_FORMAT") bash scripts/sync-all-generations-teams.sh ;;
        gen9bssregi) bash scripts/sync-bss-teams.sh ;;
    esac
}

start_bot() {
    if pid_is_running "$BOT_PID_FILE"; then
        echo "foul-play is already running."
        return
    fi

    if [[ ! -x "$ROOT_DIR/.venv/bin/python" ]]; then
        echo "Python environment is missing. Run: bash scripts/codespaces-setup.sh" >&2
        return 1
    fi

    local bot_username format search_time team_dir
    bot_username="$(normalized_bot_username)"
    format="$(effective_format)"
    search_time="${FOUL_PLAY_SEARCH_TIME_MS:-500}"

    prepare_teams "$format"
    team_dir="$(team_dir_for_format "$format")"

    local -a args
    args=(
        "$ROOT_DIR/.venv/bin/python" run.py
        --websocket-uri "ws://127.0.0.1:$SHOWDOWN_PORT/showdown/websocket"
        --ps-username "$bot_username"
        --bot-mode accept_challenge
        --pokemon-format "$format"
        --search-time-ms "$search_time"
        --search-parallelism "${FOUL_PLAY_SEARCH_PARALLELISM:-1}"
        --search-threads "${FOUL_PLAY_SEARCH_THREADS:-1}"
        --run-count "${FOUL_PLAY_RUN_COUNT:-1000000}"
        --log-level "${FOUL_PLAY_LOG_LEVEL:-INFO}"
    )

    if [[ "$format" == *bss* ]]; then
        if [[ -z "$team_dir" ]]; then
            echo "No team library is configured for BSS format $format." >&2
            return 1
        fi
        args+=(
            --team-name "${FOUL_PLAY_TEAM_NAME:-$team_dir}"
            --team-preview-search-time-ms "${FOUL_PLAY_TEAM_PREVIEW_SEARCH_TIME_MS:-1000}"
            --team-preview-search-parallelism "${FOUL_PLAY_TEAM_PREVIEW_SEARCH_PARALLELISM:-1}"
        )
    elif [[ -n "${FOUL_PLAY_TEAM_NAME:-}" ]]; then
        args+=(--team-name "$FOUL_PLAY_TEAM_NAME")
    fi

    if [[ "$format" == "$ALL_GENERATIONS_FORMAT" ]]; then
        args+=(--smogon-stats-format "${FOUL_PLAY_SMOGON_STATS_FORMAT:-gen9nationaldexubers}")
    elif [[ -n "${FOUL_PLAY_SMOGON_STATS_FORMAT:-}" ]]; then
        args+=(--smogon-stats-format "$FOUL_PLAY_SMOGON_STATS_FORMAT")
    fi

    if [[ -n "${FOUL_PLAY_PASSWORD:-}" ]]; then
        args+=(--ps-password "$FOUL_PLAY_PASSWORD")
    fi

    echo "Starting foul-play as $bot_username in $format..."
    cd "$ROOT_DIR/foul-play"
    nohup "${args[@]}" >"$BOT_LOG" 2>&1 &
    echo $! > "$BOT_PID_FILE"
    sleep 2

    if ! pid_is_running "$BOT_PID_FILE"; then
        echo "foul-play exited during startup." >&2
        tail -n 180 "$BOT_LOG" >&2 || true
        return 1
    fi
}

start_launcher() {
    if pid_is_running "$LAUNCHER_PID_FILE"; then
        echo "Launcher is already running."
        return
    fi

    local bot_username format team_dir metadata
    bot_username="$(normalized_bot_username)"
    format="$(effective_format)"
    team_dir="$(team_dir_for_format "$format")"
    metadata="$(metadata_for_format "$format")"

    echo "Starting launcher and same-origin Showdown client proxy..."
    cd "$ROOT_DIR"
    nohup env \
        "BOT_USERNAME=$bot_username" \
        "BOT_FORMAT=$format" \
        "BOT_FORMAT_LABEL=$(format_label "$format")" \
        "TEAM_LIBRARY_DIR=$team_dir" \
        "TEAM_METADATA=$metadata" \
        "LAUNCHER_PORT=$LAUNCHER_PORT" \
        "SHOWDOWN_PORT=$SHOWDOWN_PORT" \
        node scripts/launcher-server.js >"$LAUNCHER_LOG" 2>&1 &
    echo $! > "$LAUNCHER_PID_FILE"

    for _ in {1..30}; do
        if curl -fs -o /dev/null "http://127.0.0.1:$LAUNCHER_PORT/health" 2>/dev/null; then
            return 0
        fi
        if ! pid_is_running "$LAUNCHER_PID_FILE"; then
            echo "Launcher exited during startup." >&2
            tail -n 100 "$LAUNCHER_LOG" >&2 || true
            return 1
        fi
        sleep 1
    done

    echo "Launcher did not become ready on port $LAUNCHER_PORT." >&2
    tail -n 100 "$LAUNCHER_LOG" >&2 || true
    return 1
}

show_status() {
    local bot_username format team_count team_dir
    bot_username="$(normalized_bot_username)"
    format="$(effective_format)"
    team_dir="$(team_dir_for_format "$format")"
    team_count=0
    if [[ -n "$team_dir" && -d "$team_dir" ]]; then
        team_count="$(find "$team_dir" -maxdepth 1 -type f -name '*.txt' | wc -l | tr -d ' ')"
    fi

    if pid_is_running "$SHOWDOWN_PID_FILE"; then
        echo "Pokemon Showdown: running (PID $(cat "$SHOWDOWN_PID_FILE"))"
    else
        echo "Pokemon Showdown: stopped"
    fi
    if pid_is_running "$BOT_PID_FILE"; then
        echo "foul-play: running (PID $(cat "$BOT_PID_FILE"))"
    else
        echo "foul-play: stopped"
    fi
    if pid_is_running "$LAUNCHER_PID_FILE"; then
        echo "Launcher/proxy: running (PID $(cat "$LAUNCHER_PID_FILE"))"
    else
        echo "Launcher/proxy: stopped"
    fi
    echo "Bot username: $bot_username"
    echo "Format: $format ($(format_label "$format"))"
    if [[ "$format" == *bss* ]]; then
        echo "Team library: $team_count teams (random team each battle)"
    fi
    echo "Client: $(client_url)"
}

start_all() {
    start_showdown
    keep_showdown_port_private
    start_bot
    start_launcher
    echo
    show_status
}

stop_all() {
    stop_pid "$BOT_PID_FILE" "foul-play"
    stop_pid "$LAUNCHER_PID_FILE" "launcher/proxy"
    stop_pid "$SHOWDOWN_PID_FILE" "Pokemon Showdown"
    keep_showdown_port_private
    echo "Stopped. The Showdown server port remains private."
}

set_mode() {
    local requested="${1:-}"
    if [[ -n "${FOUL_PLAY_FORMAT:-}" ]]; then
        echo "FOUL_PLAY_FORMAT is set, so it overrides the saved mode. Remove that environment variable first." >&2
        exit 1
    fi
    case "$requested" in
        all|allgen|chaos|anything|nationaldex|"$ALL_GENERATIONS_FORMAT")
            printf '%s\n' "$ALL_GENERATIONS_FORMAT" > "$MODE_FILE"
            ;;
        bss|regi|gen9bssregi)
            printf 'gen9bssregi\n' > "$MODE_FILE"
            ;;
        random|randombattle|gen9randombattle)
            printf 'gen9randombattle\n' > "$MODE_FILE"
            ;;
        *)
            echo "Usage: bash scripts/showdown-ai.sh mode {all|bss|random}" >&2
            exit 2
            ;;
    esac
    echo "Battle format changed to $(effective_format). Restarting..."
    stop_all
    start_all
}

show_logs() {
    echo "===== Pokemon Showdown ====="
    tail -n 100 "$SHOWDOWN_LOG" 2>/dev/null || echo "No Showdown log yet."
    echo
    echo "===== foul-play ====="
    tail -n 180 "$BOT_LOG" 2>/dev/null || echo "No foul-play log yet."
    echo
    echo "===== launcher/proxy ====="
    tail -n 100 "$LAUNCHER_LOG" 2>/dev/null || echo "No launcher log yet."
}

case "${1:-start}" in
    start) start_all ;;
    stop) stop_all ;;
    restart) stop_all; start_all ;;
    status) show_status ;;
    logs) show_logs ;;
    refresh-teams)
        case "$(effective_format)" in
            "$ALL_GENERATIONS_FORMAT") bash "$ROOT_DIR/scripts/sync-all-generations-teams.sh" --refresh ;;
            gen9bssregi) bash "$ROOT_DIR/scripts/sync-bss-teams.sh" --refresh ;;
            *) echo "The current format does not use a fixed team library." ;;
        esac
        ;;
    mode) set_mode "${2:-}" ;;
    *)
        echo "Usage: bash scripts/showdown-ai.sh {start|stop|restart|status|logs|refresh-teams|mode {all|bss|random}}" >&2
        exit 2
        ;;
esac
