"""Database models for the portfolio shop flow."""

from decimal import Decimal

from django.conf import settings
from django.db import models
from django.http import Http404
from django.urls import reverse
from django.utils import timezone
from josephlovesjohn_site.assets import public_asset_url

from .downloads import preview_asset_url


class Product(models.Model):
    """Represent a purchasable music download."""

    class ProductKind(models.TextChoices):
        """Supported storefront product types."""

        SINGLE = "single", "Single"
        BUNDLE = "bundle", "Bundle"
        ALBUM = "album", "Album"

    title = models.CharField(max_length=180)
    slug = models.SlugField(unique=True)
    artist_name = models.CharField(max_length=180, default="JosephlovesJohn and Jayne Connell")
    meta = models.CharField(max_length=120, blank=True)
    description = models.TextField(blank=True)
    art_path = models.CharField(max_length=255)
    art_alt = models.CharField(max_length=180, blank=True)
    preview_file_wav = models.CharField(max_length=255, blank=True)
    preview_file_mp3 = models.CharField(max_length=255, blank=True)
    download_file_path = models.CharField(max_length=255)
    download_file_wav_path = models.CharField(max_length=255, blank=True)
    product_kind = models.CharField(max_length=20, choices=ProductKind.choices, default=ProductKind.SINGLE)
    price = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("1.00"))
    sort_order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=True)
    is_reversed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Storefront ordering metadata."""

        ordering = ("sort_order", "id")

    def __str__(self):
        """Return the admin label for the product.

        :returns: Product title.
        :rtype: str
        """
        return self.title

    @property
    def player_id(self):
        """Return the unique front-end player identifier.

        :returns: DOM-safe player ID.
        :rtype: str
        """
        return f"shop-player-{self.slug}"

    @property
    def price_display(self):
        """Return the formatted product price.

        :returns: Human-friendly GBP amount.
        :rtype: str
        """
        return f"£{self.price:.2f}"

    def get_add_to_cart_url(self):
        """Return the cart endpoint for this product.

        :returns: Add-to-cart URL.
        :rtype: str
        """
        return reverse("shop:cart_add", kwargs={"slug": self.slug})

    @property
    def art_url(self):
        """Return the public artwork URL for storefront rendering."""
        return public_asset_url(self.art_path)

    @property
    def preview_wav_url(self):
        """Return a signed private WAV preview URL when configured."""
        if not self.preview_file_wav:
            return ""
        try:
            return preview_asset_url(self.preview_file_wav)
        except Http404:
            return public_asset_url(self.preview_file_wav)

    @property
    def preview_mp3_url(self):
        """Return a signed private MP3 preview URL when configured."""
        if not self.preview_file_mp3:
            return ""
        try:
            return preview_asset_url(self.preview_file_mp3)
        except Http404:
            return public_asset_url(self.preview_file_mp3)

    @property
    def download_url(self):
        """Return the public download URL for the product."""
        return public_asset_url(self.download_file_path)

    @property
    def download_wav_url(self):
        """Return the public WAV download URL for the product when available."""
        if not self.download_file_wav_path:
            return ""
        return public_asset_url(self.download_file_wav_path)

    @property
    def download_asset_paths(self):
        """Return every deliverable file path that should exist for this product."""
        return [path for path in (self.download_file_path, self.download_file_wav_path) if path]


class CustomerProfile(models.Model):
    """Persist optional saved customer details for logged-in shoppers."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="shop_profile")
    full_name = models.CharField(max_length=180, blank=True)
    marketing_opt_in = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        """Return an admin-friendly profile label.

        :returns: Profile label.
        :rtype: str
        """
        return self.full_name or self.user.get_username()


class Order(models.Model):
    """Store a completed checkout."""

    class Status(models.TextChoices):
        """Supported demo order statuses."""

        PENDING = "pending", "Pending payment"
        CONFIRMED = "confirmed", "Confirmed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="shop_orders",
    )
    full_name = models.CharField(max_length=180)
    email = models.EmailField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CONFIRMED)
    subtotal = models.DecimalField(max_digits=8, decimal_places=2)
    total = models.DecimalField(max_digits=8, decimal_places=2)
    notes = models.TextField(blank=True)
    stripe_checkout_session_id = models.CharField(max_length=255, blank=True)
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    confirmation_email_sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Newest orders first for account views and admin."""

        ordering = ("-created_at", "-id")

    def __str__(self):
        """Return the admin label for the order.

        :returns: Readable order label.
        :rtype: str
        """
        return f"Order #{self.pk} - {self.full_name}"

    @property
    def total_display(self):
        """Return the formatted order total.

        :returns: Human-friendly GBP amount.
        :rtype: str
        """
        return f"£{self.total:.2f}"

    @property
    def is_paid(self):
        """Return whether the order has a confirmed Stripe payment."""

        return self.status == self.Status.CONFIRMED

    def mark_paid(self, *, payment_intent_id=""):
        """Mark the order as paid after Stripe confirms the checkout session."""

        self.status = self.Status.CONFIRMED
        self.stripe_payment_intent_id = payment_intent_id
        if self.paid_at is None:
            self.paid_at = timezone.now()


class OrderItem(models.Model):
    """Snapshot a purchased product within an order."""

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="order_items")
    title_snapshot = models.CharField(max_length=180)
    artist_snapshot = models.CharField(max_length=180)
    meta_snapshot = models.CharField(max_length=120, blank=True)
    price_snapshot = models.DecimalField(max_digits=6, decimal_places=2)
    art_path_snapshot = models.CharField(max_length=255)
    art_alt_snapshot = models.CharField(max_length=180, blank=True)
    download_file_path = models.CharField(max_length=255)
    download_file_wav_path = models.CharField(max_length=255, blank=True)

    def __str__(self):
        """Return the admin label for the order line.

        :returns: Order line label.
        :rtype: str
        """
        return f"{self.title_snapshot} ({self.order_id})"

    @property
    def price_display(self):
        """Return the formatted line-item price.

        :returns: Human-friendly GBP amount.
        :rtype: str
        """
        return f"£{self.price_snapshot:.2f}"

    @property
    def title(self):
        """Return the reusable item title for shared templates.

        :returns: Snapshot title.
        :rtype: str
        """
        return self.title_snapshot

    @property
    def artist_name(self):
        """Return the reusable artist label for shared templates.

        :returns: Snapshot artist label.
        :rtype: str
        """
        return self.artist_snapshot

    @property
    def meta(self):
        """Return the reusable metadata label for shared templates.

        :returns: Snapshot metadata label.
        :rtype: str
        """
        return self.meta_snapshot

    @property
    def art_path(self):
        """Return the reusable artwork path for shared templates.

        :returns: Snapshot artwork path.
        :rtype: str
        """
        return self.art_path_snapshot

    @property
    def art_alt(self):
        """Return the reusable artwork alt text for shared templates.

        :returns: Snapshot artwork alt text.
        :rtype: str
        """
        return self.art_alt_snapshot

    @property
    def art_url(self):
        """Return the public artwork URL for summary rendering."""
        return public_asset_url(self.art_path_snapshot)

    @property
    def download_url(self):
        """Return the protected application download URL for the purchased file."""
        return reverse("shop:download", kwargs={"item_id": self.pk})

    @property
    def download_wav_url(self):
        """Return the protected application download URL for the purchased WAV file."""
        if not self.download_file_wav_path:
            return ""
        return f'{reverse("shop:download", kwargs={"item_id": self.pk})}?format=wav'

    @property
    def download_links(self):
        """Return the available protected download links for this purchased item."""
        links = [{"label": "MP3", "url": self.download_url}]
        if self.download_file_wav_path:
            links.append({"label": "WAV", "url": self.download_wav_url})
        return links

    def download_file_for_format(self, format_name: str):
        """Return the snapshot path for a requested download format."""
        if format_name == "wav":
            return self.download_file_wav_path
        if format_name == "mp3":
            return self.download_file_path
        return ""
