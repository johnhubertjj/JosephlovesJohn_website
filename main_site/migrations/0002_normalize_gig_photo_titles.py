from django.db import migrations


def normalize_titles(apps, schema_editor):
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
    dependencies = [
        ("main_site", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(normalize_titles, migrations.RunPython.noop),
    ]
