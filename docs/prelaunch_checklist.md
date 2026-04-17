# JosephlovesJohn Prelaunch Checklist

This is the project-specific launch checklist for the main site, shop, checkout, downloads, email, analytics, and deployment stack.

## 1. Core Site

- [ ] Homepage loads on the production domain
- [ ] Intro, music, art, contact, privacy, cookies, terms, and refunds routes all load
- [ ] No broken images, missing CSS, or missing JS
- [ ] Header, footer, and legal links work
- [ ] Logo links back to home
- [ ] No placeholder text, test copy, or temp branding remains

## 2. Mobile and Browser

- [ ] Check the site on phone and laptop
- [ ] Check at least one non-Chromium browser
- [ ] Text is readable and controls are usable on mobile
- [ ] Cart modal, share modal, art lightbox, and menu all work on mobile
- [ ] Checkout page is usable on mobile

## 3. Contact and Signup

- [ ] Contact form submits successfully
- [ ] Contact email arrives at the correct inbox
- [ ] Validation errors are clear
- [ ] Optional signup embed respects cookie preference
- [ ] Direct signup link still works in essential-only cookie mode

## 4. Shop Basics

- [ ] Product titles, prices, artwork, preview audio, and slugs are correct
- [ ] Add to cart works
- [ ] Remove from cart works
- [ ] Cart totals are correct
- [ ] Cart persists correctly during the checkout journey

## 5. Checkout and Orders

- [ ] Complete a full test purchase in Stripe test mode
- [ ] Test a successful payment
- [ ] Test a canceled payment
- [ ] Order appears in admin
- [ ] Order is marked paid only after Stripe confirmation
- [ ] Guest success page works after payment
- [ ] Logged-in customer account shows previous orders

## 6. Downloads

- [ ] Every paid product has a real download file available before launch
- [ ] Success page download links work
- [ ] Emailed download links work from a different browser or device
- [ ] Guest download access expires back to the intended rules after the recent session is gone
- [ ] Private download storage is configured correctly if using R2

## 7. Customer Emails and Accounts

- [ ] Confirmation email sends after payment
- [ ] Confirmation email uses the correct from-address
- [ ] Email links use the real production domain
- [ ] Register flow works
- [ ] Login flow works
- [ ] Forgot-password flow works end to end

## 8. Stripe

- [ ] Live and test keys are stored only in environment variables
- [ ] Webhook endpoint is configured at `/shop/stripe/webhook/`
- [ ] Webhook deliveries succeed on the real domain
- [ ] Success and failure states are handled cleanly
- [ ] Any enabled payment methods shown in Checkout have been tested in practice
- [ ] Statement descriptor is set
- [ ] Live mode is not enabled until all test-mode checks pass

## 9. Analytics and Cookie Consent

- [ ] Plausible is enabled with the correct domain
- [ ] Pageviews appear in Plausible
- [ ] `Add to Cart`, `Begin Checkout`, and `Purchase Completed` events appear
- [ ] Cookie banner works
- [ ] Essential-only mode blocks optional embeds as intended
- [ ] Cookie settings link reopens the banner/preferences controls

## 10. Security and Production Settings

- [ ] `DEBUG=false`
- [ ] `SECRET_KEY` is set securely
- [ ] `ALLOWED_HOSTS` includes the production hostnames
- [ ] `CSRF_TRUSTED_ORIGINS` includes the production origins
- [ ] HTTPS redirect is enabled
- [ ] Secure session and CSRF cookies are enabled
- [ ] HSTS settings are correct for the deployment stage
- [ ] No secrets or `.env` files are committed
- [ ] `manage.py check --deploy` passes with production settings

## 11. Email, Domains, and Legal

- [ ] `DEFAULT_FROM_EMAIL` is correct
- [ ] Contact inbox is correct
- [ ] Business name, contact email, postal address, and VAT details are correct
- [ ] Domain routing is correct for apex and `www`, if both are used
- [ ] Stripe success, cancel, webhook, and email links all point at the intended domain

## 12. Admin and Operations

- [ ] Admin login works
- [ ] Products can be added and edited
- [ ] Orders can be viewed in admin
- [ ] Team knows where Render logs are
- [ ] Team knows how to redeploy
- [ ] Team knows how to roll back

## 13. Assets, Storage, and Performance

- [ ] `collectstatic` output is healthy in production
- [ ] Large assets are in the intended storage location
- [ ] Public CDN/R2 asset URLs resolve correctly if enabled
- [ ] Private downloads are signed correctly if using R2
- [ ] Pages load quickly enough on real devices

## 14. Backup and Recovery

- [ ] Database backup plan is understood
- [ ] Database restore process is known
- [ ] Media/download recovery plan is known
- [ ] App can be redeployed from the repo and environment variables alone

## 15. Monitoring and Error Reporting

- [ ] Sentry project exists
- [ ] `SENTRY_DSN` is set in production
- [ ] `SENTRY_ENVIRONMENT=production`
- [ ] `SENTRY_RELEASE` is set to the deployed revision or version
- [ ] `SENTRY_TRACES_SAMPLE_RATE` is intentionally chosen
- [ ] One deliberate test error has been sent and received in Sentry
- [ ] Alerts are configured for unhandled production errors

## 16. Final Human Pass

- [ ] Buy one real low-value product after launch and verify the whole journey
- [ ] Read the order email as a customer would
- [ ] Download the purchased file from the email link
- [ ] Check admin, Stripe, Plausible, and Sentry after the first real purchase
