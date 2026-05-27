from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("carpeta", "0007_collectionentry_photo_url"),
    ]

    operations = [
        migrations.AddField(
            model_name="collectionentry",
            name="photo_url_2",
            field=models.URLField(
                blank=True,
                default="",
                help_text="Segunda foto real (Cloudinary)",
                max_length=500,
            ),
        ),
    ]
