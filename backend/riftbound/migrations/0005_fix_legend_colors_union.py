"""
Repara legends cuyo color quedó incompleto: unifica los colores entre
variantes que comparten el mismo nombre (p.ej. Annie, Rumble, Sivir tenían
solo 1 color en algunas variantes cuando todas las leyendas son bicolor).

Equivalente a `python manage.py fix_legend_colors` pero aplicado vía
migración para que se ejecute automáticamente en cada entorno (prod
incluida) tras `migrate`.
"""
from __future__ import annotations

from collections import defaultdict

from django.db import migrations


def fix_legend_colors(apps, schema_editor):
    Card = apps.get_model("riftbound", "RiftboundCard")
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
    # No es reversible (no guardamos snapshot previo).
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("riftbound", "0004_alter_language_en_zh"),
    ]

    operations = [
        migrations.RunPython(fix_legend_colors, noop_reverse),
    ]
