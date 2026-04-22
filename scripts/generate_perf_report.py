#!/usr/bin/env python3
"""Generate a combined HTML performance report for branch comparisons."""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import re
import statistics
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
DETAIL_PATH_RE = re.compile(r"^\s{2}(/.+)$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default="perf-report", help="Directory to write HTML/JSON outputs into.")
    parser.add_argument("--runs", type=int, default=10, help="Warm request timing samples per route.")
    parser.add_argument(
        "--query-requests",
        type=int,
        default=2,
        help="Repeated requests per endpoint for query count comparisons.",
    )
    parser.add_argument(
        "--profile-warmup-requests",
        type=int,
        default=1,
        help="Warmup requests before collecting Python profile hotspots.",
    )
    parser.add_argument(
        "--endpoints",
        default="/,/music/,/art/",
        help="Comma-separated endpoints to benchmark.",
    )
    parser.add_argument(
        "--top-profile-rows",
        type=int,
        default=12,
        help="Number of top files/functions to keep in profile outputs.",
    )
    parser.add_argument(
        "--concurrent-requests",
        type=int,
        default=200,
        help="Total requests per endpoint for the concurrent Gunicorn benchmark.",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=20,
        help="Concurrent workers for the Gunicorn benchmark load generator.",
    )
    parser.add_argument(
        "--gunicorn-workers",
        type=int,
        default=4,
        help="Gunicorn workers per branch in the concurrent benchmark.",
    )
    parser.add_argument(
        "--concurrent-warmup-requests",
        type=int,
        default=1,
        help="Warmup requests per endpoint before concurrent benchmarking.",
    )
    return parser.parse_args()


def require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"{name} is required for the combined performance report.")
    return value


def mask_url(raw: str) -> str:
    if not raw:
        return ""
    parts = urlsplit(raw)
    netloc = parts.hostname or ""
    if parts.port:
        netloc = f"{netloc}:{parts.port}"
    if parts.username:
        if parts.password:
            netloc = f"{parts.username}:***@{netloc}"
        else:
            netloc = f"{parts.username}@{netloc}"
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


def flush_redis_db(url: str) -> None:
    import redis

    client = redis.Redis.from_url(url)
    client.flushdb()


def run_script(script_name: str, env: dict[str, str]) -> tuple[str, list[Path]]:
    script_path = SCRIPTS_DIR / script_name
    result = subprocess.run(
        [str(script_path)],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    stdout = result.stdout.strip()
    stderr = result.stderr.strip()
    if result.returncode != 0:
        raise RuntimeError(
            f"{script_name} failed with exit code {result.returncode}\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"
        )

    detail_paths = [Path(match.group(1)) for line in stdout.splitlines() if (match := DETAIL_PATH_RE.match(line))]
    if len(detail_paths) != 2:
        raise RuntimeError(f"Could not parse detail JSON paths from {script_name} output:\n{stdout}")
    return stdout, detail_paths


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def median(values: list[float]) -> float:
    return statistics.median(values) if values else 0.0


def top_deltas(
    old_rows: list[dict[str, Any]],
    new_rows: list[dict[str, Any]],
    *,
    key_fields: tuple[str, ...],
    value_field: str,
    limit: int = 8,
) -> list[dict[str, Any]]:
    old_map = {tuple(str(row[field]) for field in key_fields): row for row in old_rows}
    new_map = {tuple(str(row[field]) for field in key_fields): row for row in new_rows}
    keys = set(old_map) | set(new_map)
    results: list[dict[str, Any]] = []
    for key in keys:
        old_value = float(old_map.get(key, {}).get(value_field, 0.0))
        new_value = float(new_map.get(key, {}).get(value_field, 0.0))
        delta = round(new_value - old_value, 3)
        if delta <= 0:
            continue
        row: dict[str, Any] = {field: key[idx] for idx, field in enumerate(key_fields)}
        row["old_value"] = round(old_value, 3)
        row["new_value"] = round(new_value, 3)
        row["delta"] = delta
        results.append(row)
    return sorted(results, key=lambda row: row["delta"], reverse=True)[:limit]


def build_findings(report: dict[str, Any]) -> list[str]:
    findings: list[str] = []

    baseline_timing = report["timings"]["baseline"]
    scaling_timing = report["timings"]["scaling"]
    baseline_queries = report["queries"]["baseline"]
    scaling_queries = report["queries"]["scaling"]
    concurrency = report["concurrency"]["scaling"]

    for endpoint in report["endpoints"]:
        base_timing_delta = (
            baseline_timing["new"]["endpoints"][endpoint]["avg_ms"]
            - baseline_timing["old"]["endpoints"][endpoint]["avg_ms"]
        )
        scaling_timing_delta = (
            scaling_timing["new"]["endpoints"][endpoint]["avg_ms"]
            - scaling_timing["old"]["endpoints"][endpoint]["avg_ms"]
        )
        base_query_new = baseline_queries["new"]["endpoints"][endpoint]["query_counts"]
        scaling_query_new = scaling_queries["new"]["endpoints"][endpoint]["query_counts"]

        if scaling_query_new[-1] == 0 and scaling_query_new[0] > 0:
            findings.append(
                f"`{endpoint}` reaches a zero-query warm path on `feature/scaling`, "
                f"but its warm request time is still {scaling_timing_delta:.2f}ms slower than the baseline branch locally."
            )

        if base_timing_delta > 0.75:
            findings.append(
                f"`{endpoint}` shows a steady uncached overhead on `feature/scaling` "
                f"({base_timing_delta:.2f}ms slower in baseline mode)."
            )

        if scaling_timing_delta < base_timing_delta - 0.25:
            findings.append(
                f"Caching pays some of the overhead back on `{endpoint}`: "
                f"delta improves from {base_timing_delta:.2f}ms in baseline mode "
                f"to {scaling_timing_delta:.2f}ms in scaling mode."
            )

        if base_query_new[-1] == base_query_new[0] and scaling_query_new[-1] < scaling_query_new[0]:
            findings.append(
                f"`{endpoint}` only reduces repeated DB work on `feature/scaling`; "
                "the older branch continues issuing the same queries on repeated requests."
            )

        concurrency_old = concurrency["old"]["endpoints"][endpoint]
        concurrency_new = concurrency["new"]["endpoints"][endpoint]
        if (
            concurrency_new["success_count"] == concurrency_new["total_requests"]
            and concurrency_old["success_count"] == concurrency_old["total_requests"]
            and concurrency_new["avg_ms"] < concurrency_old["avg_ms"] * 0.75
        ):
            findings.append(
                f"Under concurrent Gunicorn load, `{endpoint}` improves from "
                f"{concurrency_old['avg_ms']:.2f}ms avg / {concurrency_old['requests_per_second']:.1f} req/s "
                f"to {concurrency_new['avg_ms']:.2f}ms avg / {concurrency_new['requests_per_second']:.1f} req/s "
                "on `feature/scaling`."
            )

    deduped: list[str] = []
    seen: set[str] = set()
    for item in findings:
        if item not in seen:
            deduped.append(item)
            seen.add(item)
    return deduped


def render_table(headers: list[str], rows: list[list[str]]) -> str:
    head_html = "".join(f"<th>{html.escape(cell)}</th>" for cell in headers)
    row_html = []
    for row in rows:
        row_html.append("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>")
    return f"<table><thead><tr>{head_html}</tr></thead><tbody>{''.join(row_html)}</tbody></table>"


def format_ms(value: float) -> str:
    return f"{value:.2f}ms"


def build_html(report: dict[str, Any]) -> str:
    metadata = report["metadata"]
    endpoints = report["endpoints"]
    findings = report["findings"]

    timing_sections: list[str] = []
    for mode in ("baseline", "scaling"):
        old = report["timings"][mode]["old"]["endpoints"]
        new = report["timings"][mode]["new"]["endpoints"]
        rows: list[list[str]] = []
        for endpoint in endpoints:
            old_runs = old[endpoint]["runs_ms"]
            new_runs = new[endpoint]["runs_ms"]
            rows.append(
                [
                    html.escape(endpoint),
                    format_ms(old[endpoint]["cold_ms"]),
                    format_ms(old[endpoint]["avg_ms"]),
                    format_ms(median(old_runs)),
                    format_ms(new[endpoint]["cold_ms"]),
                    format_ms(new[endpoint]["avg_ms"]),
                    format_ms(median(new_runs)),
                    format_ms(new[endpoint]["avg_ms"] - old[endpoint]["avg_ms"]),
                ]
            )
        timing_sections.append(
            f"<section><h2>{html.escape(mode.title())} Request Timings</h2>"
            + render_table(
                [
                    "Endpoint",
                    f"{metadata['old_branch']} cold",
                    f"{metadata['old_branch']} avg",
                    f"{metadata['old_branch']} median",
                    f"{metadata['new_branch']} cold",
                    f"{metadata['new_branch']} avg",
                    f"{metadata['new_branch']} median",
                    "Avg delta",
                ],
                rows,
            )
            + "</section>"
        )

    query_sections: list[str] = []
    for mode in ("baseline", "scaling"):
        old = report["queries"][mode]["old"]["endpoints"]
        new = report["queries"][mode]["new"]["endpoints"]
        rows = []
        for endpoint in endpoints:
            rows.append(
                [
                    html.escape(endpoint),
                    html.escape(str(old[endpoint]["query_counts"])),
                    html.escape(str(new[endpoint]["query_counts"])),
                    html.escape(str(new[endpoint]["delta_after_first"])),
                ]
            )
        query_sections.append(
            f"<section><h2>{html.escape(mode.title())} Query Counts</h2>"
            + render_table(
                [
                    "Endpoint",
                    f"{metadata['old_branch']} queries",
                    f"{metadata['new_branch']} queries",
                    f"{metadata['new_branch']} repeated delta",
                ],
                rows,
            )
            + "</section>"
        )

    concurrency_sections: list[str] = []
    for mode in ("scaling",):
        old = report["concurrency"][mode]["old"]["endpoints"]
        new = report["concurrency"][mode]["new"]["endpoints"]
        rows: list[list[str]] = []
        for endpoint in endpoints:
            rows.append(
                [
                    html.escape(endpoint),
                    format_ms(old[endpoint]["avg_ms"]),
                    format_ms(old[endpoint]["p95_ms"]),
                    html.escape(str(old[endpoint]["requests_per_second"])),
                    html.escape(f"{old[endpoint]['success_count']}/{old[endpoint]['total_requests']}"),
                    format_ms(new[endpoint]["avg_ms"]),
                    format_ms(new[endpoint]["p95_ms"]),
                    html.escape(str(new[endpoint]["requests_per_second"])),
                    html.escape(f"{new[endpoint]['success_count']}/{new[endpoint]['total_requests']}"),
                ]
            )
        concurrency_sections.append(
            f"<section><h2>{html.escape(mode.title())} Concurrent Gunicorn Load</h2>"
            + render_table(
                [
                    "Endpoint",
                    f"{metadata['old_branch']} avg",
                    f"{metadata['old_branch']} p95",
                    f"{metadata['old_branch']} req/s",
                    f"{metadata['old_branch']} ok",
                    f"{metadata['new_branch']} avg",
                    f"{metadata['new_branch']} p95",
                    f"{metadata['new_branch']} req/s",
                    f"{metadata['new_branch']} ok",
                ],
                rows,
            )
            + "</section>"
        )

    profile_sections: list[str] = []
    for mode in ("baseline", "scaling"):
        old = report["profiles"][mode]["old"]["endpoints"]
        new = report["profiles"][mode]["new"]["endpoints"]
        mode_parts = [f"<section><h2>{html.escape(mode.title())} Python Hotspots</h2>"]
        for endpoint in endpoints:
            file_deltas = top_deltas(
                old[endpoint]["top_files"],
                new[endpoint]["top_files"],
                key_fields=("file",),
                value_field="cumtime_ms",
            )
            func_deltas = top_deltas(
                old[endpoint]["top_functions"],
                new[endpoint]["top_functions"],
                key_fields=("file", "function", "line"),
                value_field="cumtime_ms",
            )
            mode_parts.append(f"<h3>{html.escape(endpoint)}</h3>")
            mode_parts.append(
                f"<p>{metadata['old_branch']}: {format_ms(old[endpoint]['elapsed_ms'])} | "
                f"{metadata['new_branch']}: {format_ms(new[endpoint]['elapsed_ms'])}</p>"
            )

            if file_deltas:
                rows = [
                    [
                        html.escape(str(row["file"])),
                        format_ms(row["old_value"]),
                        format_ms(row["new_value"]),
                        format_ms(row["delta"]),
                    ]
                    for row in file_deltas
                ]
                mode_parts.append("<h4>Top regressed files</h4>")
                mode_parts.append(render_table(["File", "Old cum", "New cum", "Delta"], rows))

            if func_deltas:
                rows = [
                    [
                        html.escape(f"{row['file']}:{row['line']}::{row['function']}"),
                        format_ms(row["old_value"]),
                        format_ms(row["new_value"]),
                        format_ms(row["delta"]),
                    ]
                    for row in func_deltas
                ]
                mode_parts.append("<h4>Top regressed functions</h4>")
                mode_parts.append(render_table(["Function", "Old cum", "New cum", "Delta"], rows))
        mode_parts.append("</section>")
        profile_sections.append("".join(mode_parts))

    finding_html = "".join(f"<li>{html.escape(item)}</li>" for item in findings) or "<li>No obvious hotspots detected.</li>"

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Performance Report</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f7f8fb;
      --card: #ffffff;
      --border: #d8deea;
      --text: #1f2a37;
      --muted: #5b6777;
      --accent: #0f766e;
      --danger: #b42318;
    }}
    body {{
      margin: 0;
      padding: 2rem;
      background: var(--bg);
      color: var(--text);
      font: 15px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    main {{
      max-width: 1200px;
      margin: 0 auto;
    }}
    h1, h2, h3, h4 {{
      margin: 0 0 0.75rem;
    }}
    section {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 1.25rem 1.5rem;
      margin-bottom: 1rem;
      box-shadow: 0 1px 2px rgba(16, 24, 40, 0.05);
    }}
    .meta {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 0.75rem;
      margin-bottom: 1rem;
    }}
    .pill {{
      display: inline-block;
      border-radius: 999px;
      background: #e6fffb;
      color: var(--accent);
      padding: 0.2rem 0.6rem;
      font-weight: 600;
      font-size: 0.9rem;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin-top: 0.5rem;
      font-size: 0.95rem;
    }}
    th, td {{
      text-align: left;
      padding: 0.6rem 0.7rem;
      border-bottom: 1px solid var(--border);
      vertical-align: top;
    }}
    th {{
      color: var(--muted);
      font-weight: 600;
    }}
    code {{
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 0.92em;
    }}
    ul {{
      margin: 0.5rem 0 0;
      padding-left: 1.2rem;
    }}
    .muted {{
      color: var(--muted);
    }}
  </style>
</head>
<body>
  <main>
    <section>
      <h1>Branch Performance Report</h1>
      <p class="muted">Generated {html.escape(metadata['generated_at'])}</p>
      <div class="meta">
        <div><strong>Old branch</strong><br><span class="pill">{html.escape(metadata['old_branch'])}</span></div>
        <div><strong>New branch</strong><br><span class="pill">{html.escape(metadata['new_branch'])}</span></div>
        <div><strong>Database</strong><br><code>{html.escape(metadata['shared_database_url'])}</code></div>
        <div><strong>Endpoints</strong><br><code>{html.escape(', '.join(endpoints))}</code></div>
      </div>
    </section>

    <section>
      <h2>Key Findings</h2>
      <ul>{finding_html}</ul>
    </section>

    {''.join(timing_sections)}
    {''.join(query_sections)}
    {''.join(concurrency_sections)}
    {''.join(profile_sections)}
  </main>
</body>
</html>
"""


def main() -> int:
    args = parse_args()
    output_dir = (REPO_ROOT / args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    old_branch = os.environ.get("OLD_BRANCH", "feature/render_deploy")
    new_branch = os.environ.get("NEW_BRANCH", "feature/scaling")
    shared_database_url = require_env("SHARED_DATABASE_URL")
    old_redis_url = require_env("OLD_REDIS_URL")
    new_redis_url = require_env("NEW_REDIS_URL")

    base_env = os.environ.copy()
    base_env.update(
        {
            "OLD_BRANCH": old_branch,
            "NEW_BRANCH": new_branch,
            "ENDPOINTS": args.endpoints,
            "SHARED_DATABASE_URL": shared_database_url,
            "OLD_REDIS_URL": old_redis_url,
            "NEW_REDIS_URL": new_redis_url,
        }
    )

    raw_outputs: dict[str, str] = {}
    report: dict[str, Any] = {
        "metadata": {
            "generated_at": dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds"),
            "old_branch": old_branch,
            "new_branch": new_branch,
            "shared_database_url": mask_url(shared_database_url),
        },
        "endpoints": [item.strip() for item in args.endpoints.split(",") if item.strip()],
        "timings": {},
        "queries": {},
        "concurrency": {},
        "profiles": {},
    }

    # Timings.
    timing_env = dict(base_env)
    timing_env["RUNS"] = str(args.runs)

    raw_outputs["timings_baseline"], paths = run_script("compare_branch_perf.sh", {**timing_env, "MODE": "baseline"})
    report["timings"]["baseline"] = {"old": load_json(paths[0]), "new": load_json(paths[1])}

    flush_redis_db(old_redis_url)
    flush_redis_db(new_redis_url)
    raw_outputs["timings_scaling"], paths = run_script("compare_branch_perf.sh", {**timing_env, "MODE": "scaling"})
    report["timings"]["scaling"] = {"old": load_json(paths[0]), "new": load_json(paths[1])}

    # Query counts.
    query_env = dict(base_env)
    query_env["REQUESTS_PER_ENDPOINT"] = str(args.query_requests)
    raw_outputs["queries_baseline"], paths = run_script(
        "compare_branch_queries.sh", {**query_env, "MODE": "baseline"}
    )
    report["queries"]["baseline"] = {"old": load_json(paths[0]), "new": load_json(paths[1])}

    flush_redis_db(old_redis_url)
    flush_redis_db(new_redis_url)
    raw_outputs["queries_scaling"], paths = run_script("compare_branch_queries.sh", {**query_env, "MODE": "scaling"})
    report["queries"]["scaling"] = {"old": load_json(paths[0]), "new": load_json(paths[1])}

    # Concurrent Gunicorn load.
    concurrency_env = dict(base_env)
    concurrency_env["CONCURRENT_REQUESTS"] = str(args.concurrent_requests)
    concurrency_env["CONCURRENCY"] = str(args.concurrency)
    concurrency_env["GUNICORN_WORKERS"] = str(args.gunicorn_workers)
    concurrency_env["WARMUP_REQUESTS"] = str(args.concurrent_warmup_requests)

    flush_redis_db(old_redis_url)
    flush_redis_db(new_redis_url)
    raw_outputs["concurrency_scaling"], paths = run_script(
        "compare_branch_concurrency.sh", {**concurrency_env, "MODE": "scaling"}
    )
    report["concurrency"]["scaling"] = {"old": load_json(paths[0]), "new": load_json(paths[1])}

    # Python hotspots.
    profile_env = dict(base_env)
    profile_env["PROFILE_WARMUP_REQUESTS"] = str(args.profile_warmup_requests)
    profile_env["TOP_N"] = str(args.top_profile_rows)
    raw_outputs["profiles_baseline"], paths = run_script(
        "compare_branch_profiles.sh", {**profile_env, "MODE": "baseline"}
    )
    report["profiles"]["baseline"] = {"old": load_json(paths[0]), "new": load_json(paths[1])}

    flush_redis_db(old_redis_url)
    flush_redis_db(new_redis_url)
    raw_outputs["profiles_scaling"], paths = run_script(
        "compare_branch_profiles.sh", {**profile_env, "MODE": "scaling"}
    )
    report["profiles"]["scaling"] = {"old": load_json(paths[0]), "new": load_json(paths[1])}

    report["findings"] = build_findings(report)

    report_json = output_dir / "report.json"
    report_html = output_dir / "report.html"
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(exist_ok=True)

    report_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    report_html.write_text(build_html(report), encoding="utf-8")
    for name, text in raw_outputs.items():
        (raw_dir / f"{name}.txt").write_text(text + "\n", encoding="utf-8")

    print(f"Performance report written to {report_html}")
    print(f"Structured JSON written to {report_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
