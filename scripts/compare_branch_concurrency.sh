#!/usr/bin/env bash

set -euo pipefail

OLD_BRANCH="${OLD_BRANCH:-feature/render_deploy}"
NEW_BRANCH="${NEW_BRANCH:-feature/scaling}"
OLD_PORT="${OLD_PORT:-8010}"
NEW_PORT="${NEW_PORT:-8011}"
MODE="${MODE:-scaling}"
ENDPOINTS="${ENDPOINTS:-/,/music/,/art/}"
CONCURRENT_REQUESTS="${CONCURRENT_REQUESTS:-200}"
CONCURRENCY="${CONCURRENCY:-20}"
GUNICORN_WORKERS="${GUNICORN_WORKERS:-4}"
WARMUP_REQUESTS="${WARMUP_REQUESTS:-1}"
OLD_REDIS_URL="${OLD_REDIS_URL:-}"
NEW_REDIS_URL="${NEW_REDIS_URL:-}"

REPO_ROOT="$(git rev-parse --show-toplevel)"
PARENT_DIR="$(dirname "$REPO_ROOT")"
CURRENT_BRANCH="$(git -C "$REPO_ROOT" branch --show-current)"
PYTHON_BIN="${PYTHON_BIN:-$REPO_ROOT/.venv/bin/python}"
GUNICORN_BIN="${GUNICORN_BIN:-$REPO_ROOT/.venv/bin/gunicorn}"
SHARED_DB_PATH="${SHARED_DB_PATH:-$REPO_ROOT/db.sqlite3}"
SHARED_DATABASE_URL="${SHARED_DATABASE_URL:-}"
OLD_WORKTREE="${OLD_WORKTREE:-$PARENT_DIR/jlj-render-deploy-bench}"
NEW_WORKTREE="${NEW_WORKTREE:-$PARENT_DIR/jlj-scaling-bench}"

usage() {
    cat <<'EOF'
Compare branch performance under concurrent load using Gunicorn.

Usage:
  scripts/compare_branch_concurrency.sh

Environment overrides:
  OLD_BRANCH, NEW_BRANCH             Branch names to compare.
  OLD_PORT, NEW_PORT                 Local Gunicorn ports (default: 8010 / 8011).
  MODE                               baseline | scaling  (default: scaling)
  ENDPOINTS                          Comma-separated endpoints (default: /,/music/,/art/)
  CONCURRENT_REQUESTS                Total requests per endpoint (default: 200)
  CONCURRENCY                        Concurrent workers in the load generator (default: 20)
  GUNICORN_WORKERS                   Gunicorn workers per branch (default: 4)
  WARMUP_REQUESTS                    Warmup requests per endpoint before timing (default: 1)
  OLD_WORKTREE, NEW_WORKTREE         Worktree directories to use/create.
  PYTHON_BIN                         Python interpreter to use (default: repo .venv/bin/python)
  GUNICORN_BIN                       Gunicorn binary to use (default: repo .venv/bin/gunicorn)
  SHARED_DB_PATH                     Shared sqlite DB used by both branches.
  SHARED_DATABASE_URL                Shared DATABASE_URL used by both branches (overrides SHARED_DB_PATH).
  OLD_REDIS_URL, NEW_REDIS_URL       Required in MODE=scaling; use different Redis DBs.

Notes:
  - Uses Gunicorn, not Django's runserver.
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

if [[ ! -x "$GUNICORN_BIN" ]]; then
    echo "Gunicorn binary not found at: $GUNICORN_BIN" >&2
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
        env "${env_cmd[@]}" "$GUNICORN_BIN" josephlovesjohn_site.wsgi:application --bind "127.0.0.1:$port" --workers "$GUNICORN_WORKERS"
    ) >"$server_log" 2>&1 &
    local pid=$!

    for _ in $(seq 1 40); do
        if curl -fsS "http://127.0.0.1:$port/" >/dev/null 2>&1; then
            echo "$pid"
            return 0
        fi
        sleep 0.5
    done

    echo "Gunicorn on port $port did not start correctly. Log: $server_log" >&2
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

    RESULTS_FILE="$results_file" LABEL="$label" PORT="$port" ENDPOINTS="$ENDPOINTS" \
    CONCURRENT_REQUESTS="$CONCURRENT_REQUESTS" CONCURRENCY="$CONCURRENCY" WARMUP_REQUESTS="$WARMUP_REQUESTS" \
    "$PYTHON_BIN" - <<'PY'
import concurrent.futures
import json
import os
import statistics
import time
import urllib.error
import urllib.request

label = os.environ["LABEL"]
port = int(os.environ["PORT"])
endpoints = [item.strip() for item in os.environ["ENDPOINTS"].split(",") if item.strip()]
total_requests = int(os.environ["CONCURRENT_REQUESTS"])
concurrency = int(os.environ["CONCURRENCY"])
warmup_requests = int(os.environ["WARMUP_REQUESTS"])
results_file = os.environ["RESULTS_FILE"]

base = f"http://127.0.0.1:{port}"
summary = {"label": label, "mode": os.environ.get("MODE", ""), "endpoints": {}}


def request_once(url: str) -> dict[str, float | int | str]:
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            body = response.read()
            elapsed_ms = (time.perf_counter() - start) * 1000
            return {
                "ok": 1,
                "status": response.status,
                "elapsed_ms": elapsed_ms,
                "bytes": len(body),
            }
    except urllib.error.HTTPError as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return {"ok": 0, "status": exc.code, "elapsed_ms": elapsed_ms, "error": f"http {exc.code}"}
    except Exception as exc:  # pragma: no cover - defensive for load tests
        elapsed_ms = (time.perf_counter() - start) * 1000
        return {"ok": 0, "status": 0, "elapsed_ms": elapsed_ms, "error": str(exc)}


for endpoint in endpoints:
    url = base + endpoint

    for _ in range(warmup_requests):
        request_once(url)

    started = time.perf_counter()
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(request_once, url) for _ in range(total_requests)]
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())
    total_elapsed = time.perf_counter() - started

    successes = [item for item in results if item["ok"] == 1]
    failures = [item for item in results if item["ok"] == 0]
    latencies = sorted(item["elapsed_ms"] for item in successes)

    def percentile(p: float) -> float:
        if not latencies:
            return 0.0
        idx = min(len(latencies) - 1, max(0, int(round((len(latencies) - 1) * p))))
        return latencies[idx]

    summary["endpoints"][endpoint] = {
        "total_requests": total_requests,
        "concurrency": concurrency,
        "success_count": len(successes),
        "failure_count": len(failures),
        "requests_per_second": round((len(successes) / total_elapsed) if total_elapsed else 0.0, 3),
        "avg_ms": round(statistics.mean(latencies), 3) if latencies else 0.0,
        "median_ms": round(statistics.median(latencies), 3) if latencies else 0.0,
        "p95_ms": round(percentile(0.95), 3),
        "p99_ms": round(percentile(0.99), 3),
        "min_ms": round(min(latencies), 3) if latencies else 0.0,
        "max_ms": round(max(latencies), 3) if latencies else 0.0,
        "size_request_bytes": int(statistics.mean(item["bytes"] for item in successes)) if successes else 0,
        "errors": [item.get("error", "") for item in failures[:10]],
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
    print(f"  {old['label']}: avg {o['avg_ms']}ms, p95 {o['p95_ms']}ms, req/s {o['requests_per_second']}, ok {o['success_count']}/{o['total_requests']}")
    print(f"  {new['label']}: avg {n['avg_ms']}ms, p95 {n['p95_ms']}ms, req/s {n['requests_per_second']}, ok {n['success_count']}/{n['total_requests']}")
    print(f"  avg delta ({new['label']} - {old['label']}): {round(n['avg_ms'] - o['avg_ms'], 3)}ms")
    print()
PY
}

OLD_WORKTREE="$(ensure_worktree "$OLD_BRANCH" "$OLD_WORKTREE")"
NEW_WORKTREE="$(ensure_worktree "$NEW_BRANCH" "$NEW_WORKTREE")"

OLD_LOG="$(mktemp -t jlj-old-gunicorn.XXXXXX.log)"
NEW_LOG="$(mktemp -t jlj-new-gunicorn.XXXXXX.log)"
OLD_RESULTS="$(mktemp -t jlj-old-concurrency.XXXXXX.json)"
NEW_RESULTS="$(mktemp -t jlj-new-concurrency.XXXXXX.json)"

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

echo "Benchmarking $OLD_BRANCH under concurrency on port $OLD_PORT ..."
OLD_PID="$(start_server "$OLD_WORKTREE" "$OLD_PORT" "$OLD_REDIS_URL" "$OLD_LOG")"
MODE="$MODE" benchmark_server "$OLD_BRANCH" "$OLD_PORT" "$OLD_RESULTS"
stop_server "$OLD_PID"
unset OLD_PID

echo "Benchmarking $NEW_BRANCH under concurrency on port $NEW_PORT ..."
NEW_PID="$(start_server "$NEW_WORKTREE" "$NEW_PORT" "$NEW_REDIS_URL" "$NEW_LOG")"
MODE="$MODE" benchmark_server "$NEW_BRANCH" "$NEW_PORT" "$NEW_RESULTS"
stop_server "$NEW_PID"
unset NEW_PID

echo
print_summary "$OLD_RESULTS" "$NEW_RESULTS"
echo "Detailed results:"
echo "  $OLD_RESULTS"
echo "  $NEW_RESULTS"
