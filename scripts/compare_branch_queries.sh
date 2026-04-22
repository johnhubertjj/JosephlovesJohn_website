#!/usr/bin/env bash

set -euo pipefail

OLD_BRANCH="${OLD_BRANCH:-feature/render_deploy}"
NEW_BRANCH="${NEW_BRANCH:-feature/scaling}"
MODE="${MODE:-baseline}"
ENDPOINTS="${ENDPOINTS:-/,/music/,/art/}"
REQUESTS_PER_ENDPOINT="${REQUESTS_PER_ENDPOINT:-2}"
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
Compare branch query counts for feature/render_deploy vs feature/scaling.

Usage:
  scripts/compare_branch_queries.sh

Environment overrides:
  OLD_BRANCH, NEW_BRANCH             Branch names to compare.
  MODE                               baseline | scaling  (default: baseline)
  ENDPOINTS                          Comma-separated endpoints (default: /,/music/,/art/)
  REQUESTS_PER_ENDPOINT              Repeated requests per endpoint after cache clear (default: 2)
  OLD_WORKTREE, NEW_WORKTREE         Worktree directories to use/create.
  PYTHON_BIN                         Python interpreter to use (default: repo .venv/bin/python)
  SHARED_DB_PATH                     Shared sqlite DB used by both branches.
  SHARED_DATABASE_URL                Shared DATABASE_URL used by both branches (overrides SHARED_DB_PATH).
  OLD_REDIS_URL, NEW_REDIS_URL       Required in MODE=scaling; use different Redis DBs.

Notes:
  - This script uses Django's test client and CaptureQueriesContext.
  - Each endpoint starts from cache.clear() so the first request is "cold" and the
    next request(s) show whether repeated requests reduce query counts.
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

collect_queries() {
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
        "REQUESTS_PER_ENDPOINT=$REQUESTS_PER_ENDPOINT"
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
            "REQUESTS_PER_ENDPOINT=$REQUESTS_PER_ENDPOINT"
            "RESULTS_FILE=$results_file"
        )
    fi

    (
        cd "$dir"
        env "${env_cmd[@]}" "$PYTHON_BIN" - <<'PY'
import json
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "josephlovesjohn_site.settings")

import django

django.setup()

from django.core.cache import cache
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext

label = os.environ["LABEL"]
mode = os.environ["MODE"]
endpoints = [item.strip() for item in os.environ["ENDPOINTS"].split(",") if item.strip()]
requests_per_endpoint = int(os.environ["REQUESTS_PER_ENDPOINT"])
results_file = os.environ["RESULTS_FILE"]

summary = {
    "label": label,
    "mode": mode,
    "requests_per_endpoint": requests_per_endpoint,
    "endpoints": {},
}

for endpoint in endpoints:
    cache.clear()
    client = Client()
    request_counts = []
    statuses = []

    for _ in range(requests_per_endpoint):
        with CaptureQueriesContext(connection) as ctx:
            response = client.get(endpoint, HTTP_HOST="127.0.0.1")
            render = getattr(response, "render", None)
            if callable(render):
                render()
        request_counts.append(len(ctx.captured_queries))
        statuses.append(response.status_code)

    summary["endpoints"][endpoint] = {
        "query_counts": request_counts,
        "statuses": statuses,
        "delta_after_first": request_counts[-1] - request_counts[0] if len(request_counts) > 1 else 0,
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
    print(f"  {old['label']}: queries {o['query_counts']} statuses {o['statuses']} delta_after_first {o['delta_after_first']}")
    print(f"  {new['label']}: queries {n['query_counts']} statuses {n['statuses']} delta_after_first {n['delta_after_first']}")
    print()
PY
}

OLD_WORKTREE="$(ensure_worktree "$OLD_BRANCH" "$OLD_WORKTREE")"
NEW_WORKTREE="$(ensure_worktree "$NEW_BRANCH" "$NEW_WORKTREE")"

OLD_RESULTS="$(mktemp -t jlj-old-queries.XXXXXX.json)"
NEW_RESULTS="$(mktemp -t jlj-new-queries.XXXXXX.json)"

echo "Collecting query counts for $OLD_BRANCH ..."
collect_queries "$OLD_WORKTREE" "$OLD_BRANCH" "$OLD_REDIS_URL" "$OLD_RESULTS"

echo "Collecting query counts for $NEW_BRANCH ..."
collect_queries "$NEW_WORKTREE" "$NEW_BRANCH" "$NEW_REDIS_URL" "$NEW_RESULTS"

echo
print_summary "$OLD_RESULTS" "$NEW_RESULTS"
echo "Detailed results:"
echo "  $OLD_RESULTS"
echo "  $NEW_RESULTS"
