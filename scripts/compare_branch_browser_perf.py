#!/usr/bin/env python3
"""Compare browser-side route performance for two git refs."""

from __future__ import annotations

import json
import os
import signal
import statistics
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
PARENT_DIR = REPO_ROOT.parent
CURRENT_HEAD = subprocess.check_output(
    ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
    text=True,
).strip()

OLD_REF = os.environ.get("OLD_REF") or os.environ.get("OLD_BRANCH", "feature/render_deploy")
NEW_REF = os.environ.get("NEW_REF") or os.environ.get("NEW_BRANCH", "feature/scaling")
OLD_LABEL = os.environ.get("OLD_LABEL", OLD_REF)
NEW_LABEL = os.environ.get("NEW_LABEL", NEW_REF)
OLD_PORT = int(os.environ.get("OLD_PORT", "8060"))
NEW_PORT = int(os.environ.get("NEW_PORT", "8061"))
MODE = os.environ.get("MODE", "baseline").strip()
ENDPOINTS = [item.strip() for item in os.environ.get("ENDPOINTS", "/,/music/,/art/").split(",") if item.strip()]
OLD_REDIS_URL = os.environ.get("OLD_REDIS_URL", "").strip()
NEW_REDIS_URL = os.environ.get("NEW_REDIS_URL", "").strip()
SHARED_DB_PATH = Path(os.environ.get("SHARED_DB_PATH", str(REPO_ROOT / "db.sqlite3")))
SHARED_DATABASE_URL = os.environ.get("SHARED_DATABASE_URL", "").strip()
PYTHON_BIN = Path(os.environ.get("PYTHON_BIN", str(REPO_ROOT / ".venv/bin/python")))
OLD_WORKTREE = Path(os.environ.get("OLD_WORKTREE", str(PARENT_DIR / "jlj-render-deploy-bench")))
NEW_WORKTREE = Path(os.environ.get("NEW_WORKTREE", str(PARENT_DIR / "jlj-scaling-bench")))
BROWSER_ENGINE = os.environ.get("BROWSER_ENGINE", "chromium").strip()
BROWSER_RUNS = int(os.environ.get("BROWSER_RUNS", "3"))
BROWSER_INTERACTION_RUNS = int(os.environ.get("BROWSER_INTERACTION_RUNS", "3"))

METRICS_INIT_SCRIPT = """
(() => {
  window.__jljBrowserPerf = window.__jljBrowserPerf || { lcp: null };
  if (!("PerformanceObserver" in window)) {
    return;
  }
  try {
    new PerformanceObserver((list) => {
      const entries = list.getEntries();
      const entry = entries[entries.length - 1];
      if (entry) {
        window.__jljBrowserPerf.lcp = entry.startTime;
      }
    }).observe({ type: "largest-contentful-paint", buffered: true });
  } catch (error) {
    // Ignore browsers without buffered LCP support.
  }
})();
"""

METRICS_EVAL_SCRIPT = """
() => {
  const navigation = performance.getEntriesByType("navigation")[0] || null;
  const resources = performance.getEntriesByType("resource");

  function classify(entry) {
    const pathname = (entry.name || "").split("?")[0].toLowerCase();
    const extension = pathname.includes(".") ? pathname.split(".").pop() : "";
    if (["png", "jpg", "jpeg", "gif", "webp", "svg", "avif"].includes(extension)) return "image";
    if (["mp4", "webm", "mov", "m4v"].includes(extension)) return "video";
    if (["css"].includes(extension)) return "style";
    if (["js", "mjs"].includes(extension)) return "script";
    if (["woff", "woff2", "ttf", "otf", "eot"].includes(extension)) return "font";
    if (entry.initiatorType === "img") return "image";
    if (entry.initiatorType === "video") return "video";
    if (entry.initiatorType === "css") return "style";
    if (entry.initiatorType === "script") return "script";
    if (entry.initiatorType === "font") return "font";
    return entry.initiatorType || "other";
  }

  const byType = {};
  const largestResources = [];

  if (navigation) {
    byType.document = {
      request_count: 1,
      transfer_size_bytes: navigation.transferSize || 0,
      decoded_body_size_bytes: navigation.decodedBodySize || 0,
    };
  }

  for (const entry of resources) {
    const type = classify(entry);
    if (!byType[type]) {
      byType[type] = {
        request_count: 0,
        transfer_size_bytes: 0,
        decoded_body_size_bytes: 0,
      };
    }

    byType[type].request_count += 1;
    byType[type].transfer_size_bytes += entry.transferSize || 0;
    byType[type].decoded_body_size_bytes += entry.decodedBodySize || 0;

    largestResources.push({
      url: entry.name,
      type,
      transfer_size_bytes: entry.transferSize || 0,
      decoded_body_size_bytes: entry.decodedBodySize || 0,
      duration_ms: entry.duration || 0,
    });
  }

  largestResources.sort((left, right) => right.transfer_size_bytes - left.transfer_size_bytes);

  const totalTransferSize = Object.values(byType).reduce((total, bucket) => total + bucket.transfer_size_bytes, 0);
  const totalDecodedBodySize = Object.values(byType).reduce(
    (total, bucket) => total + bucket.decoded_body_size_bytes,
    0
  );
  const requestCount = Object.values(byType).reduce((total, bucket) => total + bucket.request_count, 0);

  return {
    dom_content_loaded_ms: navigation ? navigation.domContentLoadedEventEnd : null,
    load_ms: navigation ? navigation.loadEventEnd : null,
    ttfb_ms: navigation ? navigation.responseStart : null,
    lcp_ms: window.__jljBrowserPerf ? window.__jljBrowserPerf.lcp : null,
    request_count: requestCount,
    transfer_size_bytes: totalTransferSize,
    decoded_body_size_bytes: totalDecodedBodySize,
    by_type: byType,
    largest_resources: largestResources.slice(0, 5),
  };
}
"""


def require_playwright():
    from playwright.sync_api import sync_playwright

    return sync_playwright


def browser_executable_candidates(browser_engine_name: str) -> tuple[str, ...]:
    if browser_engine_name == "firefox":
        candidates = [os.environ.get("PLAYWRIGHT_FIREFOX_EXECUTABLE")]
        return tuple(candidate for candidate in candidates if candidate)

    if browser_engine_name == "webkit":
        candidates = [os.environ.get("PLAYWRIGHT_WEBKIT_EXECUTABLE")]
        return tuple(candidate for candidate in candidates if candidate)

    candidates = [
        os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE"),
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
    ]
    return tuple(candidate for candidate in candidates if candidate)


def browser_launch_options(browser_engine_name: str) -> dict[str, object]:
    launch_options: dict[str, object] = {"headless": True}
    if browser_engine_name == "chromium":
        launch_options["args"] = ["--disable-dev-shm-usage", "--no-sandbox"]

    for candidate in browser_executable_candidates(browser_engine_name):
        if Path(candidate).exists():
            launch_options["executable_path"] = candidate
            break

    return launch_options


def resolve_ref(ref: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(REPO_ROOT), "rev-parse", f"{ref}^{{commit}}"],
        text=True,
    ).strip()


def ensure_clean_worktree(path: Path) -> None:
    if not (path / ".git").exists() and not path.exists():
        return

    status = subprocess.check_output(
        ["git", "-C", str(path), "status", "--short"],
        text=True,
    ).strip()
    if status:
        raise RuntimeError(f"Existing worktree has local changes: {path}")


def ensure_worktree(ref: str, target: Path) -> Path:
    resolved_ref = resolve_ref(ref)
    if resolved_ref == CURRENT_HEAD and target != REPO_ROOT:
        return REPO_ROOT

    if not target.exists():
        subprocess.run(
            ["git", "-C", str(REPO_ROOT), "worktree", "add", "--detach", str(target), resolved_ref],
            check=True,
        )

    ensure_clean_worktree(target)
    current_head = subprocess.check_output(
        ["git", "-C", str(target), "rev-parse", "HEAD"],
        text=True,
    ).strip()
    if current_head != resolved_ref:
        raise RuntimeError(f"Worktree {target} is on {current_head}, expected {resolved_ref}.")
    return target


def wait_for_http(url: str, timeout: float = 20.0) -> None:
    deadline = time.time() + timeout
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status < 500:
                    return
        except Exception as error:  # pragma: no cover - defensive during process startup.
            last_error = error
        time.sleep(0.5)
    raise RuntimeError(f"Server did not become ready at {url}: {last_error}")


def start_server(worktree: Path, port: int, redis_url: str) -> subprocess.Popen[str]:
    database_url = SHARED_DATABASE_URL or f"sqlite:///{SHARED_DB_PATH}"
    env = os.environ.copy()
    env.update(
        {
            "DATABASE_URL": database_url,
            "DEBUG": "true",
            "LOG_SQL_QUERIES": "false",
            "SITE_URL": f"http://127.0.0.1:{port}",
            "SITE_CONTENT_CACHE_TTL": "300" if MODE == "scaling" else "0",
            "CART_SUMMARY_CACHE_TTL": "60" if MODE == "scaling" else "0",
        }
    )
    if MODE == "scaling" and redis_url:
        env["REDIS_URL"] = redis_url

    log_file = tempfile.NamedTemporaryFile(prefix="jlj-browser-server-", suffix=".log", delete=False)
    log_file.close()
    log_handle = open(log_file.name, "w", encoding="utf-8")

    process = subprocess.Popen(
        [
            str(PYTHON_BIN),
            "manage.py",
            "runserver",
            f"127.0.0.1:{port}",
            "--noreload",
        ],
        cwd=worktree,
        env=env,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True,
    )
    log_handle.close()
    try:
        wait_for_http(f"http://127.0.0.1:{port}/")
        return process
    except Exception:
        stop_server(process)
        raise


def stop_server(process: subprocess.Popen[str] | None) -> None:
    if process is None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except OSError:
        try:
            process.terminate()
        except OSError:
            return
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except OSError:
            process.kill()
        process.wait(timeout=5)


def round_float(value: float | None) -> float | None:
    if value is None:
        return None
    return round(float(value), 3)


def normalize_metric_run(raw: dict[str, Any]) -> dict[str, Any]:
    largest_resources = [
        {
            "url": item["url"],
            "type": item["type"],
            "transfer_size_bytes": int(item["transfer_size_bytes"]),
            "decoded_body_size_bytes": int(item["decoded_body_size_bytes"]),
            "duration_ms": round_float(float(item["duration_ms"])),
        }
        for item in raw.get("largest_resources", [])
    ]
    return {
        "ttfb_ms": round_float(raw.get("ttfb_ms")),
        "dom_content_loaded_ms": round_float(raw.get("dom_content_loaded_ms")),
        "load_ms": round_float(raw.get("load_ms")),
        "lcp_ms": round_float(raw.get("lcp_ms")),
        "request_count": int(raw.get("request_count") or 0),
        "transfer_size_bytes": int(raw.get("transfer_size_bytes") or 0),
        "decoded_body_size_bytes": int(raw.get("decoded_body_size_bytes") or 0),
        "by_type": raw.get("by_type", {}),
        "largest_resources": largest_resources,
    }


def collect_endpoint_runs(browser, base_url: str, endpoint: str, run_count: int) -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    target_url = f"{base_url}{endpoint}"
    for _ in range(run_count):
        context = browser.new_context(viewport={"width": 1440, "height": 960})
        page = context.new_page()
        page.set_default_timeout(20_000)
        page.add_init_script(METRICS_INIT_SCRIPT)
        page.goto(target_url, wait_until="load")
        page.wait_for_timeout(300)
        raw_metrics = page.evaluate(METRICS_EVAL_SCRIPT)
        runs.append(normalize_metric_run(raw_metrics))
        context.close()
    return runs


def median_or_none(values: list[float | None]) -> float | None:
    filtered = [value for value in values if value is not None]
    if not filtered:
        return None
    return round_float(statistics.median(filtered))


def aggregate_endpoint_runs(runs: list[dict[str, Any]]) -> dict[str, Any]:
    cold_run = runs[0]
    warm_runs = runs[1:] or runs
    return {
        "cold_ttfb_ms": cold_run["ttfb_ms"],
        "cold_dom_content_loaded_ms": cold_run["dom_content_loaded_ms"],
        "cold_load_ms": cold_run["load_ms"],
        "cold_lcp_ms": cold_run["lcp_ms"],
        "cold_request_count": cold_run["request_count"],
        "cold_transfer_size_bytes": cold_run["transfer_size_bytes"],
        "cold_decoded_body_size_bytes": cold_run["decoded_body_size_bytes"],
        "warm_median_ttfb_ms": median_or_none([run["ttfb_ms"] for run in warm_runs]),
        "warm_median_dom_content_loaded_ms": median_or_none([run["dom_content_loaded_ms"] for run in warm_runs]),
        "warm_median_load_ms": median_or_none([run["load_ms"] for run in warm_runs]),
        "warm_median_lcp_ms": median_or_none([run["lcp_ms"] for run in warm_runs]),
        "warm_median_request_count": int(round(statistics.median([run["request_count"] for run in warm_runs]))),
        "warm_median_transfer_size_bytes": int(
            round(statistics.median([run["transfer_size_bytes"] for run in warm_runs]))
        ),
        "warm_median_decoded_body_size_bytes": int(
            round(statistics.median([run["decoded_body_size_bytes"] for run in warm_runs]))
        ),
        "cold_asset_types": cold_run["by_type"],
        "cold_largest_resources": cold_run["largest_resources"],
        "runs": [
            {
                "ttfb_ms": run["ttfb_ms"],
                "dom_content_loaded_ms": run["dom_content_loaded_ms"],
                "load_ms": run["load_ms"],
                "lcp_ms": run["lcp_ms"],
                "request_count": run["request_count"],
                "transfer_size_bytes": run["transfer_size_bytes"],
                "decoded_body_size_bytes": run["decoded_body_size_bytes"],
            }
            for run in runs
        ],
    }


def wait_for_js(page, expression: str, timeout_ms: int = 20_000) -> None:
    page.wait_for_function(f"() => !!({expression})", timeout=timeout_ms)


ART_TRIGGER_SELECTOR = "[data-art-lightbox='image'], [data-art-lightbox='video']"
ART_MEDIA_READY_EXPR = """
(() => {
  const image = document.querySelector('.art-lightbox-image');
  if (image && !image.hasAttribute('hidden') && !!image.getAttribute('src') && image.complete) {
    return true;
  }

  const video = document.querySelector('.art-lightbox-video');
  if (video && !video.hasAttribute('hidden') && !!video.getAttribute('src') && video.readyState >= 2) {
    return true;
  }

  return false;
})()
"""


def collect_art_interactions(browser, base_url: str, run_count: int) -> dict[str, Any]:
    runs: list[dict[str, float]] = []
    target_url = f"{base_url}/art/"
    for _ in range(run_count):
        context = browser.new_context(viewport={"width": 1440, "height": 960})
        page = context.new_page()
        page.set_default_timeout(20_000)
        page.goto(target_url, wait_until="load")
        page.wait_for_selector("article#art.active")
        page.wait_for_selector(ART_TRIGGER_SELECTOR)

        start = time.perf_counter()
        page.locator(ART_TRIGGER_SELECTOR).first.click()
        wait_for_js(page, "document.getElementById('art-lightbox').getAttribute('aria-hidden') === 'false'")
        open_visible_ms = round((time.perf_counter() - start) * 1000, 3)

        start = time.perf_counter()
        wait_for_js(page, ART_MEDIA_READY_EXPR)
        open_ready_ms = round((time.perf_counter() - start) * 1000, 3)

        start = time.perf_counter()
        page.click("[data-art-close]")
        wait_for_js(page, "document.getElementById('art-lightbox').getAttribute('aria-hidden') === 'true'")
        close_ms = round((time.perf_counter() - start) * 1000, 3)

        start = time.perf_counter()
        page.locator(ART_TRIGGER_SELECTOR).first.click()
        wait_for_js(page, "document.getElementById('art-lightbox').getAttribute('aria-hidden') === 'false'")
        reopen_visible_ms = round((time.perf_counter() - start) * 1000, 3)

        start = time.perf_counter()
        wait_for_js(page, ART_MEDIA_READY_EXPR)
        reopen_ready_ms = round((time.perf_counter() - start) * 1000, 3)

        page.click("[data-art-close]")
        wait_for_js(page, "document.getElementById('art-lightbox').getAttribute('aria-hidden') === 'true'")
        context.close()

        runs.append(
            {
                "open_visible_ms": open_visible_ms,
                "open_ready_ms": open_ready_ms,
                "close_ms": close_ms,
                "reopen_visible_ms": reopen_visible_ms,
                "reopen_ready_ms": reopen_ready_ms,
            }
        )

    return {
        "scenario": "lightbox-open-close-reopen",
        "run_count": run_count,
        "open_visible_ms": round_float(statistics.median(run["open_visible_ms"] for run in runs)),
        "open_ready_ms": round_float(statistics.median(run["open_ready_ms"] for run in runs)),
        "close_ms": round_float(statistics.median(run["close_ms"] for run in runs)),
        "reopen_visible_ms": round_float(statistics.median(run["reopen_visible_ms"] for run in runs)),
        "reopen_ready_ms": round_float(statistics.median(run["reopen_ready_ms"] for run in runs)),
        "runs": runs,
    }


def collect_branch_summary(browser, worktree: Path, label: str, port: int, redis_url: str) -> dict[str, Any]:
    process = None
    base_url = f"http://127.0.0.1:{port}"
    try:
        process = start_server(worktree, port, redis_url)
        summary: dict[str, Any] = {
            "label": label,
            "mode": MODE,
            "browser_engine": BROWSER_ENGINE,
            "run_count": BROWSER_RUNS,
            "interaction_run_count": BROWSER_INTERACTION_RUNS,
            "status": "ok",
            "endpoints": {},
            "interactions": {},
        }
        for endpoint in ENDPOINTS:
            runs = collect_endpoint_runs(browser, base_url, endpoint, BROWSER_RUNS)
            summary["endpoints"][endpoint] = aggregate_endpoint_runs(runs)
            if endpoint == "/art/":
                try:
                    summary["interactions"][endpoint] = collect_art_interactions(
                        browser,
                        base_url,
                        BROWSER_INTERACTION_RUNS,
                    )
                except Exception as error:
                    summary.setdefault("interaction_errors", {})[endpoint] = str(error)
        return summary
    finally:
        stop_server(process)


def build_skip_summary(label: str, reason: str) -> dict[str, Any]:
    return {
        "label": label,
        "mode": MODE,
        "browser_engine": BROWSER_ENGINE,
        "run_count": BROWSER_RUNS,
        "interaction_run_count": BROWSER_INTERACTION_RUNS,
        "status": "skipped",
        "reason": reason,
        "endpoints": {},
        "interactions": {},
    }


def write_summary(summary: dict[str, Any]) -> Path:
    handle, raw_path = tempfile.mkstemp(prefix="jlj-browser-", suffix=".json")
    path = Path(raw_path)
    with os.fdopen(handle, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
    return path


def main() -> int:
    try:
        sync_playwright = require_playwright()
    except Exception as error:
        old_path = write_summary(build_skip_summary(OLD_LABEL, f"Playwright unavailable: {error}"))
        new_path = write_summary(build_skip_summary(NEW_LABEL, f"Playwright unavailable: {error}"))
        print("Browser comparison skipped.")
        print(f"  {old_path}")
        print(f"  {new_path}")
        return 0

    try:
        old_worktree = ensure_worktree(OLD_REF, OLD_WORKTREE)
        new_worktree = ensure_worktree(NEW_REF, NEW_WORKTREE)
    except Exception as error:
        raise SystemExit(str(error)) from error

    with sync_playwright() as playwright:
        try:
            browser_type = getattr(playwright, BROWSER_ENGINE)
            browser = browser_type.launch(**browser_launch_options(BROWSER_ENGINE))
        except Exception as error:
            old_path = write_summary(build_skip_summary(OLD_LABEL, f"Browser launch failed: {error}"))
            new_path = write_summary(build_skip_summary(NEW_LABEL, f"Browser launch failed: {error}"))
            print("Browser comparison skipped.")
            print(f"  {old_path}")
            print(f"  {new_path}")
            return 0

        try:
            old_summary = collect_branch_summary(browser, old_worktree, OLD_LABEL, OLD_PORT, OLD_REDIS_URL)
            new_summary = collect_branch_summary(browser, new_worktree, NEW_LABEL, NEW_PORT, NEW_REDIS_URL)
        finally:
            browser.close()

    old_path = write_summary(old_summary)
    new_path = write_summary(new_summary)
    print("Browser comparison complete.")
    print(f"  {old_path}")
    print(f"  {new_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
