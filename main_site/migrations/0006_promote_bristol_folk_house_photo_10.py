"""Promote the Bristol Folk House photo 10 asset to the top of the gig gallery."""

from django.db import migrations


BRISTOL_TOP_IMAGE = "images/gig_photos/Bristol_folk_house_31_03_2026_10.jpeg"


def promote_bristol_photo_10(apps, schema_editor):
    """Ensure the requested Bristol Folk House photo appears first in the gallery."""
    GigPhoto = apps.get_model("main_site", "GigPhoto")

    target, _ = GigPhoto.objects.update_or_create(
        image_path=BRISTOL_TOP_IMAGE,
        defaults={
            "title": "Bristol Folk House 31 03 2026",
            "thumbnail_path": "",
            "alt_text": "Bristol Folk House gig photo 10",
            "is_active": True,
        },
    )

    target.sort_order = 0
    target.save(update_fields=["sort_order"])

    other_photos = list(GigPhoto.objects.exclude(pk=target.pk).order_by("sort_order", "id"))
    for index, photo in enumerate(other_photos, start=1):
        if photo.sort_order != index:
            photo.sort_order = index
            photo.save(update_fields=["sort_order"])


class Migration(migrations.Migration):
    """Promote the chosen Bristol Folk House image to the top gallery slot."""

    dependencies = [
        ("main_site", "0005_spotify_social_link"),
    ]

    operations = [
        migrations.RunPython(promote_bristol_photo_10, migrations.RunPython.noop),
    ]
