from django.db import migrations


def delete_triadas_entries(apps, schema_editor):
    BanlistEntry = apps.get_model("cards", "BanlistEntry")
    BanlistEntry.objects.filter(sub_format="triadas").delete()


def noop(apps, schema_editor):
    # No es posible recrear las entradas borradas; sin operación inversa.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("cards", "0006_card_custom_image_url"),
    ]

    operations = [
        migrations.RunPython(delete_triadas_entries, noop),
    ]
