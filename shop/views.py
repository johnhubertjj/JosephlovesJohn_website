"""Views for the demo music shop experience."""

from decimal import Decimal
from http import HTTPStatus
from typing import Any, cast

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView
from django.core.exceptions import ImproperlyConfigured
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic import FormView, TemplateView

from .cart import add_product, build_cart_summary, clear_cart, get_cart_products, remove_product
from .downloads import build_download_response
from .forms import CheckoutConsentForm, RegisterForm, ShopAuthenticationForm
from .models import CustomerProfile, Order, OrderItem, Product

stripe: Any | None = None

try:
    import stripe as stripe_sdk
except ImportError:  # pragma: no cover - exercised only when Stripe is not installed.
    pass
else:
    stripe = stripe_sdk


def _get_stripe_module():
    """Return the configured Stripe SDK module."""

    if stripe is None:
        raise ImproperlyConfigured("Stripe is not installed. Add the stripe package before enabling checkout.")
    if not settings.STRIPE_SECRET_KEY:
        raise ImproperlyConfigured("Set STRIPE_SECRET_KEY before using the hosted payment page.")

    stripe.api_key = settings.STRIPE_SECRET_KEY
    stripe.api_version = settings.STRIPE_API_VERSION
    return stripe


def _stripe_value(value, key, default=None):
    """Safely read a field from Stripe responses or test doubles."""

    if value is None:
        return default
    if isinstance(value, dict):
        return value.get(key, default)
    data = getattr(value, "_data", None)
    if isinstance(data, dict):
        return data.get(key, default)

    try:
        return value[key]
    except (KeyError, TypeError, IndexError):
        pass

    try:
        return getattr(value, key)
    except AttributeError:
        return default


def _stripe_mapping(value):
    """Normalize Stripe metadata/details objects to plain dictionaries."""

    if value is None:
        return {}
    if isinstance(value, dict):
        return value

    data = getattr(value, "_data", None)
    if isinstance(data, dict):
        return data

    return {}


def _stripe_identifier(value):
    """Normalize Stripe expandable IDs to a string."""

    if isinstance(value, str):
        return value
    return _stripe_value(value, "id", "")


def _remember_recent_order(request, order_id):
    """Persist a recently-paid order in the visitor's session."""

    recent_orders = request.session.get("shop_recent_orders", [])
    request.session["shop_recent_orders"] = [
        order_id,
        *[value for value in recent_orders if value != order_id],
    ][:10]
    request.session.modified = True


def _ensure_user_can_access(request, order):
    """Restrict authenticated orders to the owning user."""
    if order.user_id and (
        not request.user.is_authenticated or order.user_id != request.user.id
    ):
        raise Http404("Order not found")


def _ensure_guest_session_can_access(request, order):
    """Restrict guest orders to the session that completed payment."""
    if order.user_id:
        return

    allowed_orders = request.session.get("shop_recent_orders", [])
    if order.pk not in allowed_orders:
        raise Http404("Order not found")


def _sync_customer_profile_from_order(order):
    """Save confirmed Stripe customer details back to the logged-in profile."""
    if not order.user_id:
        return

    profile, _ = CustomerProfile.objects.get_or_create(user=order.user)
    profile.full_name = order.full_name
    profile.marketing_opt_in = profile.marketing_opt_in
    profile.save(update_fields=["full_name", "marketing_opt_in", "updated_at"])

    if order.email and order.email != order.user.email:
        order.user.email = order.email
        order.user.save(update_fields=["email"])


def _apply_paid_checkout_session_to_order(order, checkout_session):
    """Mark an order as paid when Stripe confirms a matching Checkout session."""
    metadata = _stripe_mapping(_stripe_value(checkout_session, "metadata", {}))
    if (
        _stripe_value(checkout_session, "status") != "complete"
        or _stripe_value(checkout_session, "payment_status") != "paid"
        or metadata.get("order_id") != str(order.pk)
    ):
        raise Http404("Order not found")

    customer_details = _stripe_mapping(_stripe_value(checkout_session, "customer_details", {}))
    customer_name = customer_details.get("name") or order.full_name
    customer_email = (
        customer_details.get("email")
        or _stripe_value(checkout_session, "customer_email")
        or order.email
    )
    update_fields: list[str] = []

    if customer_name != order.full_name:
        order.full_name = customer_name
        update_fields.append("full_name")
    if customer_email != order.email:
        order.email = customer_email
        update_fields.append("email")

    was_paid = order.is_paid
    order.mark_paid(payment_intent_id=_stripe_identifier(_stripe_value(checkout_session, "payment_intent")))
    if order.status != Order.Status.CONFIRMED or "status" not in update_fields:
        update_fields.extend(["status", "stripe_payment_intent_id", "paid_at"])

    if order.user_id:
        _sync_customer_profile_from_order(order)
    order.save(update_fields=list(dict.fromkeys(update_fields)))
    return not was_paid


def _fulfill_checkout_session(checkout_session):
    """Confirm an order from a Stripe Checkout session payload."""
    metadata = _stripe_mapping(_stripe_value(checkout_session, "metadata", {}))
    order_id = metadata.get("order_id")
    session_id = _stripe_value(checkout_session, "id", "")
    if not order_id or not session_id:
        return None

    order = (
        Order.objects.filter(pk=order_id, stripe_checkout_session_id=session_id)
        .select_related("user")
        .first()
    )
    if order is None:
        return None

    _apply_paid_checkout_session_to_order(order, checkout_session)
    return order


class ShopLoginView(LoginView):
    """Render the login page for returning listeners."""

    template_name = "shop/login.html"
    authentication_form = ShopAuthenticationForm

    def get_success_url(self):
        """Return the next page after login.

        :returns: Redirect URL after login.
        :rtype: str
        """
        return self.get_redirect_url() or reverse("shop:account")


class ShopLogoutView(View):
    """Log the user out and return them to the main music page."""

    def get(self, request):
        """Log out the current user via a simple GET request.

        :param request: Current HTTP request.
        :type request: django.http.HttpRequest
        :returns: Redirect back to the music page.
        :rtype: django.http.HttpResponseRedirect
        """
        logout(request)
        messages.info(request, "You have been logged out.")
        return redirect("main_site:music")


class RegisterView(FormView):
    """Create a reusable storefront account."""

    template_name = "shop/register.html"
    form_class = RegisterForm
    success_url = reverse_lazy("shop:account")

    def get_success_url(self):
        """Return the next page after account creation.

        :returns: Redirect URL after registration.
        :rtype: str
        """
        return self.request.GET.get("next") or super().get_success_url()

    def form_valid(self, form):
        """Persist the new account and profile.

        :param form: Valid registration form.
        :type form: shop.forms.RegisterForm
        :returns: Redirect response.
        :rtype: django.http.HttpResponse
        """
        user = form.save(commit=False)
        user.email = form.cleaned_data["email"]
        user.save()
        CustomerProfile.objects.update_or_create(
            user=user,
            defaults={"full_name": form.cleaned_data["full_name"]},
        )
        login(self.request, user)
        messages.success(self.request, "Your account is ready. You can now keep track of your purchases here.")
        return super().form_valid(form)


class AccountView(LoginRequiredMixin, TemplateView):
    """Show saved customer details and previous orders."""

    template_name = "shop/account.html"
    login_url = reverse_lazy("shop:login")

    def get_context_data(self, **kwargs):
        """Build the account dashboard context.

        :param kwargs: Parent context data.
        :type kwargs: dict[str, object]
        :returns: Account page context.
        :rtype: dict[str, object]
        """
        context = super().get_context_data(**kwargs)
        user = cast(User, self.request.user)
        profile, _ = CustomerProfile.objects.get_or_create(user=user)
        context.update(
            {
                "profile": profile,
                "orders": Order.objects.filter(
                    user=user,
                    status=Order.Status.CONFIRMED,
                ).prefetch_related("items", "items__product"),
            }
        )
        return context


class CheckoutView(View):
    """Launch Stripe Checkout for the current cart."""

    template_name = "shop/checkout.html"

    def _get_checkout_products(self, request):
        """Return the current cart products for checkout processing."""

        return get_cart_products(request)

    def _redirect_empty_cart(self, request):
        """Return the standard empty-cart redirect response."""

        messages.info(request, "Your cart is empty. Add a track from the music page to continue.")
        return redirect("main_site:music")

    def _render_checkout(
        self,
        request,
        products,
        *,
        form=None,
        checkout_error="",
        checkout_canceled=False,
    ):
        """Render the checkout template with a normalized context."""

        return render(
            request,
            self.template_name,
            self._context(
                products,
                form=form or CheckoutConsentForm(),
                checkout_error=checkout_error,
                checkout_canceled=checkout_canceled,
            ),
        )

    def get(self, request):
        """Start Stripe Checkout or render a fallback page if needed.

        :param request: Current HTTP request.
        :type request: django.http.HttpRequest
        :returns: Checkout page response.
        :rtype: django.http.HttpResponse
        """
        products = self._get_checkout_products(request)
        if not products:
            return self._redirect_empty_cart(request)

        if request.GET.get("canceled"):
            messages.info(request, "Checkout was canceled, so your cart is still waiting for you.")
            return self._render_checkout(request, products, checkout_canceled=True)

        return self._render_checkout(request, products)

    def post(self, request):
        """Start Stripe Checkout from a form POST as a compatibility fallback.

        :param request: Current HTTP request.
        :type request: django.http.HttpRequest
        :returns: Redirect or rendered error response.
        :rtype: django.http.HttpResponse
        """
        products = self._get_checkout_products(request)
        if not products:
            return self._redirect_empty_cart(request)

        form = CheckoutConsentForm(request.POST)
        if not form.is_valid():
            return self._render_checkout(request, products, form=form)

        return self._start_checkout(request, products, form=form)

    def _start_checkout(self, request, products, *, form=None):
        """Create the pending order and redirect to Stripe Checkout."""

        order = self._build_order(request, products)

        try:
            checkout_session = self._create_checkout_session(request, order)
        except ImproperlyConfigured as exc:
            order.delete()
            return self._render_checkout(request, products, form=form, checkout_error=str(exc))
        except Exception:
            order.delete()
            return self._render_checkout(
                request,
                products,
                form=form,
                checkout_error="Stripe checkout could not be started right now. Please try again in a moment.",
            )

        order.stripe_checkout_session_id = _stripe_value(checkout_session, "id", "")
        order.save(update_fields=["stripe_checkout_session_id"])
        return redirect(_stripe_value(checkout_session, "url"))

    def _build_order(self, request, products):
        """Create a pending order from the current cart contents."""

        subtotal = sum((product.price for product in products), Decimal("0.00"))
        user = request.user if request.user.is_authenticated else None
        full_name, email = self._get_customer_defaults(request)
        order = Order.objects.create(
            user=user,
            full_name=full_name,
            email=email,
            subtotal=subtotal,
            total=subtotal,
            notes="",
            status=Order.Status.PENDING,
        )

        for product in products:
            OrderItem.objects.create(
                order=order,
                product=product,
                title_snapshot=product.title,
                artist_snapshot=product.artist_name,
                meta_snapshot=product.meta,
                price_snapshot=product.price,
                art_path_snapshot=product.art_path,
                art_alt_snapshot=product.art_alt,
                download_file_path=product.download_file_path,
            )

        return order

    def _get_customer_defaults(self, request):
        """Build the initial customer details that can be sent to Stripe."""

        user = request.user
        if not user.is_authenticated:
            return "Guest checkout", ""

        profile, _ = CustomerProfile.objects.get_or_create(user=user)
        full_name = profile.full_name or user.get_full_name() or user.username
        return full_name, user.email

    def _create_checkout_session(self, request, order):
        """Create the hosted Stripe Checkout session for the pending order."""

        stripe_module = _get_stripe_module()
        success_url = request.build_absolute_uri(reverse("shop:success", kwargs={"order_id": order.pk}))
        cancel_url = request.build_absolute_uri(reverse("shop:checkout"))
        currency = settings.STRIPE_CURRENCY

        line_items = []
        for item in order.items.all():
            unit_amount = int(item.price_snapshot * 100)
            line_items.append(
                {
                    "price_data": {
                        "currency": currency,
                        "product_data": {
                            "name": item.title_snapshot,
                            "description": item.meta_snapshot or item.artist_snapshot,
                        },
                        "unit_amount": unit_amount,
                    },
                    "quantity": 1,
                }
            )

        session_kwargs = {
            "mode": "payment",
            "success_url": f"{success_url}?session_id={{CHECKOUT_SESSION_ID}}",
            "cancel_url": f"{cancel_url}?canceled=1",
            "metadata": {"order_id": str(order.pk)},
            "payment_intent_data": {"metadata": {"order_id": str(order.pk)}},
            "line_items": line_items,
        }
        if order.email:
            session_kwargs["customer_email"] = order.email

        return stripe_module.checkout.Session.create(**session_kwargs)

    def _context(self, products, *, form, checkout_error="", checkout_canceled=False):
        """Build the checkout rendering context.

        :param products: Products in the cart.
        :type products: list[shop.models.Product]
        :returns: Checkout template context.
        :rtype: dict[str, object]
        """
        subtotal = sum((product.price for product in products), Decimal("0.00"))
        return {
            "checkout_items": products,
            "checkout_analytics": {
                "item_count": len(products),
                "total_amount": f"{subtotal:.2f}",
            },
            "checkout_subtotal_display": f"£{subtotal:.2f}",
            "form": form,
            "checkout_error": checkout_error,
            "checkout_canceled": checkout_canceled,
        }


class OrderSuccessView(TemplateView):
    """Show the completed order and digital downloads."""

    template_name = "shop/success.html"

    def get_context_data(self, **kwargs):
        """Build the success-page context.

        :param kwargs: URL kwargs including the order ID.
        :type kwargs: dict[str, object]
        :returns: Success page context.
        :rtype: dict[str, object]
        :raises Http404: If the order should not be visible to the current user.
        """
        context = super().get_context_data(**kwargs)
        order = get_object_or_404(Order.objects.prefetch_related("items", "items__product"), pk=kwargs["order_id"])
        _ensure_user_can_access(self.request, order)
        if self.request.GET.get("session_id"):
            self._synchronize_checkout_session(order)
        elif not order.is_paid:
            raise Http404("Order not found")
        _ensure_guest_session_can_access(self.request, order)
        context["order"] = order
        context["purchase_analytics"] = {
            "order_id": str(order.pk),
            "item_count": order.items.count(),
            "total_amount": f"{order.total:.2f}",
            "product_titles": ", ".join(item.title_snapshot for item in order.items.all()),
        }
        return context

    def _synchronize_checkout_session(self, order):
        """Verify the returned Stripe session and unlock the download page."""

        session_id = self.request.GET.get("session_id", "")
        if not session_id or session_id != order.stripe_checkout_session_id:
            raise Http404("Order not found")

        stripe_module = _get_stripe_module()
        checkout_session = stripe_module.checkout.Session.retrieve(
            session_id,
            expand=["payment_intent"],
        )
        order_was_just_confirmed = _apply_paid_checkout_session_to_order(order, checkout_session)
        clear_cart(self.request)
        _remember_recent_order(self.request, order.pk)
        if order_was_just_confirmed:
            messages.success(self.request, "Payment confirmed. Your music is ready below.")


class OrderDownloadView(View):
    """Deliver a purchased file to an authorized customer."""

    def get(self, request, item_id):
        """Redirect to a signed download URL or stream a local private file."""
        item = get_object_or_404(OrderItem.objects.select_related("order"), pk=item_id)
        order = item.order
        _ensure_user_can_access(request, order)
        _ensure_guest_session_can_access(request, order)
        download_name = item.download_file_path.rsplit("/", 1)[-1] or f"order-{order.pk}-download"
        response = build_download_response(item.download_file_path, download_name=download_name)
        if isinstance(response, FileResponse):
            return response
        return response


@method_decorator(csrf_exempt, name="dispatch")
class StripeWebhookView(View):
    """Receive Stripe webhook events for Checkout fulfillment."""

    http_method_names = ["post"]

    def post(self, request):
        """Verify and handle signed Stripe webhook payloads."""
        if not settings.STRIPE_WEBHOOK_SECRET:
            return HttpResponse(status=HTTPStatus.BAD_REQUEST)

        stripe_module = _get_stripe_module()
        signature = request.headers.get("Stripe-Signature", "")
        try:
            event = stripe_module.Webhook.construct_event(
                payload=request.body,
                sig_header=signature,
                secret=settings.STRIPE_WEBHOOK_SECRET,
            )
        except Exception:
            return HttpResponse(status=HTTPStatus.BAD_REQUEST)

        event_type = _stripe_value(event, "type", "")
        event_data = _stripe_value(event, "data", {}) or {}
        checkout_session = _stripe_value(event_data, "object")

        if event_type in {"checkout.session.completed", "checkout.session.async_payment_succeeded"}:
            try:
                _fulfill_checkout_session(checkout_session)
            except Http404:
                pass

        return HttpResponse(status=HTTPStatus.OK)


@require_POST
def cart_add(request, slug):
    """Add the requested product to the session cart.

    :param request: Current HTTP request.
    :type request: django.http.HttpRequest
    :param slug: Product slug.
    :type slug: str
    :returns: JSON cart summary.
    :rtype: django.http.JsonResponse
    """
    product = get_object_or_404(Product, slug=slug, is_published=True)
    add_product(request, product)
    return JsonResponse(build_cart_summary(request))


@require_POST
def cart_remove(request, slug):
    """Remove the requested product from the session cart.

    :param request: Current HTTP request.
    :type request: django.http.HttpRequest
    :param slug: Product slug.
    :type slug: str
    :returns: JSON cart summary.
    :rtype: django.http.JsonResponse
    """
    product = get_object_or_404(Product, slug=slug, is_published=True)
    remove_product(request, product)
    return JsonResponse(build_cart_summary(request))
