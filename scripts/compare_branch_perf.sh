#!/usr/bin/env bash

set -euo pipefail

OLD_BRANCH="${OLD_BRANCH:-feature/render_deploy}"
NEW_BRANCH="${NEW_BRANCH:-feature/scaling}"
OLD_PORT="${OLD_PORT:-8000}"
NEW_PORT="${NEW_PORT:-8001}"
MODE="${MODE:-baseline}"
RUNS="${RUNS:-5}"
ENDPOINTS="${ENDPOINTS:-/,/music/,/art/}"
OLD_REDIS_URL="${OLD_REDIS_URL:-}"
NEW_REDIS_URL="${NEW_REDIS_URL:-}"

REPO_ROOT="$(git rev-parse --show-toplevel)"
PARENT_DIR="$(dirname "$REPO_ROOT")"
CURRENT_BRANCH="$(git -C "$REPO_ROOT" branch --show-current)"
PYTHON_BIN="${PYTHON_BIN:-$REPO_ROOT/.venv/bin/python}"
SHARED_DB_PATH="${SHARED_DB_PATH:-$REPO_ROOT/db.sqlite3}"
SHARED_DATABASE_URL="${SHARED_DATABASE_URL:-}"
OLD_WORKTREE="${OLD_WORKTREE:-$PARENT_DIR/jlj-render-deploy-bench}"
NEW_WORKTREE="${NEW_WORKTREE:-$PARENT_DIR/jlj-scaling-bench}"

usage() {
    cat <<'EOF'
Compare branch performance for feature/render_deploy vs feature/scaling.

Usage:
  scripts/compare_branch_perf.sh

Environment overrides:
  OLD_BRANCH, NEW_BRANCH           Branch names to compare.
  OLD_PORT, NEW_PORT               Local ports for the temporary dev servers.
  MODE                             baseline | scaling  (default: baseline)
  RUNS                             Number of timed requests per endpoint (default: 5)
  ENDPOINTS                        Comma-separated endpoints (default: /,/music/,/art/)
  OLD_WORKTREE, NEW_WORKTREE       Worktree directories to use/create.
  PYTHON_BIN                       Python interpreter to use (default: repo .venv/bin/python)
  SHARED_DB_PATH                   Shared sqlite DB used by both branches.
  SHARED_DATABASE_URL              Shared DATABASE_URL used by both branches (overrides SHARED_DB_PATH).
  OLD_REDIS_URL, NEW_REDIS_URL     Required in MODE=scaling; use different Redis DBs.

Notes:
  - This script benchmarks server/request performance, not animation smoothness.
  - Do not enable LOG_SQL_QUERIES while timing; it distorts the results.
  - In MODE=scaling, use separate Redis DBs for the two branches, e.g.
      OLD_REDIS_URL=redis://127.0.0.1:6379/1
      NEW_REDIS_URL=redis://127.0.0.1:6379/2
EOF
}

if [[ "${1:-}" == "--help" ]]; then
    usage
    exit 0
fi

if [[ ! -x "$PYTHON_BIN" ]]; then
    echo "Python interpreter not found at: $PYTHON_BIN" >&2
    exit 1
fi

if [[ "$MODE" != "baseline" && "$MODE" != "scaling" ]]; then
    echo "MODE must be 'baseline' or 'scaling'." >&2
    exit 1
fi

if [[ "$MODE" == "scaling" ]]; then
    if [[ -z "$OLD_REDIS_URL" || -z "$NEW_REDIS_URL" ]]; then
        echo "MODE=scaling requires both OLD_REDIS_URL and NEW_REDIS_URL." >&2
        echo "Use different Redis DBs so branch caches do not interfere." >&2
        exit 1
    fi
fi

ensure_clean_worktree() {
    local dir="$1"
    if [[ -d "$dir/.git" || -f "$dir/.git" ]]; then
        if [[ -n "$(git -C "$dir" status --short)" ]]; then
            echo "Existing worktree has local changes: $dir" >&2
            exit 1
        fi
    fi
}

ensure_worktree() {
    local branch="$1"
    local dir="$2"

    if [[ "$branch" == "$CURRENT_BRANCH" && "$dir" != "$REPO_ROOT" ]]; then
        echo "$REPO_ROOT"
        return 0
    fi

    if [[ ! -e "$dir" ]]; then
        git -C "$REPO_ROOT" worktree add "$dir" "$branch"
    fi

    ensure_clean_worktree "$dir"

    local current_branch
    current_branch="$(git -C "$dir" branch --show-current)"
    if [[ "$current_branch" != "$branch" ]]; then
        echo "Worktree $dir is on branch '$current_branch', expected '$branch'." >&2
        exit 1
    fi

    echo "$dir"
}

start_server() {
    local dir="$1"
    local port="$2"
    local redis_url="$3"
    local server_log="$4"
    local database_url="${SHARED_DATABASE_URL:-sqlite:///$SHARED_DB_PATH}"

    local -a env_cmd=(
        "DATABASE_URL=$database_url"
        "DEBUG=true"
        "LOG_SQL_QUERIES=false"
        "SITE_CONTENT_CACHE_TTL=0"
        "CART_SUMMARY_CACHE_TTL=0"
    )

    if [[ "$MODE" == "scaling" ]]; then
        env_cmd=(
            "DATABASE_URL=$database_url"
            "DEBUG=true"
            "LOG_SQL_QUERIES=false"
            "SITE_CONTENT_CACHE_TTL=300"
            "CART_SUMMARY_CACHE_TTL=60"
            "REDIS_URL=$redis_url"
        )
    fi

    (
        cd "$dir"
        env "${env_cmd[@]}" "$PYTHON_BIN" manage.py runserver "127.0.0.1:$port" --noreload
    ) >"$server_log" 2>&1 &
    local pid=$!

    for _ in $(seq 1 40); do
        if curl -fsS "http://127.0.0.1:$port/" >/dev/null 2>&1; then
            echo "$pid"
            return 0
        fi
        sleep 0.5
    done

    echo "Server on port $port did not start correctly. Log: $server_log" >&2
    tail -50 "$server_log" >&2 || true
    kill "$pid" >/dev/null 2>&1 || true
    wait "$pid" >/dev/null 2>&1 || true
    exit 1
}

stop_server() {
    local pid="$1"
    kill "$pid" >/dev/null 2>&1 || true
    wait "$pid" >/dev/null 2>&1 || true
}

benchmark_server() {
    local label="$1"
    local port="$2"
    local results_file="$3"

    RESULTS_FILE="$results_file" LABEL="$label" PORT="$port" RUNS="$RUNS" ENDPOINTS="$ENDPOINTS" \
    "$PYTHON_BIN" - <<'PY'
import json
import os
import time
import urllib.request

label = os.environ["LABEL"]
port = int(os.environ["PORT"])
runs = int(os.environ["RUNS"])
endpoints = [item.strip() for item in os.environ["ENDPOINTS"].split(",") if item.strip()]
results_file = os.environ["RESULTS_FILE"]

base = f"http://127.0.0.1:{port}"
summary = {"label": label, "mode": os.environ.get("MODE", ""), "endpoints": {}}

for endpoint in endpoints:
    # Cold request
    start = time.perf_counter()
    with urllib.request.urlopen(base + endpoint) as response:
        response.read()
    cold_ms = (time.perf_counter() - start) * 1000

    runs_ms = []
    for _ in range(runs):
        start = time.perf_counter()
        with urllib.request.urlopen(base + endpoint) as response:
            response.read()
        runs_ms.append((time.perf_counter() - start) * 1000)

    summary["endpoints"][endpoint] = {
        "cold_ms": round(cold_ms, 2),
        "avg_ms": round(sum(runs_ms) / len(runs_ms), 2),
        "min_ms": round(min(runs_ms), 2),
        "max_ms": round(max(runs_ms), 2),
        "runs_ms": [round(value, 2) for value in runs_ms],
    }

with open(results_file, "w", encoding="utf-8") as fh:
    json.dump(summary, fh, indent=2)
PY
}

print_summary() {
    local old_file="$1"
    local new_file="$2"
    OLD_FILE="$old_file" NEW_FILE="$new_file" "$PYTHON_BIN" - <<'PY'
import json
import os

with open(os.environ["OLD_FILE"], encoding="utf-8") as fh:
    old = json.load(fh)
with open(os.environ["NEW_FILE"], encoding="utf-8") as fh:
    new = json.load(fh)

print(f"Mode: {old.get('mode') or os.environ.get('MODE', '')}")
print()
for endpoint in old["endpoints"]:
    o = old["endpoints"][endpoint]
    n = new["endpoints"][endpoint]
    print(endpoint)
    print(f"  {old['label']}: cold {o['cold_ms']}ms, avg {o['avg_ms']}ms, min {o['min_ms']}ms, max {o['max_ms']}ms")
    print(f"  {new['label']}: cold {n['cold_ms']}ms, avg {n['avg_ms']}ms, min {n['min_ms']}ms, max {n['max_ms']}ms")
    delta = round(n["avg_ms"] - o["avg_ms"], 2)
    print(f"  avg delta ({new['label']} - {old['label']}): {delta}ms")
    print()
PY
}

OLD_WORKTREE="$(ensure_worktree "$OLD_BRANCH" "$OLD_WORKTREE")"
NEW_WORKTREE="$(ensure_worktree "$NEW_BRANCH" "$NEW_WORKTREE")"

OLD_LOG="$(mktemp -t jlj-old-server.XXXXXX.log)"
NEW_LOG="$(mktemp -t jlj-new-server.XXXXXX.log)"
OLD_RESULTS="$(mktemp -t jlj-old-results.XXXXXX.json)"
NEW_RESULTS="$(mktemp -t jlj-new-results.XXXXXX.json)"

cleanup() {
    if [[ -n "${OLD_PID:-}" ]]; then
        stop_server "$OLD_PID"
    fi
    if [[ -n "${NEW_PID:-}" ]]; then
        stop_server "$NEW_PID"
    fi
    return 0
}
trap cleanup EXIT

echo "Benchmarking $OLD_BRANCH on port $OLD_PORT ..."
OLD_PID="$(start_server "$OLD_WORKTREE" "$OLD_PORT" "$OLD_REDIS_URL" "$OLD_LOG")"
MODE="$MODE" benchmark_server "$OLD_BRANCH" "$OLD_PORT" "$OLD_RESULTS"
stop_server "$OLD_PID"
unset OLD_PID

echo "Benchmarking $NEW_BRANCH on port $NEW_PORT ..."
NEW_PID="$(start_server "$NEW_WORKTREE" "$NEW_PORT" "$NEW_REDIS_URL" "$NEW_LOG")"
MODE="$MODE" benchmark_server "$NEW_BRANCH" "$NEW_PORT" "$NEW_RESULTS"
stop_server "$NEW_PID"
unset NEW_PID

echo
print_summary "$OLD_RESULTS" "$NEW_RESULTS"
echo "Detailed results:"
echo "  $OLD_RESULTS"
echo "  $NEW_RESULTS"
