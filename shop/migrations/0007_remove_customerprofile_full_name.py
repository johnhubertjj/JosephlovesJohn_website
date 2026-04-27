"""Remove stored customer profile names."""

from django.db import migrations


class Migration(migrations.Migration):
    """Drop the optional customer profile name field."""

    dependencies = [
        ("shop", "0006_product_orderitem_download_file_wav_path"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="customerprofile",
            name="full_name",
        ),
    ]
