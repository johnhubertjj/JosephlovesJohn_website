from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("shop", "0004_order_paid_at_order_stripe_checkout_session_id_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="confirmation_email_sent_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
