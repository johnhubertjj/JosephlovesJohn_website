# Changelog

This project follows simple semantic versioning for production releases:

- `v1.0.0` was the first live public release of `josephlovesjohn.com`
- the current working tree is tracking `v1.0.2` until the next release commit is cut

## v1.0.2 - Unreleased

- Cleaned direct section routes so `/music/` and `/intro/` no longer append redundant hash fragments
- Hardened malformed one-page route handling for cases such as `#contact/music` and related variants
- Opened external contact social links in a new tab to avoid contaminating in-tab route state
- Preserved the active section hash before external contact popups open, so returning from TikTok or Instagram keeps clean in-page navigation
- Tightened the browser regression test to target the contact-section social link instead of any matching header icon
- Added repository-level architecture documentation and Mermaid diagrams for routing, rendering, state, and shop flow
- Upgraded Django from `6.0.3` to `6.0.4` to clear the April 2026 audit advisories affecting uploads, admin privilege boundaries, and ASGI header handling

## v1.0.1 - Unreleased

- Post-launch fixes and polish after the first live deployment
- Domain, email, SEO, and analytics hardening
- Browser regression coverage for routing, checkout, and cross-browser behavior
- Live-ops fixes for static assets, download delivery, and email failure tolerance

## v1.0.0 - 2026-04-17

- First public launch of `josephlovesjohn.com`
- Main artist site, mastering microsite, and legal pages live
- Direct-download music shop with Stripe Checkout
- Customer accounts, password reset, order history, and downloads
- MP3 and WAV delivery from account, success page, and email links
- Plausible, Sentry, sitemap, and robots setup
