from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("carpeta", "0005_populate_store_slug"),
    ]
    operations = [
        migrations.AlterField(
            model_name="binderprofile",
            name="store_slug",
            field=models.SlugField(blank=True, max_length=60, unique=True),
        ),
    ]
