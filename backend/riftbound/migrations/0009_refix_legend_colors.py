"""
Re-ejecuta la unificación de colores por nombre que hizo 0005, pero esta
vez después de 0008 (que reclasificó cartas como `legend`). El bug original
era que 0005 corrió antes de tener todas las cartas marcadas como `legend`,
por lo que Sivir SFD-203, Rumble SFD-181, Annie OGS-017 (y posiblemente
otras) seguían apareciendo con un solo color en el cliente.

Además, si alguna leyenda quedó con 0 o 1 color y conocemos el correcto
desde el seed JSON, aplicamos un override explícito.
"""
from __future__ import annotations

from collections import defaultdict

from django.db import migrations


# Colores canonicos por número de carta (fuente: riftbound_cards.json del scraper).
# Sólo casos que reportó el usuario o donde el JSON difiere.
CANONICAL_COLORS = {
    "OGS-017": ["chaos", "fury"],   # Annie, Dark Child
    "SFD-181": ["fury", "mind"],    # Rumble, Mechanized Menace
    "SFD-203": ["body", "chaos"],   # Sivir, Battle Mistress
}


def fix_legend_colors_again(apps, schema_editor):
    Card = apps.get_model("riftbound", "RiftboundCard")

    # 1) Override explícito por número de carta (ignora sufijo `*`).
    for card in Card.objects.all():
        base = (card.card_number or "").rstrip("*").strip()
        if base in CANONICAL_COLORS:
            canonical = sorted(CANONICAL_COLORS[base])
            if sorted(card.colors or []) != canonical:
                card.colors = canonical
                card.save(update_fields=["colors"])

    # 2) Unifica colores entre variantes que comparten nombre (todas las leyendas).
    groups: dict[str, list] = defaultdict(list)
    for c in Card.objects.filter(card_type="legend"):
        groups[c.name].append(c)

    for name, cards in groups.items():
        union = sorted({col for c in cards for col in (c.colors or [])})
        if not union:
            continue
        for c in cards:
            if sorted(c.colors or []) != union:
                c.colors = union
                c.save(update_fields=["colors"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("riftbound", "0008_force_legends_overrides"),
    ]

    operations = [
        migrations.RunPython(fix_legend_colors_again, noop_reverse),
    ]
