# Shop Flow

This document maps the current shop implementation in the Django app as it exists today.

## User Journey

```mermaid
flowchart TD
    A["User opens /music/"] --> B["Clicks Buy song"]
    B --> C["cart.js POSTs to /shop/cart/add/&lt;slug&gt;/"]
    C --> D["Session cart stores product slug"]
    D --> E["Cart modal updates with items and subtotal"]
    E --> F{"User clicks Checkout?"}
    F -- No --> G["User can remove item or keep browsing"]
    G --> B
    F -- Yes --> H["GET /shop/checkout/"]
    H --> I{"Cart has products?"}
    I -- No --> J["Redirect back to /music/ with info message"]
    I -- Yes --> K["Create pending Order and OrderItem snapshots"]
    K --> L["Create Stripe Checkout Session"]
    L --> M{"Stripe session created?"}
    M -- No --> N["Delete pending order and render checkout error state"]
    M -- Yes --> O["Redirect to hosted Stripe Checkout"]
    O --> P{"Payment outcome"}
    P -- Canceled --> Q["Return to /shop/checkout/?canceled=1 with cart intact"]
    P -- Paid --> R["Return to /shop/success/&lt;order_id&gt;/?session_id=..."]
    R --> S["Success view verifies Stripe session and payment status"]
    S --> T["Order marked confirmed and customer details synced"]
    T --> U["Session cart cleared and order remembered in session"]
    U --> V["Success page shows download links"]
    V --> W{"Logged-in user?"}
    W -- Yes --> X["Order also appears in /shop/account/"]
    W -- No --> Y["Guest can revisit only if order is in shop_recent_orders"]
```

## Sequence Diagram

```mermaid
sequenceDiagram
    actor User
    participant MusicPage as Music Page
    participant CartJS as cart.js
    participant CartAdd as shop.views.cart_add
    participant Cart as shop.cart
    participant Product as shop.models.Product
    participant Checkout as shop.views.CheckoutView
    participant Order as shop.models.Order
    participant OrderItem as shop.models.OrderItem
    participant Stripe as Stripe Checkout
    participant Success as shop.views.OrderSuccessView
    participant Profile as shop.models.CustomerProfile

    User->>MusicPage: Click "Buy song"
    MusicPage->>CartJS: data-cart-add-url
    CartJS->>CartAdd: POST /shop/cart/add/<slug>/
    CartAdd->>Product: get published product by slug
    CartAdd->>Cart: add_product(request, product)
    CartAdd->>Cart: build_cart_summary(request)
    Cart-->>CartAdd: JSON summary
    CartAdd-->>CartJS: cart payload
    CartJS-->>User: Update and open cart modal

    User->>CartJS: Click "Checkout"
    CartJS->>Checkout: GET /shop/checkout/
    Checkout->>Cart: get_cart_products(request)
    Checkout->>Order: create pending order
    loop For each product in cart
        Checkout->>OrderItem: create snapshot row
    end
    Checkout->>Stripe: create hosted checkout session
    Stripe-->>Checkout: checkout URL + session id
    Checkout->>Order: save stripe_checkout_session_id
    Checkout-->>User: Redirect to Stripe-hosted payment page

    User->>Stripe: Complete payment
    Stripe-->>Success: Redirect /shop/success/<order_id>/?session_id=...
    Success->>Order: load order and items
    Success->>Stripe: retrieve checkout session
    Stripe-->>Success: session status, payment status, customer details
    Success->>Order: mark_paid(), save Stripe payment intent, save customer details
    opt Logged-in user
        Success->>Profile: sync full_name
    end
    Success->>Cart: clear_cart(request)
    Success-->>User: Show downloads and confirmed order details
```

## Class Diagram

```mermaid
classDiagram
    class Product {
        +title
        +slug
        +artist_name
        +meta
        +description
        +art_path
        +download_file_path
        +product_kind
        +price
        +sort_order
        +is_published
        +price_display()
        +get_add_to_cart_url()
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
        +stripe_checkout_session_id
        +stripe_payment_intent_id
        +paid_at
        +created_at
        +total_display()
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
        +download_file_path
        +price_display()
    }

    class CartHelpers {
        +add_product()
        +remove_product()
        +get_cart_products()
        +build_cart_summary()
        +clear_cart()
    }

    class CheckoutView
    class OrderSuccessView
    class AccountView
    class RegisterView
    class ShopLoginView
    class cart_add
    class cart_remove

    Order "1" --> "*" OrderItem
    Product "1" --> "*" OrderItem
    CustomerProfile --> "1" Order : via authenticated user
    CheckoutView ..> CartHelpers
    CheckoutView ..> Order
    CheckoutView ..> OrderItem
    CheckoutView ..> Product
    CheckoutView ..> Stripe
    OrderSuccessView ..> Order
    OrderSuccessView ..> CustomerProfile
    OrderSuccessView ..> Stripe
    AccountView ..> Order
    RegisterView ..> CustomerProfile
    cart_add ..> Product
    cart_add ..> CartHelpers
    cart_remove ..> Product
    cart_remove ..> CartHelpers
```

## Notes

- The cart is session-backed and stores product slugs, not quantities.
- Checkout is Stripe-hosted. The local checkout page is now mainly a fallback surface for cancellation and startup errors.
- Orders are created as `pending` before redirecting to Stripe.
- The cart is only cleared after the success view re-validates the Stripe session as `complete` and `paid`.
- Guest success pages are protected by `shop_recent_orders` in session.
- Logged-in users can review confirmed purchases in `/shop/account/`.

## Main Files

- [shop/views.py](/Users/johnjoseph/PycharmProjects/JosephlovesJohn_website/shop/views.py)
- [shop/cart.py](/Users/johnjoseph/PycharmProjects/JosephlovesJohn_website/shop/cart.py)
- [shop/models.py](/Users/johnjoseph/PycharmProjects/JosephlovesJohn_website/shop/models.py)
- [shop/forms.py](/Users/johnjoseph/PycharmProjects/JosephlovesJohn_website/shop/forms.py)
- [main_site/views.py](/Users/johnjoseph/PycharmProjects/JosephlovesJohn_website/main_site/views.py)
- [static/main_site/js/cart.js](/Users/johnjoseph/PycharmProjects/JosephlovesJohn_website/static/main_site/js/cart.js)
- [tests/test_shop_flow.py](/Users/johnjoseph/PycharmProjects/JosephlovesJohn_website/tests/test_shop_flow.py)
- [tests/test_browser_ui.py](/Users/johnjoseph/PycharmProjects/JosephlovesJohn_website/tests/test_browser_ui.py)
