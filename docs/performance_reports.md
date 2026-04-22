## Performance Reports

Use the combined report script to compare request timings, query counts, and Python-side hotspots between two branches.

### Local usage

With Postgres and Redis running locally:

```bash
SHARED_DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@127.0.0.1:5432/jlj_bench \
OLD_REDIS_URL=redis://127.0.0.1:6379/1 \
NEW_REDIS_URL=redis://127.0.0.1:6379/2 \
python3 scripts/generate_perf_report.py --output-dir perf-report
```

The script writes:

- `perf-report/report.html`
- `perf-report/report.json`
- `perf-report/raw/*.txt`

### What the report contains

- **Baseline timings**: repeated local request timings without Redis-backed caching.
- **Scaling timings**: repeated local request timings with the cache/session settings enabled.
- **Query counts**: DB queries for repeated requests to the same route.
- **Concurrent Gunicorn load**: realistic multi-request route benchmarks using a production-style app server.
- **Python hotspots**: cProfile summaries of the slowest application files/functions on the profiled request path.

### Important limits

- The timing sections measure **server-side request handling**, not browser animation smoothness.
- The hotspot sections measure **Python execution time**, not paint/compositing/image decode costs in the browser.
- The CI workflow benchmarks on seeded migration data. For highly custom content, a local report using your real benchmark DB is more representative.

### Concurrent load testing

Use concurrent load tests when you want to know whether the scaling branch behaves better under pressure, not just on one request at a time.

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
