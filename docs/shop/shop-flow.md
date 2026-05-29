# Shop Flow

This document maps how the JosephlovesJohn site is wired together today, with extra focus on where state lives and what each JavaScript file is responsible for.

## Site Architecture

```mermaid
flowchart LR
    Browser["Browser"]
    URLs["URL router<br>/ /shop/ /mastering-services/"]
    MainViews["main_site views<br>build one-page site context"]
    ShopViews["shop views<br>cart, checkout, account, downloads"]
    MainModels["main_site models<br>nav links, gig photos, album art, animations"]
    ShopModels["shop models<br>Product, Order, OrderItem, CustomerProfile"]
    Session["Session store<br>shop_cart, shop_recent_orders"]
    Templates["Django templates<br>site.html, shop/*.html"]
    ThemeJS["Theme JS<br>static/assets/js/main.js"]
    SiteJS["Custom JS<br>site.js, cart.js, cookies.js, analytics.js"]
    Downloads["Download delivery<br>local/private files or presigned redirects"]
    Email["Order emails<br>signed download links"]
    Stripe["Stripe Checkout + webhook"]

    Browser --> URLs
    URLs --> MainViews
    URLs --> ShopViews
    MainViews --> MainModels
    MainViews --> ShopModels
    ShopViews --> ShopModels
    ShopViews --> Session
    MainViews --> Templates
    ShopViews --> Templates
    Templates --> Browser
    Browser --> ThemeJS
    Browser --> SiteJS
    ShopViews --> Stripe
    Stripe --> ShopViews
    ShopViews --> Downloads
    ShopViews --> Email
```

## State And Stores

```mermaid
flowchart TD
    DOM["DOM state<br>open modal, visible section, copied button text"]
    CookieState["Cookie preference<br>essential vs all"]
    CartSession["Session key: shop_cart<br>ordered list of product slugs"]
    RecentOrders["Session key: shop_recent_orders<br>guest access allow-list"]
    ProductTable["Database: Product"]
    OrderTables["Database: Order + OrderItem"]
    ProfileTable["Database: CustomerProfile"]
    ContentTables["Database: HeaderSocialLink, PrimaryNavItem, GigPhoto, AlbumArt, AnimationAsset"]
    Stripe["Stripe session state"]
    EmailTokens["Signed email access tokens<br>30-day download links"]

    DOM <-->|fetch JSON + rerender| CartSession
    CookieState --> DOM
    CartSession --> ProductTable
    ProductTable --> OrderTables
    OrderTables --> ProfileTable
    OrderTables <-->|session_id + webhook| Stripe
    RecentOrders --> OrderTables
    EmailTokens --> OrderTables
    ContentTables --> DOM
```

## Checkout Journey

```mermaid
flowchart TD
    A["User opens /music/ or /#music"] --> B["Clicks Download"]
    B --> C["cart.js POSTs to /shop/cart/add/&lt;slug&gt;/"]
    C --> D["Session cart saves product slug"]
    D --> E["JSON cart summary comes back"]
    E --> F["cart.js rerenders cart modal and floating count"]
    F --> G{"Checkout now?"}
    G -- No --> H["Keep browsing or remove an item"]
    H --> B
    G -- Yes --> I["GET /shop/checkout/"]
    I --> J{"Cart has products?"}
    J -- No --> K["Redirect to /music/ with message"]
    J -- Yes --> L{"Downloads available for every item?"}
    L -- No --> M["Render checkout page with delivery error"]
    L -- Yes --> N["Render local checkout review page"]
    N --> O["User accepts terms and POSTs /shop/checkout/"]
    O --> P["Re-check download availability"]
    P --> Q{"Still available?"}
    Q -- No --> R["Show checkout error and do not create an order"]
    Q -- Yes --> S["Create pending Order"]
    S --> T["Create OrderItem snapshots from current products"]
    T --> U["Create Stripe Checkout Session"]
    U --> V{"Stripe session created?"}
    V -- No --> W["Delete pending order and show checkout error"]
    V -- Yes --> X["Redirect to hosted Stripe Checkout"]
    X --> Y{"Payment outcome"}
    Y -- Canceled --> Z["Return to /shop/checkout/?canceled=1 with cart intact"]
    Y -- Paid --> AA["Webhook and/or success page verify payment"]
    AA --> AB["Order marked confirmed and customer details synced"]
    AB --> AC["Send confirmation email with signed download links once"]
    AC --> AD["Session cart cleared and recent guest order remembered"]
    AD --> AE["Success page shows protected download links"]
    AE --> AF["Download allowed by account, recent session, or signed email token"]
```

## Checkout Sequence

```mermaid
sequenceDiagram
    actor User
    participant MusicPage as Music page template
    participant CartJS as static/main_site/js/cart.js
    participant CartAdd as shop.views.cart_add
    participant Cart as shop.cart helpers
    participant CheckoutGet as CheckoutView.get
    participant CheckoutPost as CheckoutView.post
    participant Downloads as shop.downloads helpers
    participant Order as Order / OrderItem
    participant Stripe as Stripe Checkout
    participant Webhook as StripeWebhookView
    participant Success as OrderSuccessView
    participant Profile as CustomerProfile
    participant Email as shop.emails helpers
    participant DownloadView as OrderDownloadView

    User->>MusicPage: Click "Download"
    MusicPage->>CartJS: Read data-cart-add-url
    CartJS->>CartAdd: POST /shop/cart/add/<slug>/
    CartAdd->>Cart: add_product()
    CartAdd->>Cart: build_cart_summary()
    Cart-->>CartAdd: items + totals + URLs
    CartAdd-->>CartJS: JSON summary
    CartJS-->>User: Open modal and rerender cart UI

    User->>CheckoutGet: GET /shop/checkout/
    CheckoutGet->>Cart: get_cart_products()
    CheckoutGet->>Downloads: download_asset_exists()
    CheckoutGet-->>User: Render review page or delivery error

    User->>CheckoutPost: POST /shop/checkout/
    CheckoutPost->>Cart: get_cart_products()
    CheckoutPost->>Downloads: download_asset_exists()
    CheckoutPost->>Order: create pending Order
    loop For each product in cart
        CheckoutPost->>Order: create OrderItem snapshot
    end
    CheckoutPost->>Stripe: create checkout session
    Stripe-->>CheckoutPost: hosted URL + session id
    CheckoutPost->>Order: save stripe_checkout_session_id
    CheckoutPost-->>User: Redirect to Stripe

    par Optional background fulfillment
        Stripe-->>Webhook: checkout.session.completed
        Webhook->>Order: fulfill matching order if found
        Webhook->>Email: send_order_confirmation_email()
    and Return to success page
        Stripe-->>Success: GET /shop/success/<order_id>/?session_id=...
        Success->>Order: load order + verify access rules
        Success->>Stripe: retrieve checkout session
        Stripe-->>Success: complete + paid + customer details
        Success->>Order: mark_paid()
        opt Logged-in order
            Success->>Profile: sync full_name and email
        end
        Success->>Email: send_order_confirmation_email()
        Success->>Cart: clear_cart()
        Success->>Cart: remember order id in shop_recent_orders
        Success-->>User: Render download page
    end

    User->>DownloadView: GET /shop/download/<item_id>/
    DownloadView->>Order: verify paid order access
    alt Signed email link
        DownloadView->>Email: validate signed access token
    end
    DownloadView->>Downloads: build_download_response()
    Downloads-->>User: File response or presigned redirect
```

## Core Shop Models

```mermaid
classDiagram
    class Product {
        +title
        +slug
        +artist_name
        +meta
        +description
        +art_path
        +art_alt
        +preview_file_wav
        +preview_file_mp3
        +download_file_path
        +product_kind
        +price
        +sort_order
        +is_published
        +is_reversed
        +player_id
        +price_display
        +art_url
        +preview_wav_url
        +preview_mp3_url
        +download_url
    }

    class CustomerProfile {
        +user
        +full_name
        +marketing_opt_in
        +updated_at
    }

    class Order {
        +user
        +full_name
        +email
        +status
        +subtotal
        +total
        +notes
        +stripe_checkout_session_id
        +stripe_payment_intent_id
        +paid_at
        +confirmation_email_sent_at
        +created_at
        +total_display
        +is_paid
        +mark_paid()
    }

    class OrderItem {
        +order
        +product
        +title_snapshot
        +artist_snapshot
        +meta_snapshot
        +price_snapshot
        +art_path_snapshot
        +art_alt_snapshot
        +download_file_path
        +price_display
        +art_url
        +download_url
    }

    class CartHelpers {
        +add_product()
        +remove_product()
        +get_cart_slugs()
        +get_cart_products()
        +build_cart_summary()
        +clear_cart()
    }

    class DownloadHelpers {
        +download_asset_exists()
        +build_download_response()
        +presigned_private_asset_url()
    }

    class EmailHelpers {
        +send_order_confirmation_email()
        +build_download_access_token()
        +has_valid_download_access_token()
    }

    class CheckoutView
    class OrderSuccessView
    class OrderDownloadView
    class StripeWebhookView
    class AccountView
    class cart_add
    class cart_remove

    Order "1" --> "*" OrderItem
    Product "1" --> "*" OrderItem
    CustomerProfile --> "1" Order : via authenticated user
    CheckoutView ..> CartHelpers
    CheckoutView ..> DownloadHelpers
    CheckoutView ..> Order
    CheckoutView ..> Stripe
    OrderSuccessView ..> Order
    OrderSuccessView ..> CustomerProfile
    OrderSuccessView ..> EmailHelpers
    OrderSuccessView ..> Stripe
    OrderDownloadView ..> Order
    OrderDownloadView ..> DownloadHelpers
    OrderDownloadView ..> EmailHelpers
    StripeWebhookView ..> Order
    StripeWebhookView ..> EmailHelpers
    AccountView ..> Order
    cart_add ..> Product
    cart_add ..> CartHelpers
    cart_remove ..> Product
    cart_remove ..> CartHelpers
```

## Notes

- There is no front-end store library here. The main "stores" are Django sessions, the database, and the DOM.
- `shop_cart` is a session-backed list of product slugs. It is not a quantity-based basket.
- `shop_recent_orders` is a session-backed allow-list so guest users can revisit their own success page and downloads.
- The site is mostly server-rendered. Django builds HTML first, then JavaScript enhances that HTML.
- `static/assets/js/main.js` is the HTML5 UP shell controller. It handles hash-based article switching, header/footer visibility, top-nav docking, and the mastering-link transition.
- `static/main_site/js/site.js` handles custom UI enhancements: lazy-loading the signup embed, audio player setup, share modal behavior, and the art lightbox.
- `static/main_site/js/cart.js` handles add/remove cart requests, receives JSON summaries from Django, and rerenders the cart modal client-side.
- `static/main_site/js/cookies.js` only manages the cookie banner visibility and its dismissal cookie.
- `templates/shop/checkout.html` also contains a tiny inline script that enables or disables the submit button based on the consent checkbox.
- Orders are created as `pending` before redirecting to Stripe, then confirmed either on the success-page verification path or via webhook fulfillment.

## Main Files

- [shop/views.py](/Users/johnjoseph/PycharmProjects/JosephlovesJohn_website/shop/views.py)
- [shop/cart.py](/Users/johnjoseph/PycharmProjects/JosephlovesJohn_website/shop/cart.py)
- [shop/models.py](/Users/johnjoseph/PycharmProjects/JosephlovesJohn_website/shop/models.py)
- [shop/context_processors.py](/Users/johnjoseph/PycharmProjects/JosephlovesJohn_website/shop/context_processors.py)
- [shop/forms.py](/Users/johnjoseph/PycharmProjects/JosephlovesJohn_website/shop/forms.py)
- [main_site/views.py](/Users/johnjoseph/PycharmProjects/JosephlovesJohn_website/main_site/views.py)
- [templates/main_site/site.html](/Users/johnjoseph/PycharmProjects/JosephlovesJohn_website/templates/main_site/site.html)
- [templates/main_site/includes/components/music/library_item.html](/Users/johnjoseph/PycharmProjects/JosephlovesJohn_website/templates/main_site/includes/components/music/library_item.html)
- [static/main_site/js/cart.js](/Users/johnjoseph/PycharmProjects/JosephlovesJohn_website/static/main_site/js/cart.js)
- [static/main_site/js/site.js](/Users/johnjoseph/PycharmProjects/JosephlovesJohn_website/static/main_site/js/site.js)
- [static/main_site/js/cookies.js](/Users/johnjoseph/PycharmProjects/JosephlovesJohn_website/static/main_site/js/cookies.js)
- [static/assets/js/main.js](/Users/johnjoseph/PycharmProjects/JosephlovesJohn_website/static/assets/js/main.js)
- [tests/test_shop_flow.py](/Users/johnjoseph/PycharmProjects/JosephlovesJohn_website/tests/test_shop_flow.py)
- [tests/test_browser_ui.py](/Users/johnjoseph/PycharmProjects/JosephlovesJohn_website/tests/test_browser_ui.py)
