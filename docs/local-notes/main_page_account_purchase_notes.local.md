Main-page account/purchase-state idea that was reverted on April 17, 2026:

- Public-page auth entry:
  Add small `Log in` / `Create account` controls for anonymous visitors, and an `Account` link for signed-in users.
  Best implementation path used:
  - markup at the page-shell level rather than inside the hero stack
  - styles in a dedicated CSS component file

- Purchased-track music-card state:
  When a signed-in listener already owns a track, replace the `Download` buy button in the music library card with an account-facing thank-you state.
  Best implementation path used:
  - derive owned product slugs from confirmed `OrderItem` rows for `request.user`
  - pass owned slugs through the main-site context
  - swap the buy CTA in `templates/main_site/includes/components/music/library_item.html`

- Reverted because:
  The account-entry control did not suit the homepage composition and the user preferred the prior cleaner layout.

- If reintroduced later:
  Keep the account entry outside the centered hero composition.
  Consider a subtler single-link treatment instead of a paired pill CTA.
  Consider whether the purchased-track state belongs on the main page, cart, checkout, or account page before re-enabling it.
