"""
Override manual: hay champion legends que la heurística de 0006 no logró
reclasificar (la mayoría siguen como `unit` o `spell`). En vez de seguir
ajustando la heurística, marcamos explícitamente estas cartas como `legend`
por `card_number` (la coincidencia ignora el sufijo `*` de variante alt-art).
"""
from __future__ import annotations

from django.db import migrations


LEGEND_NUMBERS = {
    "OGN-253",  # Darius, Hand of Noxus
    "OGN-305",  # Yasuo, Unforgiven
    "OGN-306",  # Leona, Radiant Dawn
    "OGN-307",  # Teemo, Swift Scout
    "OGN-310",  # Sett, The Boss
    "OGS-019",  # Master Yi, Wuju Bladesman
    "OGS-021",  # Lux, Lady of Luminosity
    "SFD-193",  # Jax, Grandmaster at Arms
    "SFD-195",  # Irelia, Blade Dancer
    "SFD-197",  # Azir, Emperor of the Sands
    "SFD-199",  # Ezreal, Prodigal Explorer
    "SFD-201",  # Renata Glasc, Chem-Baroness
    "SFD-203",  # Sivir, Battle Mistress
    "SFD-205",  # Fiora, Grand Duelist
    "SFD-240",  # Rumble, Mechanized Menace
    "SFD-241",  # Lucian, Purifier
    "SFD-245",  # Jax, Grandmaster at Arms (variant)
    "SFD-246",  # Irelia, Blade Dancer (variant)
    "SFD-248",  # Ezreal, Prodigal Explorer (variant)
}


def force_legends(apps, schema_editor):
    RiftboundCard = apps.get_model("riftbound", "RiftboundCard")
    updated = 0
    for card in RiftboundCard.objects.all():
        base = (card.card_number or "").rstrip("*").strip()
        if base in LEGEND_NUMBERS and card.card_type != "legend":
            card.card_type = "legend"
            card.save(update_fields=["card_type"])
            updated += 1
    print(f"[riftbound] Forzadas a legend: {updated}")


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("riftbound", "0007_add_champion_unit"),
    ]

    operations = [
        migrations.RunPython(force_legends, noop_reverse),
    ]
