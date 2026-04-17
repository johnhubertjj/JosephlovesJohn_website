"""URL patterns for the reusable shop flow."""

from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from .views import (
    AccountView,
    CheckoutView,
    OrderDownloadView,
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
    path("download/<int:item_id>/", OrderDownloadView.as_view(), name="download"),
    path("success/<int:order_id>/", OrderSuccessView.as_view(), name="success"),
    path("login/", ShopLoginView.as_view(), name="login"),
    path("logout/", ShopLogoutView.as_view(), name="logout"),
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="shop/password_reset_form.html",
            email_template_name="shop/emails/password_reset_email.txt",
            subject_template_name="shop/emails/password_reset_subject.txt",
            success_url=reverse_lazy("shop:password_reset_done"),
        ),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(template_name="shop/password_reset_done.html"),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="shop/password_reset_confirm.html",
            success_url=reverse_lazy("shop:password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/complete/",
        auth_views.PasswordResetCompleteView.as_view(template_name="shop/password_reset_complete.html"),
        name="password_reset_complete",
    ),
    path("register/", RegisterView.as_view(), name="register"),
    path("account/", AccountView.as_view(), name="account"),
]
