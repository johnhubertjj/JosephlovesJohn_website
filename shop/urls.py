"""URL patterns for the reusable shop flow."""

from django.urls import path

from .views import (
    AccountView,
    CheckoutView,
    OrderSuccessView,
    RegisterView,
    ShopLoginView,
    ShopLogoutView,
    StripeWebhookView,
    cart_add,
    cart_remove,
)

app_name = "shop"

urlpatterns = [
    path("cart/add/<slug:slug>/", cart_add, name="cart_add"),
    path("cart/remove/<slug:slug>/", cart_remove, name="cart_remove"),
    path("checkout/", CheckoutView.as_view(), name="checkout"),
    path("stripe/webhook/", StripeWebhookView.as_view(), name="stripe_webhook"),
    path("success/<int:order_id>/", OrderSuccessView.as_view(), name="success"),
    path("login/", ShopLoginView.as_view(), name="login"),
    path("logout/", ShopLogoutView.as_view(), name="logout"),
    path("register/", RegisterView.as_view(), name="register"),
    path("account/", AccountView.as_view(), name="account"),
]
