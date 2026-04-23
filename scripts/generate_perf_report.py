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
    parser.add_argument(
        "--concurrency-runs",
        type=int,
        default=5,
        help="Repeated Gunicorn concurrency runs to aggregate with medians.",
    )
    parser.add_argument(
        "--steady-state-warmup-rounds",
        type=int,
        default=5,
        help="Full endpoint warmup cycles before the steady-state concurrency benchmark.",
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
    old_label = report["metadata"]["old_label"]
    new_label = report["metadata"]["new_label"]

    baseline_timing = report["timings"]["baseline"]
    scaling_timing = report["timings"]["scaling"]
    baseline_queries = report["queries"]["baseline"]
    scaling_queries = report["queries"]["scaling"]
    concurrency_fresh = report["concurrency"]["fresh"]
    concurrency_warm = report["concurrency"]["warm"]

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
                f"`{endpoint}` reaches a zero-query warm path on `{new_label}`, "
                f"but its warm request time is still {scaling_timing_delta:.2f}ms slower than `{old_label}` locally."
            )

        if base_timing_delta > 0.75:
            findings.append(
                f"`{endpoint}` shows a steady uncached overhead on `{new_label}` "
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
                f"`{endpoint}` only reduces repeated DB work on `{new_label}`; "
                f"`{old_label}` continues issuing the same queries on repeated requests."
            )

        concurrency_old_fresh = concurrency_fresh["old"]["endpoints"][endpoint]
        concurrency_new_fresh = concurrency_fresh["new"]["endpoints"][endpoint]
        concurrency_old_warm = concurrency_warm["old"]["endpoints"][endpoint]
        concurrency_new_warm = concurrency_warm["new"]["endpoints"][endpoint]
        if (
            concurrency_new_fresh["success_count"] == concurrency_new_fresh["total_requests"]
            and concurrency_old_fresh["success_count"] == concurrency_old_fresh["total_requests"]
            and concurrency_new_fresh["avg_ms"] < concurrency_old_fresh["avg_ms"] * 0.75
        ):
            findings.append(
                f"Under fresh-cache concurrent Gunicorn load, `{endpoint}` improves from "
                f"{concurrency_old_fresh['avg_ms']:.2f}ms avg / {concurrency_old_fresh['requests_per_second']:.1f} req/s "
                f"to {concurrency_new_fresh['avg_ms']:.2f}ms avg / {concurrency_new_fresh['requests_per_second']:.1f} req/s "
                f"on `{new_label}`."
            )

        if (
            concurrency_new_warm["success_count"] == concurrency_new_warm["total_requests"]
            and concurrency_old_warm["success_count"] == concurrency_old_warm["total_requests"]
            and concurrency_new_warm["avg_ms"] < concurrency_old_warm["avg_ms"] * 0.75
        ):
            findings.append(
                f"Under warm steady-state Gunicorn load, `{endpoint}` improves from "
                f"{concurrency_old_warm['avg_ms']:.2f}ms avg / {concurrency_old_warm['requests_per_second']:.1f} req/s "
                f"to {concurrency_new_warm['avg_ms']:.2f}ms avg / {concurrency_new_warm['requests_per_second']:.1f} req/s "
                f"on `{new_label}`."
            )

        if (
            concurrency_new_fresh["avg_ms"] > concurrency_old_fresh["avg_ms"]
            and concurrency_new_warm["avg_ms"] < concurrency_new_fresh["avg_ms"] * 0.9
        ):
            findings.append(
                f"`{endpoint}` is notably better on `{new_label}` after a deeper warmup than on a fresh-cache burst, "
                f"suggesting its cache path pays off after initial shared payloads are populated."
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


def format_req_per_sec(value: float) -> str:
    return f"{value:.1f} req/s"


def format_range(values: list[float], formatter) -> str:
    if not values:
        return "n/a"
    low = min(values)
    high = max(values)
    if abs(high - low) < 1e-9:
        return formatter(low)
    return f"{formatter(low)} - {formatter(high)}"


def render_bar_chart(
    title: str,
    *,
    endpoints: list[str],
    old_values: list[float],
    new_values: list[float],
    old_label: str,
    new_label: str,
    value_formatter,
    max_value: float | None = None,
) -> str:
    width = 860
    height = 300
    margin_left = 56
    margin_right = 24
    margin_top = 24
    margin_bottom = 56
    plot_width = width - margin_left - margin_right
    plot_height = height - margin_top - margin_bottom
    group_width = plot_width / max(len(endpoints), 1)
    bar_width = min(40.0, group_width * 0.3)
    gap = bar_width * 0.35
    scale_max = max_value or max(old_values + new_values + [1.0])

    def bar_height(value: float) -> float:
        return (value / scale_max) * plot_height if scale_max else 0.0

    elements: list[str] = [
        f'<line x1="{margin_left}" y1="{margin_top + plot_height}" x2="{margin_left + plot_width}" y2="{margin_top + plot_height}" stroke="#cbd5e1" stroke-width="1" />',
        f'<line x1="{margin_left}" y1="{margin_top}" x2="{margin_left}" y2="{margin_top + plot_height}" stroke="#cbd5e1" stroke-width="1" />',
    ]

    ticks = 4
    for tick in range(ticks + 1):
        value = scale_max * tick / ticks
        y = margin_top + plot_height - (plot_height * tick / ticks)
        elements.append(
            f'<line x1="{margin_left}" y1="{y:.2f}" x2="{margin_left + plot_width}" y2="{y:.2f}" stroke="#e5e7eb" stroke-width="1" />'
        )
        elements.append(
            f'<text x="{margin_left - 8}" y="{y + 4:.2f}" text-anchor="end" font-size="11" fill="#667085">{html.escape(value_formatter(value))}</text>'
        )

    for index, endpoint in enumerate(endpoints):
        group_x = margin_left + index * group_width + group_width / 2
        old_height = bar_height(old_values[index])
        new_height = bar_height(new_values[index])
        old_x = group_x - bar_width - gap / 2
        new_x = group_x + gap / 2
        old_y = margin_top + plot_height - old_height
        new_y = margin_top + plot_height - new_height
        label_y = margin_top + plot_height + 18

        elements.append(
            f'<rect x="{old_x:.2f}" y="{old_y:.2f}" width="{bar_width:.2f}" height="{old_height:.2f}" rx="4" fill="#94a3b8" />'
        )
        elements.append(
            f'<rect x="{new_x:.2f}" y="{new_y:.2f}" width="{bar_width:.2f}" height="{new_height:.2f}" rx="4" fill="#0f766e" />'
        )
        elements.append(
            f'<text x="{old_x + bar_width / 2:.2f}" y="{old_y - 6:.2f}" text-anchor="middle" font-size="11" fill="#475467">{html.escape(value_formatter(old_values[index]))}</text>'
        )
        elements.append(
            f'<text x="{new_x + bar_width / 2:.2f}" y="{new_y - 6:.2f}" text-anchor="middle" font-size="11" fill="#0f766e">{html.escape(value_formatter(new_values[index]))}</text>'
        )
        elements.append(
            f'<text x="{group_x:.2f}" y="{label_y:.2f}" text-anchor="middle" font-size="12" fill="#475467">{html.escape(endpoint)}</text>'
        )

    legend_y = height - 16
    elements.extend(
        [
            f'<rect x="{margin_left}" y="{legend_y - 10}" width="12" height="12" rx="3" fill="#94a3b8" />',
            f'<text x="{margin_left + 18}" y="{legend_y}" font-size="12" fill="#475467">{html.escape(old_label)}</text>',
            f'<rect x="{margin_left + 160}" y="{legend_y - 10}" width="12" height="12" rx="3" fill="#0f766e" />',
            f'<text x="{margin_left + 178}" y="{legend_y}" font-size="12" fill="#475467">{html.escape(new_label)}</text>',
        ]
    )

    return (
        '<div class="chart-card">'
        f"<h3>{html.escape(title)}</h3>"
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{html.escape(title)}">'
        + "".join(elements)
        + "</svg></div>"
    )


def build_html(report: dict[str, Any]) -> str:
    metadata = report["metadata"]
    endpoints = report["endpoints"]
    findings = report["findings"]
    old_label = metadata["old_label"]
    new_label = metadata["new_label"]

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
        chart = render_bar_chart(
            f"{mode.title()} average request times",
            endpoints=endpoints,
            old_values=[old[endpoint]["avg_ms"] for endpoint in endpoints],
            new_values=[new[endpoint]["avg_ms"] for endpoint in endpoints],
            old_label=old_label,
            new_label=new_label,
            value_formatter=format_ms,
        )
        timing_sections.append(
            f"<section><h2>{html.escape(mode.title())} Request Timings</h2>"
            + chart
            + render_table(
                [
                    "Endpoint",
                    f"{old_label} cold",
                    f"{old_label} avg",
                    f"{old_label} median",
                    f"{new_label} cold",
                    f"{new_label} avg",
                    f"{new_label} median",
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
        chart = render_bar_chart(
            f"{mode.title()} repeated request query counts",
            endpoints=endpoints,
            old_values=[float(old[endpoint]["query_counts"][-1]) for endpoint in endpoints],
            new_values=[float(new[endpoint]["query_counts"][-1]) for endpoint in endpoints],
            old_label=old_label,
            new_label=new_label,
            value_formatter=lambda value: str(int(round(value))),
            max_value=max(
                [
                    float(old[endpoint]["query_counts"][0])
                    for endpoint in endpoints
                ]
                + [float(new[endpoint]["query_counts"][0]) for endpoint in endpoints]
                + [1.0]
            ),
        )
        query_sections.append(
            f"<section><h2>{html.escape(mode.title())} Query Counts</h2>"
            + chart
            + render_table(
                [
                    "Endpoint",
                    f"{old_label} queries",
                    f"{new_label} queries",
                    f"{new_label} repeated delta",
                ],
                rows,
            )
            + "</section>"
        )

    concurrency_sections: list[str] = []
    concurrency_modes = (
        ("fresh", "Fresh-cache burst"),
        ("warm", "Warm steady-state"),
    )
    for mode_key, mode_title in concurrency_modes:
        old = report["concurrency"][mode_key]["old"]["endpoints"]
        new = report["concurrency"][mode_key]["new"]["endpoints"]
        concurrency_runs = report["concurrency"][mode_key]["old"].get("run_count", 1)
        warmup_rounds = report["concurrency"][mode_key]["old"].get("steady_state_warmup_rounds", 0)
        rows: list[list[str]] = []
        for endpoint in endpoints:
            old_runs = old[endpoint].get("runs", [])
            new_runs = new[endpoint].get("runs", [])
            rows.append(
                [
                    html.escape(endpoint),
                    format_ms(old[endpoint]["avg_ms"]),
                    format_ms(old[endpoint]["p95_ms"]),
                    html.escape(str(old[endpoint]["requests_per_second"])),
                    html.escape(format_range([float(run["avg_ms"]) for run in old_runs], format_ms)),
                    html.escape(f"{old[endpoint]['success_count']}/{old[endpoint]['total_requests']}"),
                    format_ms(new[endpoint]["avg_ms"]),
                    format_ms(new[endpoint]["p95_ms"]),
                    html.escape(str(new[endpoint]["requests_per_second"])),
                    html.escape(format_range([float(run["avg_ms"]) for run in new_runs], format_ms)),
                    html.escape(f"{new[endpoint]['success_count']}/{new[endpoint]['total_requests']}"),
                ]
            )
        avg_chart = render_bar_chart(
            f"{mode_title} average latency",
            endpoints=endpoints,
            old_values=[old[endpoint]["avg_ms"] for endpoint in endpoints],
            new_values=[new[endpoint]["avg_ms"] for endpoint in endpoints],
            old_label=old_label,
            new_label=new_label,
            value_formatter=format_ms,
        )
        throughput_chart = render_bar_chart(
            f"{mode_title} throughput",
            endpoints=endpoints,
            old_values=[old[endpoint]["requests_per_second"] for endpoint in endpoints],
            new_values=[new[endpoint]["requests_per_second"] for endpoint in endpoints],
            old_label=old_label,
            new_label=new_label,
            value_formatter=format_req_per_sec,
        )
        note = f"Latency and throughput charts below use medians across {concurrency_runs} repeated run(s)."
        if mode_key == "warm":
            note += f" Each run prewarms all benchmark endpoints for {warmup_rounds} full cycle(s) before timing."
        concurrency_sections.append(
            f"<section><h2>{html.escape(mode_title)} Concurrent Gunicorn Load</h2>"
            f"<p class=\"muted\">{html.escape(note)}</p>"
            + avg_chart
            + throughput_chart
            + render_table(
                [
                    "Endpoint",
                    f"{old_label} avg (med)",
                    f"{old_label} p95 (med)",
                    f"{old_label} req/s (med)",
                    f"{old_label} avg range",
                    f"{old_label} ok",
                    f"{new_label} avg (med)",
                    f"{new_label} p95 (med)",
                    f"{new_label} req/s (med)",
                    f"{new_label} avg range",
                    f"{new_label} ok",
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
            mode_parts.append(f"<p>{old_label}: {format_ms(old[endpoint]['elapsed_ms'])} | {new_label}: {format_ms(new[endpoint]['elapsed_ms'])}</p>")

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
    .chart-card {{
      margin: 0.75rem 0 1.2rem;
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 0.9rem;
      background: #fcfcfd;
    }}
    .chart-card h3 {{
      margin-bottom: 0.35rem;
      font-size: 1rem;
    }}
    svg {{
      width: 100%;
      height: auto;
      display: block;
    }}
  </style>
</head>
<body>
  <main>
    <section>
      <h1>Branch Performance Report</h1>
      <p class="muted">Generated {html.escape(metadata['generated_at'])}</p>
      <div class="meta">
        <div><strong>Old ref</strong><br><span class="pill">{html.escape(metadata['old_label'])}</span><br><code>{html.escape(metadata['old_ref'])}</code></div>
        <div><strong>New ref</strong><br><span class="pill">{html.escape(metadata['new_label'])}</span><br><code>{html.escape(metadata['new_ref'])}</code></div>
        <div><strong>Database</strong><br><code>{html.escape(metadata['shared_database_url'])}</code></div>
        <div><strong>Endpoints</strong><br><code>{html.escape(', '.join(endpoints))}</code></div>
        <div><strong>Concurrency runs</strong><br><code>{html.escape(str(metadata['concurrency_runs']))}</code></div>
        <div><strong>Steady-state warmup cycles</strong><br><code>{html.escape(str(metadata['steady_state_warmup_rounds']))}</code></div>
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

    old_ref = os.environ.get("OLD_REF") or os.environ.get("OLD_BRANCH", "feature/render_deploy")
    new_ref = os.environ.get("NEW_REF") or os.environ.get("NEW_BRANCH", "feature/scaling")
    old_label = os.environ.get("OLD_LABEL", old_ref)
    new_label = os.environ.get("NEW_LABEL", new_ref)
    shared_database_url = require_env("SHARED_DATABASE_URL")
    old_redis_url = require_env("OLD_REDIS_URL")
    new_redis_url = require_env("NEW_REDIS_URL")

    base_env = os.environ.copy()
    base_env.update(
        {
            "OLD_REF": old_ref,
            "NEW_REF": new_ref,
            "OLD_LABEL": old_label,
            "NEW_LABEL": new_label,
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
            "old_ref": old_ref,
            "new_ref": new_ref,
            "old_label": old_label,
            "new_label": new_label,
            "shared_database_url": mask_url(shared_database_url),
            "concurrency_runs": args.concurrency_runs,
            "steady_state_warmup_rounds": args.steady_state_warmup_rounds,
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
    concurrency_env["CONCURRENCY_RUNS"] = str(args.concurrency_runs)
    concurrency_env["STEADY_STATE_WARMUP_ROUNDS"] = str(args.steady_state_warmup_rounds)

    flush_redis_db(old_redis_url)
    flush_redis_db(new_redis_url)
    raw_outputs["concurrency_fresh"], paths = run_script(
        "compare_branch_concurrency.sh", {**concurrency_env, "MODE": "scaling", "CACHE_STATE": "fresh"}
    )
    report["concurrency"]["fresh"] = {"old": load_json(paths[0]), "new": load_json(paths[1])}

    flush_redis_db(old_redis_url)
    flush_redis_db(new_redis_url)
    raw_outputs["concurrency_warm"], paths = run_script(
        "compare_branch_concurrency.sh", {**concurrency_env, "MODE": "scaling", "CACHE_STATE": "warm"}
    )
    report["concurrency"]["warm"] = {"old": load_json(paths[0]), "new": load_json(paths[1])}

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
