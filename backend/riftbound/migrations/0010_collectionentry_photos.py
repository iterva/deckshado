from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("riftbound", "0009_refix_legend_colors"),
    ]

    operations = [
        migrations.AddField(
            model_name="riftboundcollectionentry",
            name="photo_url",
            field=models.URLField(
                blank=True,
                default="",
                help_text="Foto real de la carta (Cloudinary)",
                max_length=500,
            ),
        ),
        migrations.AddField(
            model_name="riftboundcollectionentry",
            name="photo_url_2",
            field=models.URLField(
                blank=True,
                default="",
                help_text="Segunda foto real (Cloudinary)",
                max_length=500,
            ),
        ),
    ]
