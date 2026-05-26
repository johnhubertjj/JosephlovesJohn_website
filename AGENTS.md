# AGENTS.md

Guidance for Codex and other coding agents working in this repository.

## Project Overview

This is the production Django codebase for the JosephlovesJohn website. It contains:

- `main_site/`: the main artist site, legal pages, contact flow, and admin-managed content.
- `shop/`: products, cart, checkout, Stripe integration, accounts, orders, and downloads.
- `mastering/`: the John Joseph Mastering microsite at `/mastering-services/`.
- `josephlovesjohn_site/`: Django settings, root URLs, storage, CSP, rate limits, SEO, and shared runtime helpers.
- `templates/`: Django templates for the main site, shop, and mastering microsite.
- `static/`: tracked CSS, JS, media, theme files, and optimized site assets.
- `tests/`: pytest, smoke, integration, SEO, accessibility, and browser-oriented coverage.

Useful orientation docs:

- `README.md`
- `docs/repository-architecture.md`
- `docs/shop-flow.md`
- `docs/deployment.md`
- `docs/cloudflare_r2.md`
- `docs/performance_reports.md`

## Development Commands

Use `uv` for all Python commands.

```bash
uv sync --dev
uv run python manage.py migrate
uv run python manage.py runserver
uv run pytest -q
uv run pytest -q tests/test_main_site_smoke.py tests/test_mastering_smoke.py
uv run python manage.py check
uv run ruff check
uv run mypy
```

Notes:

- Local development defaults to SQLite when `DATABASE_URL` is unset.
- `.env` is auto-loaded from the repo root for local development.
- Ruff excludes migrations, templates, static files, and the bundled HTML5 UP source.
- If running browser/UI tests, check the test markers and existing browser-test conventions first.

## Working Style

- Read the existing view, template, static asset, and test patterns before editing.
- Keep changes scoped. This is a live application, not a starter template.
- Do not revert unrelated local changes. The worktree is often intentionally dirty during active design iterations.
- Prefer `rg` / `rg --files` for searching.
- Use focused tests that match the files changed, then broaden only when the change touches shared behavior.
- When changing user-facing pages, visually verify the relevant route when practical.
- Stop any local dev server you start before finishing.

## App Boundaries

### Main Site

Start with:

- `main_site/views.py`
- `main_site/site_data.py`
- `templates/main_site/site.html`
- `templates/main_site/includes/sections/`
- `static/main_site/js/site.js`
- `static/main_site/css/site.css`

The main artist site is mostly a one-page shell. Django chooses the initial active section; browser JavaScript handles section transitions and enhancements.

### Shop

Start with:

- `shop/models.py`
- `shop/views.py`
- `shop/cart.py`
- `shop/stripe.py`
- `shop/downloads.py`
- `templates/shop/`
- `docs/shop-flow.md`

Checkout uses Stripe-hosted Checkout. Order/download entitlement logic belongs in Django, and private paid files may be served through short-lived signed URLs.

### Mastering Microsite

Start with:

- `mastering/views.py`
- `mastering/urls.py`
- `templates/mastering/home.html`
- `templates/mastering/subfolder.html`
- `static/mastering/`
- `tests/test_mastering_smoke.py`
- `tests/test_mastering_routes.py`

The mastering page is based on the HTML5 UP Solid State theme but has page-specific inline CSS in `templates/mastering/home.html`. Recent design work uses local optimized images under `static/mastering/images/`.

## Frontend And Design Notes

- Match the existing HTML5 UP/Solid State structure unless there is a clear reason to diverge.
- Keep operational/shop UI calm and usable. Avoid marketing-only layouts where the user needs an actual workflow.
- For the mastering page, preserve the dark studio aesthetic, strong album-art imagery, and compact cards.
- Check mobile and desktop layouts for text overflow, fixed-header overlap, and awkward cropped imagery.
- Prefer existing libraries and bundled assets over adding new frontend dependencies.
- Do not place card-like components inside other cards unless the existing template already does so.
- For local media/image updates, keep assets optimized and store them in the relevant `static/.../images/` folder.

## Tests To Update

Common mappings:

- Main site text, navigation, or route changes: `tests/test_main_site_smoke.py`, `tests/test_main_site_routes.py`, `tests/test_main_site_integration.py`.
- Mastering page changes: `tests/test_mastering_smoke.py`, `tests/test_mastering_routes.py`.
- SEO/meta/canonical changes: `tests/test_seo.py`.
- Shop/cart/checkout changes: `tests/test_shop_flow.py`, `tests/test_browser_quality.py` where relevant.
- Settings/CSP/security changes: `tests/test_settings_config.py`, `tests/test_content_security_policy.py`.
- Asset helper changes: `tests/test_asset_urls.py`, `tests/test_static_asset_regressions.py`.

Use the narrowest useful test command first. For example:

```bash
uv run pytest -q tests/test_mastering_smoke.py tests/test_mastering_routes.py
```

## Assets And Media

- Repo-tracked static assets live in `static/`.
- Generated `staticfiles/` output should not be committed.
- Large public media may be backed by Cloudflare R2 using `PUBLIC_ASSET_BASE_URL`.
- Uploaded admin media can use local storage or S3-compatible storage.
- Paid downloads can use private R2 storage with signed URLs.
- Keep relative asset keys stable when moving files to R2, for example `audio/...` or `images/...`.

## Security And Production Concerns

- Do not hard-code secrets, API keys, Stripe keys, SMTP credentials, or private bucket credentials.
- Production deploys on Render with WhiteNoise, Gunicorn, Postgres, and optional Redis/R2.
- Stripe webhook behavior and paid-download access are high-risk; update tests when touching them.
- Be careful with CSP, analytics, embeds, and iframes. Check `josephlovesjohn_site/csp.py` and CSP tests if adding third-party origins.
- Contact, login, registration, and checkout flows may use reCAPTCHA, rate limiting, sessions, email, and external services.

## Current Design Gotchas

- The main site and mastering microsite are separate experiences; do not assume navigation text or branding should match everywhere.
- The mastering nav currently points back to the artist page with the label `Josephlovesjohn - Artist page`.
- The mastering hero uses `static/mastering/images/mastering-website-header-image.jpg` and a circular profile image.
- SoundCloud short links may need to be resolved to canonical `soundcloud.com/...` URLs for iframe embeds.
- If adding external embeds, retain a normal external link as a fallback.
- Mobile fixed headers can overlap anchor targets; use `scroll-margin-top` or section padding where needed.

## Before Finishing

1. Confirm the changed files are the intended scope.
2. Run focused tests and mention the exact command/result.
3. For UI work, visually check the changed page when practical.
4. Stop any dev server started for verification.
5. Summarize only the meaningful changes and any remaining caveats.
