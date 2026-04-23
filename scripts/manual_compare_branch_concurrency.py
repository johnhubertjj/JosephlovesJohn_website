#!/usr/bin/env python3
"""Manual-style Gunicorn concurrency comparison for two refs.

This reproduces the earlier ad hoc benchmarking shape more closely than the
report runner:
- collect static once per ref
- start both Gunicorn servers once
- flush Redis at most once per cache-state suite
- keep servers and caches warm across repeated rounds

It is intentionally useful as a diagnostic harness when comparing "manual"
results with the stricter report runner in compare_branch_concurrency.sh.
"""

from __future__ import annotations

import concurrent.futures
import json
import os
import shutil
import signal
import statistics
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
PARENT_DIR = REPO_ROOT.parent
CURRENT_HEAD = (
    subprocess.check_output(["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"], text=True).strip()
)


def env_str(name: str, default: str) -> str:
    return os.environ.get(name, default)


def env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    return int(value) if value else default


OLD_REF = env_str("OLD_REF", env_str("OLD_BRANCH", "feature/render_deploy"))
NEW_REF = env_str("NEW_REF", env_str("NEW_BRANCH", "feature/scaling"))
OLD_LABEL = env_str("OLD_LABEL", OLD_REF)
NEW_LABEL = env_str("NEW_LABEL", NEW_REF)
OLD_PORT = env_int("OLD_PORT", 8010)
NEW_PORT = env_int("NEW_PORT", 8011)
MODE = env_str("MODE", "scaling")
ENDPOINTS = [item.strip() for item in env_str("ENDPOINTS", "/,/music/,/art/").split(",") if item.strip()]
CONCURRENT_REQUESTS = env_int("CONCURRENT_REQUESTS", 200)
CONCURRENCY = env_int("CONCURRENCY", 20)
GUNICORN_WORKERS = env_int("GUNICORN_WORKERS", 4)
WARMUP_REQUESTS = env_int("WARMUP_REQUESTS", 1)
CONCURRENCY_RUNS = env_int("CONCURRENCY_RUNS", 5)
STEADY_STATE_WARMUP_ROUNDS = env_int("STEADY_STATE_WARMUP_ROUNDS", 5)
PYTHON_BIN = Path(env_str("PYTHON_BIN", str(REPO_ROOT / ".venv/bin/python")))
GUNICORN_BIN = Path(env_str("GUNICORN_BIN", str(REPO_ROOT / ".venv/bin/gunicorn")))
ENV_BIN = env_str("ENV_BIN", "/usr/bin/env")
OLD_WORKTREE = Path(env_str("OLD_WORKTREE", str(PARENT_DIR / "jlj-render-deploy-bench")))
NEW_WORKTREE = Path(env_str("NEW_WORKTREE", str(PARENT_DIR / "jlj-scaling-bench")))
SHARED_DB_PATH = env_str("SHARED_DB_PATH", str(REPO_ROOT / "db.sqlite3"))
SHARED_DATABASE_URL = env_str("SHARED_DATABASE_URL", "")
OLD_REDIS_URL = env_str("OLD_REDIS_URL", "")
NEW_REDIS_URL = env_str("NEW_REDIS_URL", "")
OUTPUT_PATH = Path(env_str("OUTPUT_PATH", str(REPO_ROOT / "perf-report/raw/manual_concurrency.json")))

TEMP_SETTINGS_MODULE = "jlj_bench_settings"


def ensure_executable(path: Path, label: str) -> None:
    if not path.exists() or not os.access(path, os.X_OK):
        raise SystemExit(f"{label} not found or not executable at: {path}")


def ensure_clean_worktree(dir_path: Path) -> None:
    git_marker = dir_path / ".git"
    if git_marker.exists() and subprocess.check_output(
        ["git", "-C", str(dir_path), "status", "--short"], text=True
    ).strip():
        raise SystemExit(f"Existing worktree has local changes: {dir_path}")


def resolve_ref(ref: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(REPO_ROOT), "rev-parse", f"{ref}^{{commit}}"], text=True
    ).strip()


def ensure_worktree(ref: str, dir_path: Path) -> Path:
    resolved_ref = resolve_ref(ref)
    if resolved_ref == CURRENT_HEAD and dir_path != REPO_ROOT:
        return REPO_ROOT

    if not dir_path.exists():
        subprocess.run(
            ["git", "-C", str(REPO_ROOT), "worktree", "add", "--detach", str(dir_path), resolved_ref],
            check=True,
        )

    ensure_clean_worktree(dir_path)
    current_head = subprocess.check_output(["git", "-C", str(dir_path), "rev-parse", "HEAD"], text=True).strip()
    if current_head != resolved_ref:
        raise SystemExit(f"Worktree {dir_path} is on {current_head}, expected {resolved_ref} for {ref}.")
    return dir_path


def flush_redis_db(redis_url: str) -> None:
    if redis_url:
        subprocess.run(["redis-cli", "-u", redis_url, "FLUSHDB"], check=True, stdout=subprocess.DEVNULL)


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
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return {"ok": 0, "status": 0, "elapsed_ms": elapsed_ms, "error": str(exc)}


def benchmark_server(label: str, port: int, cache_state: str) -> dict[str, Any]:
    base = f"http://127.0.0.1:{port}"
    summary: dict[str, Any] = {
        "label": label,
        "mode": MODE,
        "cache_state": cache_state,
        "steady_state_warmup_rounds": STEADY_STATE_WARMUP_ROUNDS,
        "runtime_mode": "production-manual-style",
        "endpoints": {},
    }

    for endpoint in ENDPOINTS:
        url = base + endpoint
        for _ in range(WARMUP_REQUESTS):
            request_once(url)

        started = time.perf_counter()
        results: list[dict[str, Any]] = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
            futures = [executor.submit(request_once, url) for _ in range(CONCURRENT_REQUESTS)]
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())
        total_elapsed = time.perf_counter() - started

        successes = [item for item in results if item["ok"] == 1]
        failures = [item for item in results if item["ok"] == 0]
        latencies = sorted(float(item["elapsed_ms"]) for item in successes)

        def percentile(p: float) -> float:
            if not latencies:
                return 0.0
            idx = min(len(latencies) - 1, max(0, int(round((len(latencies) - 1) * p))))
            return latencies[idx]

        summary["endpoints"][endpoint] = {
            "total_requests": CONCURRENT_REQUESTS,
            "concurrency": CONCURRENCY,
            "success_count": len(successes),
            "failure_count": len(failures),
            "requests_per_second": round((len(successes) / total_elapsed) if total_elapsed else 0.0, 3),
            "avg_ms": round(statistics.mean(latencies), 3) if latencies else 0.0,
            "median_ms": round(statistics.median(latencies), 3) if latencies else 0.0,
            "p95_ms": round(percentile(0.95), 3),
            "p99_ms": round(percentile(0.99), 3),
            "min_ms": round(min(latencies), 3) if latencies else 0.0,
            "max_ms": round(max(latencies), 3) if latencies else 0.0,
            "size_request_bytes": int(statistics.mean(int(item["bytes"]) for item in successes)) if successes else 0,
            "errors": [str(item.get("error", "")) for item in failures[:10]],
        }

    return summary


def aggregate_runs(label: str, runs: list[dict[str, Any]]) -> dict[str, Any]:
    endpoints = list(runs[0]["endpoints"].keys()) if runs else []
    summary: dict[str, Any] = {
        "label": label,
        "mode": MODE,
        "cache_state": runs[0].get("cache_state", "fresh"),
        "steady_state_warmup_rounds": runs[0].get("steady_state_warmup_rounds", 0),
        "runtime_mode": runs[0].get("runtime_mode", "production-manual-style"),
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

        errors: list[str] = []
        for row in endpoint_runs:
            for error in row.get("errors", []):
                if error and error not in errors:
                    errors.append(error)

        summary["endpoints"][endpoint] = {
            "total_requests": endpoint_runs[0]["total_requests"],
            "concurrency": endpoint_runs[0]["concurrency"],
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

    return summary


def write_benchmark_settings(temp_settings_dir: Path) -> None:
    (temp_settings_dir / f"{TEMP_SETTINGS_MODULE}.py").write_text(
        "\n".join(
            [
                "from josephlovesjohn_site.settings import *  # noqa: F401,F403",
                "import os",
                "",
                "DEBUG = False",
                'STATIC_ROOT = os.environ["STATIC_ROOT"]',
                'STATICFILES_STORAGE_BACKEND = "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"',
                "STORAGES = {",
                '    **STORAGES,',
                '    "staticfiles": {"BACKEND": STATICFILES_STORAGE_BACKEND},',
                "}",
                "WHITENOISE_AUTOREFRESH = False",
                "WHITENOISE_USE_FINDERS = False",
                "WHITENOISE_MAX_AGE = 31536000",
                "SECURE_SSL_REDIRECT = False",
                "SESSION_COOKIE_SECURE = False",
                "CSRF_COOKIE_SECURE = False",
                "SECURE_HSTS_SECONDS = 0",
                'ALLOWED_HOSTS = sorted(set([*ALLOWED_HOSTS, "127.0.0.1", "localhost", "testserver"]))',
                'SITE_URL = os.environ.get("SITE_URL", SITE_URL)',
                "VERIFY_STATIC_ASSET_FILES = False",
                "",
            ]
        ),
        encoding="utf-8",
    )


def collect_static(dir_path: Path, static_root: Path, temp_settings_dir: Path) -> None:
    database_url = SHARED_DATABASE_URL or f"sqlite:///{SHARED_DB_PATH}"
    env = os.environ.copy()
    env.update(
        {
            "PYTHONPATH": f"{temp_settings_dir}:{dir_path}",
            "DJANGO_SETTINGS_MODULE": TEMP_SETTINGS_MODULE,
            "STATIC_ROOT": str(static_root),
            "DATABASE_URL": database_url,
            "SITE_URL": "http://127.0.0.1",
            "SECRET_KEY": "bench-secret",
        }
    )
    subprocess.run(
        [str(PYTHON_BIN), "manage.py", "collectstatic", "--noinput", "--clear"],
        cwd=dir_path,
        env=env,
        check=True,
        stdout=subprocess.DEVNULL,
    )


def start_server(
    dir_path: Path,
    port: int,
    redis_url: str,
    static_root: Path,
    temp_settings_dir: Path,
) -> subprocess.Popen[str]:
    database_url = SHARED_DATABASE_URL or f"sqlite:///{SHARED_DB_PATH}"
    env = os.environ.copy()
    env.update(
        {
            "DATABASE_URL": database_url,
            "DEBUG": "false",
            "LOG_SQL_QUERIES": "false",
            "PYTHONPATH": f"{temp_settings_dir}:{dir_path}",
            "DJANGO_SETTINGS_MODULE": TEMP_SETTINGS_MODULE,
            "STATIC_ROOT": str(static_root),
            "SITE_URL": f"http://127.0.0.1:{port}",
            "SECRET_KEY": "bench-secret",
        }
    )

    if MODE == "scaling":
        env["SITE_CONTENT_CACHE_TTL"] = "300"
        env["CART_SUMMARY_CACHE_TTL"] = "60"
        env["REDIS_URL"] = redis_url
    else:
        env["SITE_CONTENT_CACHE_TTL"] = "0"
        env["CART_SUMMARY_CACHE_TTL"] = "0"

    proc = subprocess.Popen(
        [
            str(GUNICORN_BIN),
            "josephlovesjohn_site.wsgi:application",
            "--bind",
            f"127.0.0.1:{port}",
            "--workers",
            str(GUNICORN_WORKERS),
        ],
        cwd=dir_path,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    url = f"http://127.0.0.1:{port}/"
    for _ in range(40):
        if proc.poll() is not None:
            output = proc.stdout.read() if proc.stdout else ""
            raise RuntimeError(f"Gunicorn failed to start on {port}.\n{output}")
        try:
            with urllib.request.urlopen(url, timeout=1):
                return proc
        except Exception:
            time.sleep(0.5)

    proc.send_signal(signal.SIGTERM)
    raise RuntimeError(f"Gunicorn did not become ready on {port}.")


def stop_server(proc: subprocess.Popen[str] | None) -> None:
    if proc is None or proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)


def prewarm_server(port: int) -> None:
    for _ in range(STEADY_STATE_WARMUP_ROUNDS):
        for endpoint in ENDPOINTS:
            urllib.request.urlopen(f"http://127.0.0.1:{port}{endpoint}", timeout=30).read()


def run_suite(cache_state: str, old_server: tuple[str, int], new_server: tuple[str, int]) -> dict[str, Any]:
    if MODE == "scaling":
        flush_redis_db(OLD_REDIS_URL)
        flush_redis_db(NEW_REDIS_URL)

    if cache_state == "warm":
        prewarm_server(old_server[1])
        prewarm_server(new_server[1])

    old_runs: list[dict[str, Any]] = []
    new_runs: list[dict[str, Any]] = []
    for run_index in range(1, CONCURRENCY_RUNS + 1):
        if run_index % 2 == 1:
            old_runs.append(benchmark_server(old_server[0], old_server[1], cache_state))
            new_runs.append(benchmark_server(new_server[0], new_server[1], cache_state))
        else:
            new_runs.append(benchmark_server(new_server[0], new_server[1], cache_state))
            old_runs.append(benchmark_server(old_server[0], old_server[1], cache_state))

    return {
        "old": aggregate_runs(old_server[0], old_runs),
        "new": aggregate_runs(new_server[0], new_runs),
    }


def main() -> int:
    ensure_executable(PYTHON_BIN, "Python")
    ensure_executable(GUNICORN_BIN, "Gunicorn")
    if MODE == "scaling" and (not OLD_REDIS_URL or not NEW_REDIS_URL):
        raise SystemExit("MODE=scaling requires OLD_REDIS_URL and NEW_REDIS_URL.")

    old_worktree = ensure_worktree(OLD_REF, OLD_WORKTREE)
    new_worktree = ensure_worktree(NEW_REF, NEW_WORKTREE)

    temp_settings_dir = Path(tempfile.mkdtemp(prefix="jlj-manual-bench-settings."))
    old_static_root = Path(tempfile.mkdtemp(prefix="jlj-manual-old-static."))
    new_static_root = Path(tempfile.mkdtemp(prefix="jlj-manual-new-static."))
    old_proc: subprocess.Popen[str] | None = None
    new_proc: subprocess.Popen[str] | None = None

    try:
        write_benchmark_settings(temp_settings_dir)
        collect_static(old_worktree, old_static_root, temp_settings_dir)
        collect_static(new_worktree, new_static_root, temp_settings_dir)

        old_proc = start_server(old_worktree, OLD_PORT, OLD_REDIS_URL, old_static_root, temp_settings_dir)
        new_proc = start_server(new_worktree, NEW_PORT, NEW_REDIS_URL, new_static_root, temp_settings_dir)

        result = {
            "metadata": {
                "old_ref": OLD_REF,
                "new_ref": NEW_REF,
                "old_label": OLD_LABEL,
                "new_label": NEW_LABEL,
                "mode": MODE,
                "concurrency_runs": CONCURRENCY_RUNS,
                "steady_state_warmup_rounds": STEADY_STATE_WARMUP_ROUNDS,
                "runtime_mode": "production-manual-style",
                "startup_shape": "long_lived_servers_single_collectstatic_single_flush_per_suite",
            },
            "fresh": run_suite("fresh", (OLD_LABEL, OLD_PORT), (NEW_LABEL, NEW_PORT)),
            "warm": run_suite("warm", (OLD_LABEL, OLD_PORT), (NEW_LABEL, NEW_PORT)),
        }

        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(str(OUTPUT_PATH))
        return 0
    finally:
        stop_server(old_proc)
        stop_server(new_proc)
        shutil.rmtree(old_static_root, ignore_errors=True)
        shutil.rmtree(new_static_root, ignore_errors=True)
        shutil.rmtree(temp_settings_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
