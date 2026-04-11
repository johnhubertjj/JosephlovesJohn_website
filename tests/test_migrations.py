"""Regression tests for the gallery seed and normalization migrations."""

from importlib import import_module

import pytest
from django.apps import apps as django_apps
from main_site.models import GigPhoto

migration_0001 = import_module("main_site.migrations.0001_initial")
migration_0002 = import_module("main_site.migrations.0002_normalize_gig_photo_titles")

pytestmark = [pytest.mark.django_db, pytest.mark.integration]



def test_seed_gig_photos_populates_defaults_once() -> None:
    """The initial gallery seed should populate the default rows without duplicating them."""
    GigPhoto.objects.all().delete()

    migration_0001.seed_gig_photos(django_apps, None)
    first_pass_titles = list(GigPhoto.objects.order_by("sort_order").values_list("title", flat=True))

    migration_0001.seed_gig_photos(django_apps, None)

    assert GigPhoto.objects.count() == 12
    assert first_pass_titles[0] == "Sofa Session 01"
    assert first_pass_titles[-1] == "Bristol Folk House 31 03 2026 - 9"
    assert list(GigPhoto.objects.order_by("sort_order").values_list("title", flat=True)) == first_pass_titles



def test_normalize_titles_updates_seeded_gallery_labels() -> None:
    """The title-normalization migration should collapse seeded titles to display labels."""
    GigPhoto.objects.all().delete()
    GigPhoto.objects.create(
        title="Sofa Session 03",
        image_path="images/gig_photos/sofa_photos3.jpeg",
        thumbnail_path="images/gig_photos/sofa_photos3.jpeg",
        alt_text="Sofa alt",
        sort_order=10,
    )
    GigPhoto.objects.create(
        title="Bristol Folk House 31 03 2026 - 4",
        image_path="images/gig_photos/Bristol_folk_house_31_03_2026_4.jpeg",
        thumbnail_path="images/gig_photos/thumbs/Bristol_folk_house_31_03_2026_4_thumb.jpg",
        alt_text="Bristol alt",
        sort_order=20,
    )
    GigPhoto.objects.create(
        title="Leave Alone",
        image_path="images/gig_photos/custom.jpg",
        thumbnail_path="",
        alt_text="Custom alt",
        sort_order=30,
    )

    migration_0002.normalize_titles(django_apps, None)

    titles = list(GigPhoto.objects.order_by("sort_order").values_list("title", flat=True))
    assert titles == [
        "Sofa Session",
        "Bristol Folk House 31 03 2026",
        "Leave Alone",
    ]
