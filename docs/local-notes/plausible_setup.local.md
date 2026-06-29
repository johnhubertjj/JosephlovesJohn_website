# Plausible Setup Checklist

This is a local-only setup note for the live `josephlovesjohn.com` site.

## Render

Set these environment variables on the Render web service:

```env
PLAUSIBLE_DOMAIN=josephlovesjohn.com
PLAUSIBLE_SCRIPT_SRC=https://plausible.io/js/pa-J6bhmMJeOSd44Xkxjn7p2.js
```

Also confirm:

- `ALLOWED_HOSTS` includes `josephlovesjohn.com`, `www.josephlovesjohn.com`, and the Render hostname
- `CSRF_TRUSTED_ORIGINS` includes `https://josephlovesjohn.com`, `https://www.josephlovesjohn.com`, and the Render hostname

After saving the env vars, redeploy the web service.

## Plausible Dashboard

Site:

- Site domain: `josephlovesjohn.com`
- Timezone: `Europe/London`

Enable:

- `Custom events`
- `Ecommerce revenue`

Optional:

- `Outbound links`
- `Form submissions`

## Events Already Sent By The Site

The codebase already sends these Plausible custom events:

- `Add to Cart`
- `Begin Checkout`
- `Purchase Completed`
- `Signup Opened`
- `Contact Submitted`
- `Outbound Link Clicked`

`Purchase Completed` includes:

- `currency: GBP`
- dynamic order revenue amount
- `order_id`
- `item_count`
- `product_titles`

## Verification

After redeploying:

1. Visit `https://josephlovesjohn.com`
2. Open Plausible live view or installation checker
3. Add a track to cart
4. Open checkout
5. Confirm `Add to Cart` and `Begin Checkout` appear
6. After a real or test purchase flow, confirm `Purchase Completed` appears with revenue

## Code References

- Plausible loader: `templates/main_site/base.html`
- Custom events: `static/main_site/js/analytics.js`
- Cart trigger: `static/main_site/js/cart.js`
- Checkout payload: `templates/shop/checkout.html`
- Purchase payload: `templates/shop/success.html`
