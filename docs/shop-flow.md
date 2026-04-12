# Shop Flow

This document maps the current shop implementation in the Django app.

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
    H --> I["Checkout page shows form and order summary"]
    I --> J["User submits customer details"]
    J --> K["POST /shop/checkout/"]
    K --> L["Order created"]
    L --> M["OrderItem snapshots created"]
    M --> N["Session cart cleared"]
    N --> O["Redirect to /shop/success/&lt;order_id&gt;/"]
    O --> P["Success page shows download links"]
    P --> Q{"Logged-in user?"}
    Q -- Yes --> R["Order also appears in /shop/account/"]
    Q -- No --> S["Guest can revisit only from same session"]
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
    participant Success as shop.views.OrderSuccessView

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
    Checkout-->>User: Render form and order summary

    User->>Checkout: Submit checkout form
    Checkout->>Cart: get_cart_products(request)
    Checkout->>Order: create order
    loop For each product in cart
        Checkout->>OrderItem: create snapshot row
    end
    Checkout->>Cart: clear_cart(request)
    Checkout-->>Success: Redirect to success page

    User->>Success: Open /shop/success/<order_id>/
    Success->>Order: load order and items
    Success-->>User: Show downloads
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
        +price
        +is_published
        +price_display()
        +get_add_to_cart_url()
    }

    class CustomerProfile {
        +user
        +full_name
        +marketing_opt_in
    }

    class Order {
        +user
        +full_name
        +email
        +status
        +subtotal
        +total
        +notes
        +created_at
        +total_display()
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
    class cart_add
    class cart_remove

    Order "1" --> "*" OrderItem
    Product "1" --> "*" OrderItem
    CustomerProfile --> "1" Order : via authenticated user
    CheckoutView ..> CartHelpers
    CheckoutView ..> Order
    CheckoutView ..> OrderItem
    OrderSuccessView ..> Order
    AccountView ..> Order
    cart_add ..> Product
    cart_add ..> CartHelpers
    cart_remove ..> Product
    cart_remove ..> CartHelpers
```

## Main Files

- [shop/views.py](/Users/johnjoseph/PycharmProjects/JosephlovesJohn_website/shop/views.py)
- [shop/cart.py](/Users/johnjoseph/PycharmProjects/JosephlovesJohn_website/shop/cart.py)
- [shop/models.py](/Users/johnjoseph/PycharmProjects/JosephlovesJohn_website/shop/models.py)
- [main_site/views.py](/Users/johnjoseph/PycharmProjects/JosephlovesJohn_website/main_site/views.py)
- [static/main_site/js/cart.js](/Users/johnjoseph/PycharmProjects/JosephlovesJohn_website/static/main_site/js/cart.js)
- [tests/test_shop_flow.py](/Users/johnjoseph/PycharmProjects/JosephlovesJohn_website/tests/test_shop_flow.py)
- [tests/test_browser_ui.py](/Users/johnjoseph/PycharmProjects/JosephlovesJohn_website/tests/test_browser_ui.py)
