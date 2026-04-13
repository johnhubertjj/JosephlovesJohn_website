# Render Deployment Notes

This document covers the main site and shop deployment only. The mastering site remains in the same Django service, but its UI entry point can stay hidden.

## Recommended Production Shape

Deploy on Render as:

- 1 web service for Django
- 1 managed Postgres database
- 1 persistent disk mounted at `/opt/render/project/src/media`

Current app behavior matches that setup:

- static files are served with WhiteNoise
- uploaded media stays on the filesystem
- local development still falls back to SQLite when `DATABASE_URL` is unset
- production should use Postgres through `DATABASE_URL`

## Prerequisites

- Repo pushed to GitHub, GitLab, or Bitbucket
- Production domain ready
- Stripe live credentials ready
- Gmail app password or another SMTP credential ready
- Render account with access to paid services if using a persistent disk

## Render Service Configuration

### Web service

Create a Render **Web Service** from this repo with:

- Runtime: Python
- Branch: your production branch
- Root directory: repo root
- Auto deploy: On Commit

Use these commands:

```bash
# Build Command
uv sync --frozen && uv run python manage.py collectstatic --noinput && uv run python manage.py check --deploy

# Pre-Deploy Command
uv run python manage.py migrate --noinput

# Start Command
uv run gunicorn josephlovesjohn_site.wsgi:application --bind 0.0.0.0:$PORT
```

### Persistent disk

Attach a Render **Persistent Disk** to the web service:

- Mount path: `/opt/render/project/src/media`
- Start with the smallest practical size

Notes:

- keep the service to a single instance while media is disk-backed
- disk-backed uploads persist across deploys
- object storage is still the better long-term option if you later need multiple web instances

### Postgres

Create a Render **Postgres** database in the same region as the web service.

Use the database's **Internal Database URL** as `DATABASE_URL`.

## Environment Variables

Set these on the Render web service.

### Core Django/runtime

```env
DEBUG=false
SECRET_KEY=replace-with-a-long-random-secret
PYTHON_VERSION=3.14.3
UV_VERSION=0.7.12
DATABASE_URL=postgresql://...
DATABASE_CONN_MAX_AGE=600
```

### Host and HTTPS

```env
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com,your-service.onrender.com
CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com,https://your-service.onrender.com
USE_X_FORWARDED_PROTO=true
SECURE_SSL_REDIRECT=true
SESSION_COOKIE_SECURE=true
CSRF_COOKIE_SECURE=true
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=true
SECURE_HSTS_PRELOAD=false
SECURE_REFERRER_POLICY=strict-origin-when-cross-origin
```

Only switch `SECURE_HSTS_PRELOAD=true` on once you are certain the domain and relevant subdomains will remain HTTPS-only.

### Stripe

```env
STRIPE_SECRET_KEY=sk_live_...
STRIPE_API_VERSION=2026-02-25.clover
STRIPE_CURRENCY=gbp
STRIPE_WEBHOOK_SECRET=whsec_...
```

### Optional public asset CDN

If you move large audio/image assets to Cloudflare R2 or another public bucket,
set a single base URL and keep the existing `audio/...` and `images/...` paths
in the database:

```env
PUBLIC_ASSET_BASE_URL=https://your-public-bucket-domain
```

With this set, the site will resolve relative asset paths such as
`audio/song.mp3` and `images/gig_photos/photo.jpg` against that public bucket
instead of the local repo's `static/` directory.

### Optional private paid downloads

If paid download files should stay private in Cloudflare R2, configure a
separate private bucket and let Django generate short-lived signed links:

```env
PRIVATE_DOWNLOADS_BUCKET_NAME=jlj-private-downloads
PRIVATE_DOWNLOADS_ENDPOINT_URL=https://<account-id>.r2.cloudflarestorage.com
PRIVATE_DOWNLOADS_ACCESS_KEY_ID=replace-me
PRIVATE_DOWNLOADS_SECRET_ACCESS_KEY=replace-me
PRIVATE_DOWNLOADS_REGION=auto
PRIVATE_DOWNLOADS_KEY_PREFIX=
PRIVATE_DOWNLOADS_URL_EXPIRY=300
```

If you also want the public `/music/` page to stream preview files from a
private bucket, the app can sign those too. By default the preview settings
fall back to the private download credentials above, but you can override them
separately if needed:

```env
PRIVATE_PREVIEWS_BUCKET_NAME=
PRIVATE_PREVIEWS_ENDPOINT_URL=
PRIVATE_PREVIEWS_ACCESS_KEY_ID=
PRIVATE_PREVIEWS_SECRET_ACCESS_KEY=
PRIVATE_PREVIEWS_REGION=auto
PRIVATE_PREVIEWS_KEY_PREFIX=
PRIVATE_PREVIEWS_URL_EXPIRY=900
```

You can also use local private files instead by setting:

```env
PRIVATE_DOWNLOADS_ROOT=/opt/render/project/src/media/private_downloads
```

### Email/contact

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=josephlovesjohn@gmail.com
EMAIL_HOST_PASSWORD=your-gmail-app-password
EMAIL_USE_TLS=true
DEFAULT_FROM_EMAIL=josephlovesjohn@gmail.com
CONTACT_RECIPIENT_EMAIL=josephlovesjohn@gmail.com
```

### Legal/business

```env
LEGAL_BUSINESS_NAME=JosephlovesJohn
BUSINESS_CONTACT_EMAIL=josephlovesjohn@gmail.com
BUSINESS_POSTAL_ADDRESS=
VAT_NUMBER=
```

### Sentry

```env
SENTRY_DSN=
SENTRY_ENVIRONMENT=production
SENTRY_RELEASE=
SENTRY_TRACES_SAMPLE_RATE=0.0
SENTRY_SEND_DEFAULT_PII=false
SENTRY_DEBUG=false
```

## First Deploy Tutorial

### 1. Create the Postgres database

- In Render, choose **New > Postgres**
- Pick the same region you want for the web service
- After creation, copy the **Internal Database URL**

### 2. Create the web service

- In Render, choose **New > Web Service**
- Connect this repository
- Fill in the commands shown above
- Add all required environment variables

### 3. Attach the persistent disk

- Open the web service
- Add a persistent disk
- Mount it at `/opt/render/project/src/media`

### 4. Deploy

Render will:

- install dependencies with `uv sync --frozen`
- collect static files
- run `manage.py check --deploy`
- run migrations before switching the deploy live
- start Gunicorn

### 5. Create the admin user

After the first deploy:

- open the Render Shell for the web service
- run:

```bash
uv run python manage.py createsuperuser
```

### 6. Verify persistent media

- log into `/admin/`
- upload one small gallery asset
- confirm it renders on the live site
- redeploy
- confirm the asset still exists

### 7. Add the custom domain

- Open **Settings > Custom Domains** for the web service
- Add your domain and follow the DNS instructions
- Include both apex and `www` if you want both
- Remove stray `AAAA` records if Render flags them during validation

### 8. Configure the Stripe webhook

Register this endpoint in Stripe:

```text
https://yourdomain.com/shop/stripe/webhook/
```

Subscribe at minimum to:

- `checkout.session.completed`
- `checkout.session.async_payment_succeeded`

For local testing with the Stripe CLI:

```bash
stripe listen --forward-to localhost:8000/shop/stripe/webhook/
```

Copy the reported `whsec_...` value into `STRIPE_WEBHOOK_SECRET`.

## Post-Deploy Smoke Checks

After deploy, verify:

1. Home page loads and static assets render correctly.
2. Legal pages load on their standalone routes.
3. Intro page loads the Kit signup form.
4. Contact form sends mail successfully.
5. Admin loads and uploaded media still renders after redeploy.
6. Add a song to cart and reach checkout.
7. Complete a Stripe test or live checkout.
8. Success page shows downloads and webhook delivery succeeds.
