from django.db import migrations


RARITY_ORDER = {
    "milenaria": 1,
    "secreta": 2,
    "legendaria": 3,
    "promo": 4,
    "ultra-real": 5,
    "mega-real": 6,
    "real": 7,
    "vasallo": 8,
    "cortesano": 9,
    "oro": 10,
    "ficha": 11,
    "set_paralelo": 12,
}


def populate_display_order(apps, schema_editor):
    Rarity = apps.get_model("cards", "Rarity")
    for rarity in Rarity.objects.all():
        rarity.display_order = RARITY_ORDER.get(rarity.slug, 99)
        rarity.save(update_fields=["display_order"])


def reverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("cards", "0008_alter_rarity_options_rarity_display_order_and_more"),
    ]

    operations = [
        migrations.RunPython(populate_display_order, reverse_noop),
    ]
