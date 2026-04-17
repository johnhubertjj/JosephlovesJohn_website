from django.db import migrations, models


def populate_wav_download_paths(apps, schema_editor):
    """Backfill WAV download paths from existing WAV preview fields when available."""
    Product = apps.get_model("shop", "Product")
    OrderItem = apps.get_model("shop", "OrderItem")

    for product in Product.objects.filter(download_file_wav_path=""):
        if product.preview_file_wav:
            product.download_file_wav_path = product.preview_file_wav
            product.save(update_fields=["download_file_wav_path"])

    for item in OrderItem.objects.select_related("product").filter(download_file_wav_path=""):
        product = item.product
        wav_path = getattr(product, "download_file_wav_path", "") or getattr(product, "preview_file_wav", "")
        if wav_path:
            item.download_file_wav_path = wav_path
            item.save(update_fields=["download_file_wav_path"])


class Migration(migrations.Migration):
    dependencies = [("shop", "0005_order_confirmation_email_sent_at")]

    operations = [
        migrations.AddField(
            model_name="product",
            name="download_file_wav_path",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="download_file_wav_path",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.RunPython(populate_wav_download_paths, migrations.RunPython.noop),
    ]
