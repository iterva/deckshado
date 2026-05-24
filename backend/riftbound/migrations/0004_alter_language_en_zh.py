from django.db import migrations, models


def migrate_languages(apps, schema_editor):
    Entry = apps.get_model("riftbound", "RiftboundCollectionEntry")
    # Cualquier idioma que no sea EN o ZH pasa a EN
    Entry.objects.exclude(language__in=["EN", "ZH"]).update(language="EN")


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("riftbound", "0003_merge_20260522_0111"),
    ]

    operations = [
        migrations.RunPython(migrate_languages, noop_reverse),
        migrations.AlterField(
            model_name="riftboundcollectionentry",
            name="language",
            field=models.CharField(
                choices=[("EN", "English"), ("ZH", "中文")],
                default="EN",
                max_length=4,
            ),
        ),
    ]
