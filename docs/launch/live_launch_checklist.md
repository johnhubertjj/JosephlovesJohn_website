# JosephlovesJohn Live Launch Checklist

## 1. Domain and DNS

- [ ] `josephlovesjohn.com` is `Verified` in Render
- [ ] `www.josephlovesjohn.com` is `Verified` in Render
- [ ] Both domains have `Certificate Issued`
- [ ] `www.josephlovesjohn.com` redirects to `josephlovesjohn.com`
- [ ] No old GoDaddy forwarding remains enabled

## 2. Render Production Settings

- [ ] `SITE_URL=https://josephlovesjohn.com`
- [ ] `ALLOWED_HOSTS` includes `josephlovesjohn.com`, `www.josephlovesjohn.com`, and the Render hostname
- [ ] `CSRF_TRUSTED_ORIGINS` includes both HTTPS domains
- [ ] `DEBUG=false`
- [ ] `SECRET_KEY` is set
- [ ] Live Stripe keys are set
- [ ] `STRIPE_WEBHOOK_SECRET` is set
- [ ] Resend SMTP settings are set
- [ ] `SENTRY_DSN` is set
- [ ] Plausible settings are set

## 3. Deploy

- [ ] Latest code is pushed
- [ ] Render deploy completes successfully
- [ ] `collectstatic` succeeds
- [ ] Migrations run successfully
- [ ] Homepage loads without server errors

## 4. Core Site Checks

- [ ] `https://josephlovesjohn.com/` loads over HTTPS
- [ ] Intro, Music, Art, Contact, Privacy, Cookies, Terms, and Refunds routes load
- [ ] Logo, favicon, CSS, and JS all load correctly
- [ ] No broken images are visible
- [ ] Contact form loads and validates properly

## 5. Shop and Payment Checks

- [ ] Add to cart works
- [ ] Cart remove works
- [ ] Checkout page loads
- [ ] Stripe hosted checkout opens
- [ ] One real low-value live payment succeeds
- [ ] Stripe webhook succeeds on the live domain
- [ ] Success page loads
- [ ] Order is marked paid

## 6. Email and Download Checks

- [ ] Confirmation email arrives
- [ ] Password reset email arrives
- [ ] Confirmation email links use `josephlovesjohn.com`
- [ ] MP3 download works
- [ ] Download links from the email work

## 7. Monitoring and Analytics

- [ ] Plausible shows a pageview
- [ ] Plausible shows checkout/purchase events
- [ ] Sentry receives no unexpected production errors
- [ ] Stripe shows successful payment and successful webhook delivery

## 8. Search and Discovery

- [ ] `https://josephlovesjohn.com/robots.txt` loads
- [ ] `https://josephlovesjohn.com/sitemap.xml` loads
- [ ] Sitemap submitted to Google Search Console
- [ ] Sitemap submitted to Bing Webmaster Tools
- [ ] Website link added to Spotify, YouTube, Bandcamp, Instagram, TikTok, and gig listings

## 9. After Launch

- [ ] Refund your own test purchase if needed
- [ ] Watch the first real order closely
- [ ] Check Render logs after launch
- [ ] Check Stripe, Plausible, and Sentry again after the first real purchase
