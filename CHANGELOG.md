# Changelog

This project follows simple semantic versioning for production releases:

- `v1.0.0` was the first live public release of `josephlovesjohn.com`
- the current package version is `v1.3.2`
- the latest tagged release is `v1.1.1`

## v1.3.2 - 2026-05-02

- Added consent-gated Meta Pixel support for individual track pages via the `META_PIXEL_ID` environment variable
- Updated the content security policy to allow Meta Pixel script and event endpoints when the Pixel is configured
- Hardened cookie preference events for WebKit by adding a legacy `CustomEvent` fallback
- Disabled reCAPTCHA during browser-test runs so local or CI environment keys do not trigger external Google calls and WebKit access-control failures

## v1.3.1 - 2026-05-02

- Added individual music track routes to the public sitemap so search engines can discover the Dark and Light track pages directly
- Updated music-page structured data so track entries point at the dedicated track pages instead of hash fragments on `/music/`
- Added permanent redirects from legacy product-slug track URLs to the shorter canonical public track URLs
- Scoped contact-form flash messages so shop and cart notices no longer leak into the Contact section after moving between pages

## v1.3.0 - 2026-05-02

- Added standalone per-track smart-link pages for Dark and Light and Dark and Light - Instrumental, with track artwork, platform links, canonical SEO URLs, and homepage title links
- Updated the track pages with the correct Spotify, iTunes, Apple Music, Bandcamp, YouTube, Amazon Music, Deezer, and TIDAL destinations
- Refined the track-page button styling, responsive home link, cover-art sizing, and click layering so the pages stay clear and usable across viewport sizes

## v1.2.0 - 2026-04-27

- Hardened shop account privacy by adding no-store cache headers to login, registration, checkout, account, success, download, and cart endpoints
- Added a Safari back-forward cache guard so stale authenticated shop pages revalidate after logout instead of remaining visible when using the browser Back button
- Reduced bot account creation with registration rate limiting and an invisible honeypot field on the signup form
- Added optional invisible reCAPTCHA v3 verification for contact, account creation, and login submissions
- Simplified customer accounts by removing the visible full-name signup field and dropping stored profile names from customer profiles, admin, and account pages
- Added a migration to remove the old customer profile name column while keeping usernames, emails, order history, and downloads working normally
- Updated shop tests to cover no-store headers, registration bot protections, profile-name removal, and browser-history revalidation behavior

## v1.1.1 - 2026-04-24

- Improved `/art/` gallery performance with WebP thumbnail delivery for static art assets and lighter animation preview media
- Re-encoded Buddlea and Symbol animation loops to compact MP4 previews and automatically prefer them when they are smaller than the GIF source
- Restored Safari-friendly animation lightbox previews so inline video cards stay clickable, open correctly in the lightbox, and avoid image/video overlap
- Smoothed art lightbox close and reopen behavior by deferring heavy cleanup work and reducing preview preload cost during navigation

## v1.1.0 - 2026-04-23

- Added Redis-backed scaling support for cache and session state, with object-storage-ready media handling for production-style deployments
- Introduced shared main-site content caching, cache invalidation signals, narrower cart context generation, and short-lived cart summary caching
- Added performance benchmarking and reporting tooling for branch comparisons, concurrency checks, query profiling, and HTML report generation
- Fixed benchmark server cleanup so generated concurrency reports now align with direct and manual runs instead of being distorted by leaked processes
- Improved public-page throughput under warm and concurrent traffic on `feature/scaling`, while keeping benchmark artifacts and report wording clearer and more trustworthy
- Hardened shop checkout presentation with a Samsung-safe custom terms checkbox and versioned shop stylesheet URLs so mobile browsers pick up CSS changes reliably
- Fixed Safari-specific `/art/` image handling and related front-end regressions
- Improved CI and deployment support with preview URL handling, faster asset state verification, PR deployment fixes, and benchmark script fallbacks when `redis-cli` is unavailable

## v1.0.2 - 2026-04-19

- Cleaned direct section routes so `/music/` and `/intro/` no longer append redundant hash fragments
- Hardened malformed one-page route handling for cases such as `#contact/music` and related variants
- Opened external contact social links in a new tab to avoid contaminating in-tab route state
- Preserved the active section hash before external contact popups open, so returning from TikTok or Instagram keeps clean in-page navigation
- Tightened the browser regression test to target the contact-section social link instead of any matching header icon
- Added repository-level architecture documentation and Mermaid diagrams for routing, rendering, state, and shop flow
- Upgraded Django from `6.0.3` to `6.0.4` to clear the April 2026 audit advisories affecting uploads, admin privilege boundaries, and ASGI header handling

## v1.0.1 - 2026-04-18

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
