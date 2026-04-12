"""Update demo music products to the new £1.00 pricing."""

from decimal import Decimal

from django.db import migrations, models


def update_music_product_prices(apps, schema_editor):
    """Apply the new £1.00 price to the seeded storefront products."""
    Product = apps.get_model("shop", "Product")
    Product.objects.filter(
        slug__in=[
            "dark-and-light-artist-version",
            "dark-and-light-instrumental",
        ]
    ).update(price=Decimal("1.00"))


def revert_music_product_prices(apps, schema_editor):
    """Restore the previous £2.99 price for the seeded storefront products."""
    Product = apps.get_model("shop", "Product")
    Product.objects.filter(
        slug__in=[
            "dark-and-light-artist-version",
            "dark-and-light-instrumental",
        ]
    ).update(price=Decimal("2.99"))


class Migration(migrations.Migration):
    """Move the seeded product catalog to the new default price."""

    dependencies = [("shop", "0002_seed_music_products")]

    operations = [
        migrations.AlterField(
            model_name="product",
            name="price",
            field=models.DecimalField(decimal_places=2, default=Decimal("1.00"), max_digits=6),
        ),
        migrations.RunPython(update_music_product_prices, revert_music_product_prices),
    ]
