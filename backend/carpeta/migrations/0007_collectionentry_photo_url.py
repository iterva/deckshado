from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("carpeta", "0006_binderprofile_store_slug_unique"),
    ]

    operations = [
        migrations.AddField(
            model_name="collectionentry",
            name="photo_url",
            field=models.URLField(
                blank=True,
                default="",
                help_text="Foto real de la carta (Cloudinary)",
                max_length=500,
            ),
        ),
    ]
