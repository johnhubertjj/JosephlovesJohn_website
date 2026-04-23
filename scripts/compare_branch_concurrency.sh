#!/usr/bin/env bash

set -euo pipefail

OLD_REF="${OLD_REF:-${OLD_BRANCH:-feature/render_deploy}}"
NEW_REF="${NEW_REF:-${NEW_BRANCH:-feature/scaling}}"
OLD_LABEL="${OLD_LABEL:-$OLD_REF}"
NEW_LABEL="${NEW_LABEL:-$NEW_REF}"
OLD_PORT="${OLD_PORT:-8010}"
NEW_PORT="${NEW_PORT:-8011}"
MODE="${MODE:-scaling}"
CACHE_STATE="${CACHE_STATE:-fresh}"
ENDPOINTS="${ENDPOINTS:-/,/music/,/art/}"
CONCURRENT_REQUESTS="${CONCURRENT_REQUESTS:-200}"
CONCURRENCY="${CONCURRENCY:-20}"
GUNICORN_WORKERS="${GUNICORN_WORKERS:-4}"
WARMUP_REQUESTS="${WARMUP_REQUESTS:-1}"
CONCURRENCY_RUNS="${CONCURRENCY_RUNS:-5}"
STEADY_STATE_WARMUP_ROUNDS="${STEADY_STATE_WARMUP_ROUNDS:-5}"
OLD_REDIS_URL="${OLD_REDIS_URL:-}"
NEW_REDIS_URL="${NEW_REDIS_URL:-}"

REPO_ROOT="$(git rev-parse --show-toplevel)"
PARENT_DIR="$(dirname "$REPO_ROOT")"
CURRENT_HEAD="$(git -C "$REPO_ROOT" rev-parse HEAD)"
PYTHON_BIN="${PYTHON_BIN:-$REPO_ROOT/.venv/bin/python}"
GUNICORN_BIN="${GUNICORN_BIN:-$REPO_ROOT/.venv/bin/gunicorn}"
SHARED_DB_PATH="${SHARED_DB_PATH:-$REPO_ROOT/db.sqlite3}"
SHARED_DATABASE_URL="${SHARED_DATABASE_URL:-}"
OLD_WORKTREE="${OLD_WORKTREE:-$PARENT_DIR/jlj-render-deploy-bench}"
NEW_WORKTREE="${NEW_WORKTREE:-$PARENT_DIR/jlj-scaling-bench}"
ENV_BIN="${ENV_BIN:-/usr/bin/env}"
TEMP_SETTINGS_DIR=""
TEMP_SETTINGS_MODULE="jlj_bench_settings"
OLD_STATIC_ROOT=""
NEW_STATIC_ROOT=""

usage() {
    cat <<'EOF'
Compare concurrent Gunicorn performance for any two git refs.

Usage:
  scripts/compare_branch_concurrency.sh

Environment overrides:
  OLD_REF, NEW_REF                   Git refs to compare (branch, tag, or commit SHA).
  OLD_LABEL, NEW_LABEL               Optional human-friendly labels for the report output.
  OLD_PORT, NEW_PORT                 Local Gunicorn ports (default: 8010 / 8011).
  MODE                               baseline | scaling  (default: scaling)
  CACHE_STATE                        fresh | warm (default: fresh)
  ENDPOINTS                          Comma-separated endpoints (default: /,/music/,/art/)
  CONCURRENT_REQUESTS                Total requests per endpoint (default: 200)
  CONCURRENCY                        Concurrent workers in the load generator (default: 20)
  GUNICORN_WORKERS                   Gunicorn workers per branch (default: 4)
  WARMUP_REQUESTS                    Warmup requests per endpoint before timing (default: 1)
  CONCURRENCY_RUNS                   Number of repeated concurrency runs to aggregate (default: 5)
  STEADY_STATE_WARMUP_ROUNDS         Full endpoint warmup cycles before timing in CACHE_STATE=warm.
  OLD_WORKTREE, NEW_WORKTREE         Worktree directories to use/create.
  PYTHON_BIN                         Python interpreter to use (default: repo .venv/bin/python)
  GUNICORN_BIN                       Gunicorn binary to use (default: repo .venv/bin/gunicorn)
  SHARED_DB_PATH                     Shared sqlite DB used by both branches.
  SHARED_DATABASE_URL                Shared DATABASE_URL used by both branches (overrides SHARED_DB_PATH).
  OLD_REDIS_URL, NEW_REDIS_URL       Required in MODE=scaling; use different Redis DBs.

Notes:
  - Uses Gunicorn, not Django's runserver.
  - Runs Gunicorn in a production-style DEBUG=false setup with manifest-collected static files.
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

if [[ "$CACHE_STATE" != "fresh" && "$CACHE_STATE" != "warm" ]]; then
    echo "CACHE_STATE must be 'fresh' or 'warm'." >&2
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

resolve_ref() {
    local ref="$1"
    git -C "$REPO_ROOT" rev-parse "${ref}^{commit}"
}

ensure_worktree() {
    local ref="$1"
    local dir="$2"
    local resolved_ref
    resolved_ref="$(resolve_ref "$ref")"

    if [[ "$resolved_ref" == "$CURRENT_HEAD" && "$dir" != "$REPO_ROOT" ]]; then
        echo "$REPO_ROOT"
        return 0
    fi

    if [[ ! -e "$dir" ]]; then
        git -C "$REPO_ROOT" worktree add --detach "$dir" "$resolved_ref"
    fi

    ensure_clean_worktree "$dir"

    local current_head
    current_head="$(git -C "$dir" rev-parse HEAD)"
    if [[ "$current_head" != "$resolved_ref" ]]; then
        echo "Worktree $dir is on commit '$current_head', expected ref '$ref' ($resolved_ref)." >&2
        exit 1
    fi

    echo "$dir"
}

start_server() {
    local dir="$1"
    local port="$2"
    local redis_url="$3"
    local server_log="$4"
    local static_root="$5"
    local database_url="${SHARED_DATABASE_URL:-sqlite:///$SHARED_DB_PATH}"

    local -a env_cmd=(
        "DATABASE_URL=$database_url"
        "DEBUG=false"
        "LOG_SQL_QUERIES=false"
        "PYTHONPATH=$TEMP_SETTINGS_DIR:$dir"
        "DJANGO_SETTINGS_MODULE=$TEMP_SETTINGS_MODULE"
        "STATIC_ROOT=$static_root"
        "SITE_URL=http://127.0.0.1:$port"
        "SECRET_KEY=bench-secret"
        "SITE_CONTENT_CACHE_TTL=0"
        "CART_SUMMARY_CACHE_TTL=0"
    )

    if [[ "$MODE" == "scaling" ]]; then
        env_cmd=(
            "DATABASE_URL=$database_url"
            "DEBUG=false"
            "LOG_SQL_QUERIES=false"
            "PYTHONPATH=$TEMP_SETTINGS_DIR:$dir"
            "DJANGO_SETTINGS_MODULE=$TEMP_SETTINGS_MODULE"
            "STATIC_ROOT=$static_root"
            "SITE_URL=http://127.0.0.1:$port"
            "SECRET_KEY=bench-secret"
            "SITE_CONTENT_CACHE_TTL=300"
            "CART_SUMMARY_CACHE_TTL=60"
            "REDIS_URL=$redis_url"
        )
    fi

    (
        cd "$dir"
        exec env "${env_cmd[@]}" "$PYTHON_BIN" -c 'import os, sys; os.setsid(); os.execvpe(sys.argv[1], sys.argv[1:], os.environ)' \
            "$GUNICORN_BIN" josephlovesjohn_site.wsgi:application --bind "127.0.0.1:$port" --workers "$GUNICORN_WORKERS"
    ) >"$server_log" 2>&1 &
    local pid=$!

    for _ in $(seq 1 40); do
        if ! kill -0 "$pid" >/dev/null 2>&1; then
            break
        fi
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
    kill -TERM -- "-$pid" >/dev/null 2>&1 || kill "$pid" >/dev/null 2>&1 || true
    wait "$pid" >/dev/null 2>&1 || true
    kill -KILL -- "-$pid" >/dev/null 2>&1 || true
}

flush_redis_db() {
    local redis_url="$1"
    if [[ -n "$redis_url" ]]; then
        if command -v redis-cli >/dev/null 2>&1; then
            redis-cli -u "$redis_url" FLUSHDB >/dev/null
        else
            "$PYTHON_BIN" -c 'import sys, redis; redis.Redis.from_url(sys.argv[1]).flushdb()' "$redis_url"
        fi
    fi
}

benchmark_server() {
    local label="$1"
    local port="$2"
    local results_file="$3"

    RESULTS_FILE="$results_file" LABEL="$label" PORT="$port" ENDPOINTS="$ENDPOINTS" \
    CONCURRENT_REQUESTS="$CONCURRENT_REQUESTS" CONCURRENCY="$CONCURRENCY" WARMUP_REQUESTS="$WARMUP_REQUESTS" \
    CACHE_STATE="$CACHE_STATE" STEADY_STATE_WARMUP_ROUNDS="$STEADY_STATE_WARMUP_ROUNDS" RUNTIME_MODE="production" \
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
cache_state = os.environ.get("CACHE_STATE", "fresh")
steady_state_warmup_rounds = int(os.environ.get("STEADY_STATE_WARMUP_ROUNDS", "0"))
results_file = os.environ["RESULTS_FILE"]

base = f"http://127.0.0.1:{port}"
summary = {
    "label": label,
    "mode": os.environ.get("MODE", ""),
    "cache_state": cache_state,
    "steady_state_warmup_rounds": steady_state_warmup_rounds,
    "runtime_mode": os.environ.get("RUNTIME_MODE", ""),
    "endpoints": {},
}


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

run_count = old.get("run_count", 1)
cache_state = old.get("cache_state", "fresh")
warmup_rounds = old.get("steady_state_warmup_rounds", 0)
runtime_mode = old.get("runtime_mode", "")
state_note = f"{cache_state} cache"
if cache_state == "warm":
    state_note += f", {warmup_rounds} full warmup cycle(s)"
if runtime_mode:
    state_note += f", {runtime_mode}"
print(f"Mode: {old.get('mode') or os.environ.get('MODE', '')} ({state_note}, medians across {run_count} run(s))")
print()
for endpoint in old["endpoints"]:
    o = old["endpoints"][endpoint]
    n = new["endpoints"][endpoint]
    old_avg_range = (min(run["avg_ms"] for run in o.get("runs", []) or [o]), max(run["avg_ms"] for run in o.get("runs", []) or [o]))
    new_avg_range = (min(run["avg_ms"] for run in n.get("runs", []) or [n]), max(run["avg_ms"] for run in n.get("runs", []) or [n]))
    print(endpoint)
    print(f"  {old['label']}: avg {o['avg_ms']}ms, p95 {o['p95_ms']}ms, req/s {o['requests_per_second']}, ok {o['success_count']}/{o['total_requests']}")
    print(f"    avg range: {round(old_avg_range[0], 3)}ms .. {round(old_avg_range[1], 3)}ms")
    print(f"  {new['label']}: avg {n['avg_ms']}ms, p95 {n['p95_ms']}ms, req/s {n['requests_per_second']}, ok {n['success_count']}/{n['total_requests']}")
    print(f"    avg range: {round(new_avg_range[0], 3)}ms .. {round(new_avg_range[1], 3)}ms")
    print(f"  avg delta ({new['label']} - {old['label']}): {round(n['avg_ms'] - o['avg_ms'], 3)}ms")
    print()
PY
}

aggregate_results() {
    local label="$1"
    local results_file="$2"
    shift 2

    if [[ "$#" -eq 0 ]]; then
        echo "aggregate_results requires at least one run file." >&2
        exit 1
    fi

    local joined_files
    joined_files="$(printf '%s:' "$@")"
    joined_files="${joined_files%:}"

    LABEL="$label" MODE="$MODE" RUN_FILES="$joined_files" RESULTS_FILE="$results_file" "$PYTHON_BIN" - <<'PY'
import json
import os
import statistics

run_files = [item for item in os.environ["RUN_FILES"].split(":") if item]
runs = []
for path in run_files:
    with open(path, encoding="utf-8") as fh:
        runs.append(json.load(fh))

label = os.environ["LABEL"]
mode = os.environ["MODE"]
endpoints = list(runs[0]["endpoints"].keys()) if runs else []
summary = {
    "label": label,
    "mode": mode,
    "cache_state": runs[0].get("cache_state", "fresh"),
    "steady_state_warmup_rounds": runs[0].get("steady_state_warmup_rounds", 0),
    "runtime_mode": runs[0].get("runtime_mode", ""),
    "run_count": len(runs),
    "endpoints": {},
}

for endpoint in endpoints:
    endpoint_runs = [run["endpoints"][endpoint] for run in runs]
    avg_values = [row["avg_ms"] for row in endpoint_runs]
    p95_values = [row["p95_ms"] for row in endpoint_runs]
    p99_values = [row["p99_ms"] for row in endpoint_runs]
    median_values = [row["median_ms"] for row in endpoint_runs]
    rps_values = [row["requests_per_second"] for row in endpoint_runs]
    min_values = [row["min_ms"] for row in endpoint_runs]
    max_values = [row["max_ms"] for row in endpoint_runs]
    success_values = [row["success_count"] for row in endpoint_runs]
    failure_values = [row["failure_count"] for row in endpoint_runs]
    size_values = [row["size_request_bytes"] for row in endpoint_runs]
    total_requests = endpoint_runs[0]["total_requests"]
    concurrency = endpoint_runs[0]["concurrency"]

    errors = []
    for row in endpoint_runs:
        for error in row.get("errors", []):
            if error and error not in errors:
                errors.append(error)

    summary["endpoints"][endpoint] = {
        "total_requests": total_requests,
        "concurrency": concurrency,
        "success_count": min(success_values),
        "failure_count": max(failure_values),
        "requests_per_second": round(statistics.median(rps_values), 3),
        "avg_ms": round(statistics.median(avg_values), 3),
        "median_ms": round(statistics.median(median_values), 3),
        "p95_ms": round(statistics.median(p95_values), 3),
        "p99_ms": round(statistics.median(p99_values), 3),
        "min_ms": round(min(min_values), 3),
        "max_ms": round(max(max_values), 3),
        "size_request_bytes": int(round(statistics.median(size_values))),
        "errors": errors[:10],
        "runs": endpoint_runs,
    }

with open(os.environ["RESULTS_FILE"], "w", encoding="utf-8") as fh:
    json.dump(summary, fh, indent=2)
PY
}

run_branch_round() {
    local run_index="$1"
    local label="$2"
    local ref="$3"
    local worktree="$4"
    local port="$5"
    local redis_url="$6"
    local results_file="$7"
    local static_root="$8"
    local server_log
    server_log="$(mktemp -t jlj-gunicorn.run${run_index}.XXXXXX.log)"

    if [[ "$MODE" == "scaling" ]]; then
        flush_redis_db "$redis_url"
    fi

    echo "Run $run_index/$CONCURRENCY_RUNS: benchmarking $label ($ref) under concurrency on port $port ..."
    local pid
    pid="$(start_server "$worktree" "$port" "$redis_url" "$server_log" "$static_root")"
    if [[ "$CACHE_STATE" == "warm" ]]; then
        prewarm_server "$label" "$port"
    fi
    MODE="$MODE" benchmark_server "$label" "$port" "$results_file"
    stop_server "$pid"
}

prewarm_server() {
    local label="$1"
    local port="$2"
    local endpoint

    echo "  prewarming $label on port $port with $STEADY_STATE_WARMUP_ROUNDS full endpoint cycle(s) ..."
    IFS=',' read -r -a endpoints_array <<< "$ENDPOINTS"
    for _ in $(seq 1 "$STEADY_STATE_WARMUP_ROUNDS"); do
        for endpoint in "${endpoints_array[@]}"; do
            endpoint="${endpoint// /}"
            if [[ -n "$endpoint" ]]; then
                curl -fsS "http://127.0.0.1:$port$endpoint" >/dev/null
            fi
        done
    done
}

write_benchmark_settings() {
    TEMP_SETTINGS_DIR="$(mktemp -d -t jlj-bench-settings.XXXXXX)"
    cat >"$TEMP_SETTINGS_DIR/$TEMP_SETTINGS_MODULE.py" <<'PY'
from josephlovesjohn_site.settings import *  # noqa: F401,F403
import os

DEBUG = False
STATIC_ROOT = os.environ["STATIC_ROOT"]
STATICFILES_STORAGE_BACKEND = "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"
STORAGES = {
    **STORAGES,
    "staticfiles": {"BACKEND": STATICFILES_STORAGE_BACKEND},
}
WHITENOISE_AUTOREFRESH = False
WHITENOISE_USE_FINDERS = False
WHITENOISE_MAX_AGE = 31536000
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0
ALLOWED_HOSTS = sorted(set([*ALLOWED_HOSTS, "127.0.0.1", "localhost", "testserver"]))
SITE_URL = os.environ.get("SITE_URL", SITE_URL)
VERIFY_STATIC_ASSET_FILES = False
PY
}

collect_static() {
    local dir="$1"
    local static_root="$2"
    local database_url="${SHARED_DATABASE_URL:-sqlite:///$SHARED_DB_PATH}"
    (
        cd "$dir"
        "$ENV_BIN" \
            "PYTHONPATH=$TEMP_SETTINGS_DIR:$dir" \
            "DJANGO_SETTINGS_MODULE=$TEMP_SETTINGS_MODULE" \
            "STATIC_ROOT=$static_root" \
            "DATABASE_URL=$database_url" \
            "SITE_URL=http://127.0.0.1" \
            "SECRET_KEY=bench-secret" \
            "$PYTHON_BIN" manage.py collectstatic --noinput --clear >/dev/null
    )
}

OLD_WORKTREE="$(ensure_worktree "$OLD_REF" "$OLD_WORKTREE")"
NEW_WORKTREE="$(ensure_worktree "$NEW_REF" "$NEW_WORKTREE")"
write_benchmark_settings
OLD_STATIC_ROOT="$(mktemp -d -t jlj-old-static.XXXXXX)"
NEW_STATIC_ROOT="$(mktemp -d -t jlj-new-static.XXXXXX)"
echo "Collecting static for $OLD_LABEL ($OLD_REF) ..."
collect_static "$OLD_WORKTREE" "$OLD_STATIC_ROOT"
echo "Collecting static for $NEW_LABEL ($NEW_REF) ..."
collect_static "$NEW_WORKTREE" "$NEW_STATIC_ROOT"

OLD_RESULTS="$(mktemp -t jlj-old-concurrency.XXXXXX.json)"
NEW_RESULTS="$(mktemp -t jlj-new-concurrency.XXXXXX.json)"
declare -a OLD_RUN_RESULTS=()
declare -a NEW_RUN_RESULTS=()

cleanup() {
    if [[ -n "${OLD_PID:-}" ]]; then
        stop_server "$OLD_PID"
    fi
    if [[ -n "${NEW_PID:-}" ]]; then
        stop_server "$NEW_PID"
    fi
    if [[ -n "$OLD_STATIC_ROOT" ]]; then
        rm -rf "$OLD_STATIC_ROOT"
    fi
    if [[ -n "$NEW_STATIC_ROOT" ]]; then
        rm -rf "$NEW_STATIC_ROOT"
    fi
    if [[ -n "$TEMP_SETTINGS_DIR" ]]; then
        rm -rf "$TEMP_SETTINGS_DIR"
    fi
    return 0
}
trap cleanup EXIT

for run_index in $(seq 1 "$CONCURRENCY_RUNS"); do
    old_run_file="$(mktemp -t jlj-old-concurrency.run${run_index}.XXXXXX.json)"
    new_run_file="$(mktemp -t jlj-new-concurrency.run${run_index}.XXXXXX.json)"
    OLD_RUN_RESULTS+=("$old_run_file")
    NEW_RUN_RESULTS+=("$new_run_file")

    if (( run_index % 2 == 1 )); then
        run_branch_round "$run_index" "$OLD_LABEL" "$OLD_REF" "$OLD_WORKTREE" "$OLD_PORT" "$OLD_REDIS_URL" "$old_run_file" "$OLD_STATIC_ROOT"
        run_branch_round "$run_index" "$NEW_LABEL" "$NEW_REF" "$NEW_WORKTREE" "$NEW_PORT" "$NEW_REDIS_URL" "$new_run_file" "$NEW_STATIC_ROOT"
    else
        run_branch_round "$run_index" "$NEW_LABEL" "$NEW_REF" "$NEW_WORKTREE" "$NEW_PORT" "$NEW_REDIS_URL" "$new_run_file" "$NEW_STATIC_ROOT"
        run_branch_round "$run_index" "$OLD_LABEL" "$OLD_REF" "$OLD_WORKTREE" "$OLD_PORT" "$OLD_REDIS_URL" "$old_run_file" "$OLD_STATIC_ROOT"
    fi
done

aggregate_results "$OLD_LABEL" "$OLD_RESULTS" "${OLD_RUN_RESULTS[@]}"
aggregate_results "$NEW_LABEL" "$NEW_RESULTS" "${NEW_RUN_RESULTS[@]}"

echo
print_summary "$OLD_RESULTS" "$NEW_RESULTS"
echo "Detailed results:"
echo "  $OLD_RESULTS"
echo "  $NEW_RESULTS"
