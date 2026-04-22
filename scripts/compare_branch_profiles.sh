#!/usr/bin/env bash

set -euo pipefail

OLD_BRANCH="${OLD_BRANCH:-feature/render_deploy}"
NEW_BRANCH="${NEW_BRANCH:-feature/scaling}"
MODE="${MODE:-baseline}"
ENDPOINTS="${ENDPOINTS:-/,/music/,/art/}"
PROFILE_WARMUP_REQUESTS="${PROFILE_WARMUP_REQUESTS:-1}"
TOP_N="${TOP_N:-12}"
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
Compare branch Python profile hotspots for feature/render_deploy vs feature/scaling.

Usage:
  scripts/compare_branch_profiles.sh

Environment overrides:
  OLD_BRANCH, NEW_BRANCH             Branch names to compare.
  MODE                               baseline | scaling  (default: baseline)
  ENDPOINTS                          Comma-separated endpoints (default: /,/music/,/art/)
  PROFILE_WARMUP_REQUESTS            Warmup requests before profiling (default: 1)
  TOP_N                              Number of top files/functions to keep (default: 12)
  OLD_WORKTREE, NEW_WORKTREE         Worktree directories to use/create.
  PYTHON_BIN                         Python interpreter to use (default: repo .venv/bin/python)
  SHARED_DB_PATH                     Shared sqlite DB used by both branches.
  SHARED_DATABASE_URL                Shared DATABASE_URL used by both branches (overrides SHARED_DB_PATH).
  OLD_REDIS_URL, NEW_REDIS_URL       Required in MODE=scaling; use different Redis DBs.

Notes:
  - Profiles Python-side request handling only; browser rendering costs are out of scope.
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

collect_profiles() {
    local dir="$1"
    local label="$2"
    local redis_url="$3"
    local results_file="$4"
    local database_url="${SHARED_DATABASE_URL:-sqlite:///$SHARED_DB_PATH}"

    local -a env_cmd=(
        "DATABASE_URL=$database_url"
        "DEBUG=true"
        "LOG_SQL_QUERIES=false"
        "SITE_CONTENT_CACHE_TTL=0"
        "CART_SUMMARY_CACHE_TTL=0"
        "LABEL=$label"
        "MODE=$MODE"
        "ENDPOINTS=$ENDPOINTS"
        "PROFILE_WARMUP_REQUESTS=$PROFILE_WARMUP_REQUESTS"
        "TOP_N=$TOP_N"
        "RESULTS_FILE=$results_file"
    )

    if [[ "$MODE" == "scaling" ]]; then
        env_cmd=(
            "DATABASE_URL=$database_url"
            "DEBUG=true"
            "LOG_SQL_QUERIES=false"
            "SITE_CONTENT_CACHE_TTL=300"
            "CART_SUMMARY_CACHE_TTL=60"
            "REDIS_URL=$redis_url"
            "LABEL=$label"
            "MODE=$MODE"
            "ENDPOINTS=$ENDPOINTS"
            "PROFILE_WARMUP_REQUESTS=$PROFILE_WARMUP_REQUESTS"
            "TOP_N=$TOP_N"
            "RESULTS_FILE=$results_file"
        )
    fi

    (
        cd "$dir"
        env "${env_cmd[@]}" "$PYTHON_BIN" - <<'PY'
import cProfile
import json
import os
import pstats
import time
from collections import defaultdict
from pathlib import Path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "josephlovesjohn_site.settings")

import django

django.setup()

from django.core.cache import cache
from django.test import Client

label = os.environ["LABEL"]
mode = os.environ["MODE"]
endpoints = [item.strip() for item in os.environ["ENDPOINTS"].split(",") if item.strip()]
warmups = int(os.environ["PROFILE_WARMUP_REQUESTS"])
top_n = int(os.environ["TOP_N"])
results_file = os.environ["RESULTS_FILE"]
repo_root = Path.cwd().resolve()
module_prefixes = (
    str(repo_root / "josephlovesjohn_site"),
    str(repo_root / "main_site"),
    str(repo_root / "shop"),
    str(repo_root / "mastering"),
)

summary = {
    "label": label,
    "mode": mode,
    "profile_warmup_requests": warmups,
    "endpoints": {},
}


def _matches_repo_file(filename: str) -> bool:
    return filename.startswith(module_prefixes)


def _relpath(filename: str) -> str:
    return os.path.relpath(filename, repo_root)


for endpoint in endpoints:
    cache.clear()
    client = Client()

    for _ in range(warmups):
        response = client.get(endpoint, HTTP_HOST="127.0.0.1")
        render = getattr(response, "render", None)
        if callable(render):
            render()

    profiler = cProfile.Profile()

    def _request() -> int:
        response = client.get(endpoint, HTTP_HOST="127.0.0.1")
        render = getattr(response, "render", None)
        if callable(render):
            render()
        return response.status_code

    start = time.perf_counter()
    status = profiler.runcall(_request)
    elapsed_ms = (time.perf_counter() - start) * 1000

    stats = pstats.Stats(profiler)
    file_totals = defaultdict(lambda: {"cumtime": 0.0, "tottime": 0.0})
    function_rows = []

    for (filename, line_no, func_name), stat in stats.stats.items():
        if not _matches_repo_file(filename):
            continue
        _, ncalls, tottime, cumtime, _ = stat
        relative = _relpath(filename)
        file_totals[relative]["cumtime"] += cumtime
        file_totals[relative]["tottime"] += tottime
        function_rows.append(
            {
                "file": relative,
                "line": line_no,
                "function": func_name,
                "ncalls": ncalls,
                "cumtime_ms": round(cumtime * 1000, 3),
                "tottime_ms": round(tottime * 1000, 3),
            }
        )

    top_files = sorted(
        (
            {
                "file": file,
                "cumtime_ms": round(values["cumtime"] * 1000, 3),
                "tottime_ms": round(values["tottime"] * 1000, 3),
            }
            for file, values in file_totals.items()
        ),
        key=lambda row: row["cumtime_ms"],
        reverse=True,
    )[:top_n]

    top_functions = sorted(function_rows, key=lambda row: row["cumtime_ms"], reverse=True)[: top_n * 2]

    summary["endpoints"][endpoint] = {
        "status": status,
        "elapsed_ms": round(elapsed_ms, 3),
        "top_files": top_files,
        "top_functions": top_functions,
    }

with open(results_file, "w", encoding="utf-8") as fh:
    json.dump(summary, fh, indent=2)
PY
    )
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

print(f"Mode: {old.get('mode', '')}")
print()
for endpoint in old["endpoints"]:
    o = old["endpoints"][endpoint]
    n = new["endpoints"][endpoint]
    print(endpoint)
    print(f"  {old['label']}: elapsed {o['elapsed_ms']}ms, status {o['status']}, top file {o['top_files'][0]['file'] if o['top_files'] else 'n/a'}")
    print(f"  {new['label']}: elapsed {n['elapsed_ms']}ms, status {n['status']}, top file {n['top_files'][0]['file'] if n['top_files'] else 'n/a'}")
    print()
PY
}

OLD_WORKTREE="$(ensure_worktree "$OLD_BRANCH" "$OLD_WORKTREE")"
NEW_WORKTREE="$(ensure_worktree "$NEW_BRANCH" "$NEW_WORKTREE")"

OLD_RESULTS="$(mktemp -t jlj-old-profiles.XXXXXX.json)"
NEW_RESULTS="$(mktemp -t jlj-new-profiles.XXXXXX.json)"

echo "Collecting profile hotspots for $OLD_BRANCH ..."
collect_profiles "$OLD_WORKTREE" "$OLD_BRANCH" "$OLD_REDIS_URL" "$OLD_RESULTS"

echo "Collecting profile hotspots for $NEW_BRANCH ..."
collect_profiles "$NEW_WORKTREE" "$NEW_BRANCH" "$NEW_REDIS_URL" "$NEW_RESULTS"

echo
print_summary "$OLD_RESULTS" "$NEW_RESULTS"
echo "Detailed results:"
echo "  $OLD_RESULTS"
echo "  $NEW_RESULTS"
