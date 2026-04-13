# Deployment Notes

This document covers the main site and shop deployment only. The mastering site is intentionally out of scope for now.

## Preconditions

- Python environment synced with project dependencies
- Real production domain ready
- HTTPS enabled on the host or proxy
- Persistent database and persistent media storage available

## Required Environment Variables

### Core Django

```env
DEBUG=false
SECRET_KEY=replace-with-a-long-random-secret
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

### HTTPS / Proxy

If the app is behind a reverse proxy that terminates SSL:

```env
USE_X_FORWARDED_PROTO=true
SECURE_SSL_REDIRECT=true
SESSION_COOKIE_SECURE=true
CSRF_COOKIE_SECURE=true
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=true
```

Optional:

```env
SECURE_HSTS_PRELOAD=true
```

Only enable `SECURE_HSTS_PRELOAD=true` once you are certain the domain and relevant subdomains will stay HTTPS-only.

### Stripe

```env
STRIPE_SECRET_KEY=sk_live_...
STRIPE_API_VERSION=2026-02-25.clover
STRIPE_CURRENCY=gbp
STRIPE_WEBHOOK_SECRET=whsec_...
```

### Contact Form Email

For Gmail SMTP:

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

### Sentry

```env
SENTRY_DSN=
SENTRY_ENVIRONMENT=production
SENTRY_RELEASE=
SENTRY_TRACES_SAMPLE_RATE=0.0
SENTRY_SEND_DEFAULT_PII=false
SENTRY_DEBUG=false
```

## Deploy Commands

Run these on the server during deploy:

```bash
uv run python manage.py migrate
uv run python manage.py collectstatic --noinput
uv run python manage.py check --deploy
```

## Stripe Webhook Setup

The shop now exposes a Stripe webhook endpoint at:

```text
/shop/stripe/webhook/
```

In Stripe, register a webhook endpoint that sends at least:

- `checkout.session.completed`
- `checkout.session.async_payment_succeeded`

For local testing with the Stripe CLI:

```bash
stripe listen --forward-to localhost:8000/shop/stripe/webhook/
```

Copy the reported `whsec_...` value into `STRIPE_WEBHOOK_SECRET`.

## Static Files

- Static files are served with WhiteNoise in production.
- `collectstatic` writes to `staticfiles/`.
- In local development, Django continues to use the normal staticfiles backend instead of the manifest backend.

## Media Files

Admin-uploaded gallery assets use `MEDIA_ROOT`.

That means production needs persistent media storage. If the deploy platform uses ephemeral disk, uploaded images/videos will disappear on redeploy unless you move media to durable storage.

Current default:

```env
MEDIA_URL=/media/
```

Current storage backend is local filesystem storage, so plan accordingly.

## Database

The app currently defaults to SQLite. That is fine for local development but not ideal for a real production deployment.

Recommended next step:

- move production to Postgres

That change has not been implemented in the repo yet.

## Post-Deploy Smoke Checks

After deploy, verify:

1. Home page loads with the animated background and icons visible.
2. Intro page loads the Kit signup form.
3. Contact form sends mail successfully.
4. Admin loads and uploaded art/media still renders.
5. Add a song to cart and complete a Stripe test/live checkout.
6. Paid order success page shows downloads.

## Known Production Follow-Up

Stripe checkout currently confirms payment when the user lands on the success page. There is not yet a Stripe webhook in the repo.

That means the next production-hardening step after this deployment work should be:

- add a Stripe webhook for checkout/session completion
