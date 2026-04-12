"""Seed the initial music products used by the storefront demo."""

from decimal import Decimal

from django.db import migrations

PRODUCT_SEED_DATA = (
    {
        "title": "Dark and Light - Artist Version",
        "slug": "dark-and-light-artist-version",
        "artist_name": "JosephlovesJohn and Jayne Connell",
        "meta": "Single",
        "description": "Original artist version of Dark and Light.",
        "art_path": "images/album_art/dark_and_light_artist_cover.jpg",
        "art_alt": "Dark and Light artist cover artwork",
        "preview_file_wav": "audio/dark_and_light_final_full_mastered_new_deesser3_24bit_192khz_JJ.wav",
        "preview_file_mp3": "audio/dark_and_light_final_full_mastered_new_deesser3_24bit_192khz_JJ.mp3",
        "download_file_path": "audio/dark_and_light_final_full_mastered_new_deesser3_24bit_192khz_JJ.mp3",
        "price": Decimal("2.99"),
        "sort_order": 1,
        "is_reversed": False,
    },
    {
        "title": "Dark and Light - Instrumental",
        "slug": "dark-and-light-instrumental",
        "artist_name": "JosephlovesJohn and Jayne Connell",
        "meta": "Instrumental Mix",
        "description": "Instrumental mix of Dark and Light.",
        "art_path": "images/album_art/dark_and_light_instrumental.jpg",
        "art_alt": "Dark and Light instrumental artwork",
        "preview_file_wav": "audio/dark_and_light_final_instrumental_v3_24_192.wav",
        "preview_file_mp3": "audio/dark_and_light_final_instrumental_v3_24_192.mp3",
        "download_file_path": "audio/dark_and_light_final_instrumental_v3_24_192.mp3",
        "price": Decimal("2.99"),
        "sort_order": 2,
        "is_reversed": True,
    },
)


def seed_music_products(apps, schema_editor):
    """Create the initial storefront products if they do not already exist.

    :param apps: Historical app registry.
    :type apps: django.apps.registry.Apps
    :param schema_editor: Active schema editor.
    :type schema_editor: django.db.backends.base.schema.BaseDatabaseSchemaEditor
    :returns: ``None``.
    :rtype: None
    """
    Product = apps.get_model("shop", "Product")
    for payload in PRODUCT_SEED_DATA:
        Product.objects.update_or_create(slug=payload["slug"], defaults=payload)


def remove_music_products(apps, schema_editor):
    """Remove the seeded storefront products.

    :param apps: Historical app registry.
    :type apps: django.apps.registry.Apps
    :param schema_editor: Active schema editor.
    :type schema_editor: django.db.backends.base.schema.BaseDatabaseSchemaEditor
    :returns: ``None``.
    :rtype: None
    """
    Product = apps.get_model("shop", "Product")
    Product.objects.filter(slug__in=[item["slug"] for item in PRODUCT_SEED_DATA]).delete()


class Migration(migrations.Migration):
    """Seed the initial shop catalog."""

    dependencies = [("shop", "0001_initial")]

    operations = [migrations.RunPython(seed_music_products, remove_music_products)]
