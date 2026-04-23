## Performance Reports

Use the combined report script to compare request timings, query counts, Python-side hotspots, and charts between any two git refs.

### Local usage

With Postgres and Redis running locally:

```bash
OLD_REF=feature/render_deploy \
NEW_REF=feature/scaling \
OLD_LABEL=render_deploy \
NEW_LABEL=scaling \
SHARED_DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@127.0.0.1:5432/jlj_bench \
OLD_REDIS_URL=redis://127.0.0.1:6379/1 \
NEW_REDIS_URL=redis://127.0.0.1:6379/2 \
python3 scripts/generate_perf_report.py --output-dir perf-report
```

`OLD_REF` and `NEW_REF` can be:

- branch names
- tags
- commit SHAs

Example comparing two commits directly:

```bash
OLD_REF=877ca75b \
NEW_REF=6ae8b92 \
OLD_LABEL=before \
NEW_LABEL=after \
SHARED_DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@127.0.0.1:5432/jlj_bench \
OLD_REDIS_URL=redis://127.0.0.1:6379/1 \
NEW_REDIS_URL=redis://127.0.0.1:6379/2 \
python3 scripts/generate_perf_report.py --output-dir perf-report-compare
```

If you omit `OLD_LABEL` and `NEW_LABEL`, the report uses the refs themselves as labels.

The script writes:

- `perf-report/report.html`
- `perf-report/report.json`
- `perf-report/raw/*.txt`

### What the report contains

- **Baseline timings**: repeated local request timings without Redis-backed caching.
- **Scaling timings**: repeated local request timings with the cache/session settings enabled.
- **Query counts**: DB queries for repeated requests to the same route.
- **Concurrent Gunicorn load**:
  - fresh-cache burst medians
  - warm steady-state medians after full endpoint prewarm cycles
  - both measured in a production-style `DEBUG=false` setup with manifest-collected static files
- **Python hotspots**: cProfile summaries of the slowest application files/functions on the profiled request path.
- **Inline plots**: endpoint charts for request timings, repeated query counts, and concurrent load throughput/latency.

### Full comparison runthrough

1. Choose the two refs you want to compare.
2. Make sure both refs can use the same database shape.
3. Start Postgres and Redis locally.
4. Pick two separate Redis DBs so caches do not overlap.
5. Run the combined report with `OLD_REF`, `NEW_REF`, `OLD_LABEL`, and `NEW_LABEL`.
6. Open the generated `report.html`.
7. Use the matching `report.json` and `raw/*.txt` files if you want to inspect exact script output.

Recommended command skeleton:

```bash
OLD_REF=<old-ref> \
NEW_REF=<new-ref> \
OLD_LABEL=<old-label> \
NEW_LABEL=<new-label> \
SHARED_DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@127.0.0.1:5432/jlj_bench \
OLD_REDIS_URL=redis://127.0.0.1:6379/1 \
NEW_REDIS_URL=redis://127.0.0.1:6379/2 \
python3 scripts/generate_perf_report.py --output-dir perf-report
```

Useful knobs:

- `--runs 20` for more stable request timing samples
- `--query-requests 3` to see more than one repeated request
- `--profile-warmup-requests 2` to reduce cold-start noise in Python hotspots
- `--concurrent-requests 400` and `--concurrency 40` for a heavier Gunicorn load check
- `--concurrency-runs 7` if you want concurrency medians across more repeated runs
- `--endpoints /,/music/,/art/,/contact/` to include more routes

### Important limits

- The timing sections measure **server-side request handling**, not browser animation smoothness.
- The hotspot sections measure **Python execution time**, not paint/compositing/image decode costs in the browser.
- The CI workflow benchmarks on seeded migration data. For highly custom content, a local report using your real benchmark DB is more representative.

### Concurrent load testing

Use concurrent load tests when you want to know whether the scaling branch behaves better under pressure, not just on one request at a time.

The combined report now runs the concurrent Gunicorn step multiple times and charts the **median** latency/throughput per endpoint for two states:

- `fresh-cache burst`: flush Redis, start Gunicorn, do minimal route warmup, then measure
- `warm steady-state`: flush Redis, start Gunicorn, prewarm all benchmark endpoints for several full cycles, then measure

Those Gunicorn runs use a production-style benchmark setup:

- `DEBUG=false`
- manifest static files collected into temporary static roots for each ref
- no debug-only static finder/autorefresh behavior

That makes one-off local outliers much less likely to distort the report and helps separate cache-fill cost from genuinely warm steady-state behavior.

#### Recommended local setup

Do **not** use Django's `runserver` for serious concurrency measurements. It is a development server and can drop connections under load, which shows up as `connection reset by peer`.

Use Gunicorn instead:

```bash
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@127.0.0.1:5432/jlj_bench \
SITE_CONTENT_CACHE_TTL=300 \
CART_SUMMARY_CACHE_TTL=60 \
REDIS_URL=redis://127.0.0.1:6379/1 \
uv run gunicorn josephlovesjohn_site.wsgi:application --bind 127.0.0.1:8000 --workers 4
```

Run the comparison branch on another port with a different Redis DB:

```bash
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@127.0.0.1:5432/jlj_bench \
SITE_CONTENT_CACHE_TTL=300 \
CART_SUMMARY_CACHE_TTL=60 \
REDIS_URL=redis://127.0.0.1:6379/2 \
uv run gunicorn josephlovesjohn_site.wsgi:application --bind 127.0.0.1:8001 --workers 4
```

Flush Redis before each comparison if you want a clean warmup cycle:

```bash
redis-cli -n 1 FLUSHDB
redis-cli -n 2 FLUSHDB
```

Warm each route once before load testing:

```bash
curl -s http://127.0.0.1:8000/ > /dev/null
curl -s http://127.0.0.1:8001/ > /dev/null
```

Then use `hey`:

```bash
hey -n 200 -c 20 http://127.0.0.1:8000/
hey -n 200 -c 20 http://127.0.0.1:8001/
```

Repeat the same pattern for:

- `/music/`
- `/art/`

What to compare:

- average latency
- p95 / p99 latency
- requests per second
- failed requests

#### Reading local `hey` results

If you see a lot of `connection reset by peer` while using `runserver`, treat that as a **dev-server limitation**, not an application scalability conclusion.

### Remote or preview deployment comparisons

Use a remote comparison when you want a more production-like answer than localhost can provide.

#### Recommended workflow

1. Deploy the older branch to one preview or dev environment.
2. Deploy the newer branch to another preview or dev environment.
3. Make sure both use the same kind of backing services:
   - same Postgres plan/region
   - same Redis plan/region
   - same Gunicorn worker shape
4. Use the same benchmark routes on both deployments:
   - `/`
   - `/music/`
   - `/art/`
5. Warm the routes once, then run `hey` against the public URLs.

Example:

```bash
hey -n 200 -c 20 https://old-preview.example.com/
hey -n 200 -c 20 https://new-preview.example.com/
```

And:

```bash
hey -n 200 -c 20 https://old-preview.example.com/music/
hey -n 200 -c 20 https://new-preview.example.com/music/
```

#### Why remote can help

A remote comparison is closer to the real deployment shape because it includes:

- Gunicorn rather than the Django dev server
- real network overhead
- production-like Postgres and Redis behavior
- static asset delivery closer to the live site

#### What remote still does not tell you

Remote load tests still do **not** measure browser animation smoothness. For frontend motion issues, keep using browser traces or Lighthouse/Web Inspector recordings separately.
