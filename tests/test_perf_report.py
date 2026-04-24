"""Smoke checks for the generated performance report structure."""

from __future__ import annotations

import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "generate_perf_report.py"
SPEC = importlib.util.spec_from_file_location("generate_perf_report", MODULE_PATH)
assert SPEC and SPEC.loader
generate_perf_report = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(generate_perf_report)


def _browser_summary(status: str = "ok") -> dict:
    if status != "ok":
        return {
            "label": "old",
            "mode": "baseline",
            "browser_engine": "chromium",
            "run_count": 3,
            "interaction_run_count": 3,
            "status": status,
            "reason": "Browser unavailable",
            "endpoints": {},
            "interactions": {},
        }

    return {
        "label": "old",
        "mode": "baseline",
        "browser_engine": "chromium",
        "run_count": 3,
        "interaction_run_count": 3,
        "status": "ok",
        "endpoints": {
            "/art/": {
                "cold_ttfb_ms": 10.0,
                "cold_dom_content_loaded_ms": 40.0,
                "cold_load_ms": 50.0,
                "cold_lcp_ms": 45.0,
                "cold_request_count": 8,
                "cold_transfer_size_bytes": 120000,
                "cold_decoded_body_size_bytes": 250000,
                "warm_median_ttfb_ms": 8.0,
                "warm_median_dom_content_loaded_ms": 30.0,
                "warm_median_load_ms": 35.0,
                "warm_median_lcp_ms": 31.0,
                "warm_median_request_count": 8,
                "warm_median_transfer_size_bytes": 120000,
                "warm_median_decoded_body_size_bytes": 250000,
                "cold_asset_types": {},
                "cold_largest_resources": [],
                "runs": [],
            }
        },
        "interactions": {
            "/art/": {
                "scenario": "lightbox-open-close-reopen",
                "run_count": 3,
                "open_visible_ms": 5.0,
                "open_ready_ms": 12.0,
                "close_ms": 6.0,
                "reopen_visible_ms": 4.0,
                "reopen_ready_ms": 5.0,
                "runs": [],
            }
        },
    }


def _report(browser_status: str = "ok") -> dict:
    browser_old = _browser_summary(browser_status)
    browser_new = _browser_summary(browser_status)
    browser_new["label"] = "new"
    if browser_status == "ok":
        browser_new["endpoints"]["/art/"]["cold_transfer_size_bytes"] = 60000
        browser_new["endpoints"]["/art/"]["warm_median_load_ms"] = 20.0
        browser_new["interactions"]["/art/"]["open_visible_ms"] = 3.0

    endpoint_metrics = {
        "/art/": {
            "cold_ms": 20.0,
            "avg_ms": 18.0,
            "min_ms": 17.0,
            "max_ms": 19.0,
            "runs_ms": [18.0, 18.0],
        }
    }
    query_metrics = {"/art/": {"query_counts": [6, 0], "statuses": [200, 200], "delta_after_first": -6}}
    concurrency_metrics = {
        "/art/": {
            "avg_ms": 20.0,
            "p95_ms": 30.0,
            "requests_per_second": 900.0,
            "success_count": 200,
            "total_requests": 200,
            "runs": [{"avg_ms": 20.0}],
        }
    }
    profile_metrics = {
        "/art/": {
            "elapsed_ms": 12.0,
            "top_files": [],
            "top_functions": [],
        }
    }

    return {
        "metadata": {
            "generated_at": "2026-04-24T17:00:00+00:00",
            "old_ref": "feature/render_deploy",
            "new_ref": "feature/scaling",
            "old_label": "render_deploy",
            "new_label": "scaling",
            "shared_database_url": "postgresql://postgres@127.0.0.1:5432/jlj_bench",
            "concurrency_runs": 5,
            "steady_state_warmup_rounds": 5,
            "browser_engine": "chromium",
            "browser_runs": 3,
            "browser_interaction_runs": 3,
        },
        "endpoints": ["/art/"],
        "timings": {
            "baseline": {"old": {"endpoints": endpoint_metrics}, "new": {"endpoints": endpoint_metrics}},
            "scaling": {"old": {"endpoints": endpoint_metrics}, "new": {"endpoints": endpoint_metrics}},
        },
        "queries": {
            "baseline": {"old": {"endpoints": query_metrics}, "new": {"endpoints": query_metrics}},
            "scaling": {"old": {"endpoints": query_metrics}, "new": {"endpoints": query_metrics}},
        },
        "concurrency": {
            "fresh": {
                "old": {"endpoints": concurrency_metrics, "run_count": 5, "steady_state_warmup_rounds": 5},
                "new": {"endpoints": concurrency_metrics, "run_count": 5, "steady_state_warmup_rounds": 5},
            },
            "warm": {
                "old": {"endpoints": concurrency_metrics, "run_count": 5, "steady_state_warmup_rounds": 5},
                "new": {"endpoints": concurrency_metrics, "run_count": 5, "steady_state_warmup_rounds": 5},
            },
        },
        "browser": {
            "baseline": {"old": browser_old, "new": browser_new},
            "scaling": {"old": browser_old, "new": browser_new},
        },
        "profiles": {
            "baseline": {"old": {"endpoints": profile_metrics}, "new": {"endpoints": profile_metrics}},
            "scaling": {"old": {"endpoints": profile_metrics}, "new": {"endpoints": profile_metrics}},
        },
        "findings": [],
    }


def test_build_html_renders_browser_sections() -> None:
    html = generate_perf_report.build_html(_report())

    assert "Browser Load" in html
    assert "Browser Interactions" in html
    assert "Baseline /art/ interaction journey" in html
    assert "Cumulative milestone timing across the open, close, and reopen flow." in html
    assert "Open visible" in html
    assert "Reopen ready" in html
    assert "open visible" in html
    assert "/art/" in html
    assert "58.6 KB" in html


def test_build_html_renders_browser_skip_reason() -> None:
    html = generate_perf_report.build_html(_report(browser_status="skipped"))

    assert "Browser unavailable" in html
