"""Normalize seeded gig photo titles to their display form."""

from django.db import migrations


def normalize_titles(apps, schema_editor):
    """Rename seeded gig photo titles to user-facing labels.

    :param apps: Historical app registry supplied by Django migrations.
    :type apps: django.apps.registry.Apps
    :param schema_editor: Schema editor for the current migration run.
    :type schema_editor: django.db.backends.base.schema.BaseDatabaseSchemaEditor
    :returns: ``None``.
    """
    GigPhoto = apps.get_model("main_site", "GigPhoto")
    for photo in GigPhoto.objects.all():
        image_path = photo.image_path or ""
        new_title = None
        if "Bristol_folk_house_31_03_2026_" in image_path:
            new_title = "Bristol Folk House 31 03 2026"
        elif "sofa_photos" in image_path:
            new_title = "Sofa Session"

        if new_title and photo.title != new_title:
            photo.title = new_title
            photo.save(update_fields=["title"])


class Migration(migrations.Migration):
    """Apply the title normalization data migration."""

    dependencies = [
        ("main_site", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(normalize_titles, migrations.RunPython.noop),
    ]
