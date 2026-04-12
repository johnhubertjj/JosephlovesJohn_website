"""Views for the demo music shop experience."""

from decimal import Decimal
from typing import cast

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.decorators.http import require_POST
from django.views.generic import FormView, TemplateView

from .cart import add_product, build_cart_summary, clear_cart, get_cart_products, remove_product
from .forms import CheckoutForm, RegisterForm, ShopAuthenticationForm
from .models import CustomerProfile, Order, OrderItem, Product


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
                "orders": Order.objects.filter(user=user).prefetch_related("items", "items__product"),
            }
        )
        return context


class CheckoutView(View):
    """Collect customer details and create a demo order."""

    template_name = "shop/checkout.html"

    def get_form_initial(self):
        """Build the initial checkout form values.

        :returns: Initial form values.
        :rtype: dict[str, object]
        """
        initial: dict[str, object] = {}
        user = self.request.user
        if user.is_authenticated:
            profile, _ = CustomerProfile.objects.get_or_create(user=user)
            initial["full_name"] = profile.full_name or user.get_full_name() or user.username
            initial["email"] = user.email
            initial["save_details"] = True
        return initial

    def get(self, request):
        """Render the checkout page.

        :param request: Current HTTP request.
        :type request: django.http.HttpRequest
        :returns: Checkout page response.
        :rtype: django.http.HttpResponse
        """
        products = get_cart_products(request)
        if not products:
            messages.info(request, "Your cart is empty. Add a track from the music page to continue.")
            return redirect("main_site:music")

        form = CheckoutForm(initial=self.get_form_initial())
        return render(request, self.template_name, self._context(form, products))

    def post(self, request):
        """Create an order from the current cart.

        :param request: Current HTTP request.
        :type request: django.http.HttpRequest
        :returns: Redirect or rendered error response.
        :rtype: django.http.HttpResponse
        """
        products = get_cart_products(request)
        if not products:
            messages.info(request, "Your cart is empty. Add a track from the music page to continue.")
            return redirect("main_site:music")

        form = CheckoutForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, self._context(form, products))

        subtotal = sum((product.price for product in products), Decimal("0.00"))
        user = request.user if request.user.is_authenticated else None
        order = Order.objects.create(
            user=user,
            full_name=form.cleaned_data["full_name"],
            email=form.cleaned_data["email"],
            subtotal=subtotal,
            total=subtotal,
            notes=form.cleaned_data["notes"],
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

        if user and form.cleaned_data["save_details"]:
            profile, _ = CustomerProfile.objects.get_or_create(user=user)
            profile.full_name = form.cleaned_data["full_name"]
            profile.marketing_opt_in = profile.marketing_opt_in
            profile.save(update_fields=["full_name", "marketing_opt_in", "updated_at"])
            if form.cleaned_data["email"] != user.email:
                user.email = form.cleaned_data["email"]
                user.save(update_fields=["email"])

        clear_cart(request)
        recent_orders = request.session.get("shop_recent_orders", [])
        request.session["shop_recent_orders"] = [
            order.pk,
            *[value for value in recent_orders if value != order.pk],
        ][:10]
        request.session.modified = True
        messages.success(request, "Order confirmed. Your music is ready below.")
        return redirect("shop:success", order_id=order.pk)

    def _context(self, form, products):
        """Build the checkout rendering context.

        :param form: Checkout form instance.
        :type form: shop.forms.CheckoutForm
        :param products: Products in the cart.
        :type products: list[shop.models.Product]
        :returns: Checkout template context.
        :rtype: dict[str, object]
        """
        subtotal = sum((product.price for product in products), Decimal("0.00"))
        return {
            "form": form,
            "checkout_items": products,
            "checkout_subtotal_display": f"£{subtotal:.2f}",
            "login_url": reverse("shop:login"),
            "register_url": reverse("shop:register"),
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
        if order.user_id:
            if not self.request.user.is_authenticated or order.user_id != self.request.user.id:
                raise Http404("Order not found")
        else:
            allowed_orders = self.request.session.get("shop_recent_orders", [])
            if order.pk not in allowed_orders:
                raise Http404("Order not found")
        context["order"] = order
        return context


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
