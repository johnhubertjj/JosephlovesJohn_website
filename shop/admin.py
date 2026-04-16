"""Admin configuration for the shop models."""

from django.contrib import admin

from .models import CustomerProfile, Order, OrderItem, Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """Manage storefront products in Django admin."""

    list_display = ("title", "product_kind", "price", "sort_order", "is_published")
    list_editable = ("sort_order", "is_published")
    list_filter = ("product_kind", "is_published")
    prepopulated_fields = {"slug": ("title",)}
    search_fields = ("title", "artist_name")
    ordering = ("sort_order", "id")


class OrderItemInline(admin.TabularInline):
    """Show purchased lines inline on the order admin page."""

    model = OrderItem
    extra = 0
    readonly_fields = ("product", "title_snapshot", "artist_snapshot", "price_snapshot", "download_file_path")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Inspect completed demo orders."""

    list_display = ("id", "full_name", "email", "status", "total", "confirmation_email_sent_at", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("full_name", "email")
    readonly_fields = (
        "user",
        "full_name",
        "email",
        "status",
        "subtotal",
        "total",
        "notes",
        "confirmation_email_sent_at",
        "created_at",
    )
    inlines = (OrderItemInline,)


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    """Manage saved customer details."""

    list_display = ("user", "full_name", "marketing_opt_in", "updated_at")
    search_fields = ("user__username", "user__email", "full_name")
