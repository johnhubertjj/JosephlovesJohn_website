"""Initial schema and seed data for editable gig photos."""

from django.db import migrations, models


def seed_gig_photos(apps, schema_editor):
    """Seed the gig photo table with default gallery entries.

    :param apps: Historical app registry supplied by Django migrations.
    :type apps: django.apps.registry.Apps
    :param schema_editor: Schema editor for the current migration run.
    :type schema_editor: django.db.backends.base.schema.BaseDatabaseSchemaEditor
    :returns: ``None``.
    """
    GigPhoto = apps.get_model("main_site", "GigPhoto")
    if GigPhoto.objects.exists():
        return

    seed_rows = [
        {
            "title": "Sofa Session 01",
            "image_path": "images/gig_photos/sofa_photos_1.jpeg",
            "thumbnail_path": "images/gig_photos/sofa_photos_1.jpeg",
            "alt_text": "Gig photo - sofa session 1",
            "sort_order": 10,
            "is_active": True,
        },
        {
            "title": "Sofa Session 02",
            "image_path": "images/gig_photos/sofa_photos2.jpeg",
            "thumbnail_path": "images/gig_photos/sofa_photos2.jpeg",
            "alt_text": "Gig photo - sofa session 2",
            "sort_order": 20,
            "is_active": True,
        },
        {
            "title": "Sofa Session 03",
            "image_path": "images/gig_photos/sofa_photos3.jpeg",
            "thumbnail_path": "images/gig_photos/sofa_photos3.jpeg",
            "alt_text": "Gig photo - sofa session 3",
            "sort_order": 30,
            "is_active": True,
        },
        {
            "title": "Bristol Folk House 31 03 2026 - 1",
            "image_path": "images/gig_photos/Bristol_folk_house_31_03_2026_1.jpeg",
            "thumbnail_path": "images/gig_photos/thumbs/Bristol_folk_house_31_03_2026_1_thumb.jpg",
            "alt_text": "Bristol Folk House gig photo 1",
            "sort_order": 40,
            "is_active": True,
        },
        {
            "title": "Bristol Folk House 31 03 2026 - 2",
            "image_path": "images/gig_photos/Bristol_folk_house_31_03_2026_2.jpeg",
            "thumbnail_path": "images/gig_photos/thumbs/Bristol_folk_house_31_03_2026_2_thumb.jpg",
            "alt_text": "Bristol Folk House gig photo 2",
            "sort_order": 50,
            "is_active": True,
        },
        {
            "title": "Bristol Folk House 31 03 2026 - 3",
            "image_path": "images/gig_photos/Bristol_folk_house_31_03_2026_3.jpeg",
            "thumbnail_path": "images/gig_photos/thumbs/Bristol_folk_house_31_03_2026_3_thumb.jpg",
            "alt_text": "Bristol Folk House gig photo 3",
            "sort_order": 60,
            "is_active": True,
        },
        {
            "title": "Bristol Folk House 31 03 2026 - 4",
            "image_path": "images/gig_photos/Bristol_folk_house_31_03_2026_4.jpeg",
            "thumbnail_path": "images/gig_photos/thumbs/Bristol_folk_house_31_03_2026_4_thumb.jpg",
            "alt_text": "Bristol Folk House gig photo 4",
            "sort_order": 70,
            "is_active": True,
        },
        {
            "title": "Bristol Folk House 31 03 2026 - 5",
            "image_path": "images/gig_photos/Bristol_folk_house_31_03_2026_5.jpeg",
            "thumbnail_path": "images/gig_photos/thumbs/Bristol_folk_house_31_03_2026_5_thumb.jpg",
            "alt_text": "Bristol Folk House gig photo 5",
            "sort_order": 80,
            "is_active": True,
        },
        {
            "title": "Bristol Folk House 31 03 2026 - 6",
            "image_path": "images/gig_photos/Bristol_folk_house_31_03_2026_6.jpeg",
            "thumbnail_path": "images/gig_photos/thumbs/Bristol_folk_house_31_03_2026_6_thumb.jpg",
            "alt_text": "Bristol Folk House gig photo 6",
            "sort_order": 90,
            "is_active": True,
        },
        {
            "title": "Bristol Folk House 31 03 2026 - 7",
            "image_path": "images/gig_photos/Bristol_folk_house_31_03_2026_7.jpeg",
            "thumbnail_path": "images/gig_photos/thumbs/Bristol_folk_house_31_03_2026_7_thumb.jpg",
            "alt_text": "Bristol Folk House gig photo 7",
            "sort_order": 100,
            "is_active": True,
        },
        {
            "title": "Bristol Folk House 31 03 2026 - 8",
            "image_path": "images/gig_photos/Bristol_folk_house_31_03_2026_8.jpeg",
            "thumbnail_path": "images/gig_photos/thumbs/Bristol_folk_house_31_03_2026_8_thumb.jpg",
            "alt_text": "Bristol Folk House gig photo 8",
            "sort_order": 110,
            "is_active": True,
        },
        {
            "title": "Bristol Folk House 31 03 2026 - 9",
            "image_path": "images/gig_photos/Bristol_folk_house_31_03_2026_9.jpeg",
            "thumbnail_path": "images/gig_photos/thumbs/Bristol_folk_house_31_03_2026_9_thumb.jpg",
            "alt_text": "Bristol Folk House gig photo 9",
            "sort_order": 120,
            "is_active": True,
        },
    ]

    GigPhoto.objects.bulk_create([GigPhoto(**row) for row in seed_rows])


def unseed_gig_photos(apps, schema_editor):
    """Remove seeded gig photos during reverse migration.

    :param apps: Historical app registry supplied by Django migrations.
    :type apps: django.apps.registry.Apps
    :param schema_editor: Schema editor for the current migration run.
    :type schema_editor: django.db.backends.base.schema.BaseDatabaseSchemaEditor
    :returns: ``None``.
    """
    GigPhoto = apps.get_model("main_site", "GigPhoto")
    GigPhoto.objects.all().delete()


class Migration(migrations.Migration):
    """Create the ``GigPhoto`` model and initial gallery seed data."""

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="GigPhoto",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=140)),
                (
                    "image_path",
                    models.CharField(
                        help_text="Path relative to static/, for example images/gig_photos/photo.jpeg",
                        max_length=255,
                    ),
                ),
                (
                    "thumbnail_path",
                    models.CharField(
                        blank=True,
                        help_text="Optional thumbnail path relative to static/. Falls back to image_path when blank.",
                        max_length=255,
                    ),
                ),
                ("alt_text", models.CharField(blank=True, max_length=180)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={"ordering": ("sort_order", "id")},
        ),
        migrations.RunPython(seed_gig_photos, unseed_gig_photos),
    ]
