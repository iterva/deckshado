"""
Reclasifica cartas Riftbound mal etiquetadas (la mayoría de los Champion
Legends de SFD/OGN/OGS quedaron como `unit` o `spell` al importar) y oculta
las cartas que sólo tienen un placeholder de texto ("CARD ART COMING SOON").

La lógica de clasificación es la misma que `python manage.py reclassify_riftbound`
y la heurística de ocultar es: si `image_url` apunta a un placeholder
(`/missing/`) marcamos `is_active=False` para que no aparezca en listados
hasta que tengamos el arte oficial.
"""
from __future__ import annotations

from django.db import migrations


RUNE_NAMES = {
    "Fury Rune", "Calm Rune", "Mind Rune",
    "Body Rune", "Chaos Rune", "Order Rune",
}


def classify(c) -> str:
    if c.card_type == "rune" and c.name not in RUNE_NAMES:
        pass
    elif c.card_type in ("rune", "battlefield"):
        return c.card_type

    desc = (c.description or "")
    desc_lower = desc.lower()
    name = c.name or ""
    first = name.split(",")[0].strip() if "," in name else ""
    is_champion = bool(first) and first in (c.subtypes or [])

    has_action = "[action]" in desc_lower or "[reaction]" in desc_lower
    has_tap = "[tap]" in desc_lower

    if is_champion:
        if c.might == 0 and c.power == 0 and c.energy == 0:
            return "legend"
        return "unit"

    if has_action:
        return "spell"

    if c.might is not None and c.might > 0:
        return "unit"

    if c.might == 0 and has_tap:
        return "gear"

    if c.might == 0 and c.energy is not None:
        return "spell"

    if c.might is None and c.power == 0 and has_tap:
        return "gear"

    if c.might is None and c.power is not None and c.energy is not None:
        return "unit"

    if c.might is None and c.energy is None:
        unit_phrases = (
            "i enter", "i attack", "i defend", "when i ", "i'm an", "i am ",
            "i must", "i have ", "[assault]", "[tank]", "[accelerate]", "[vision]",
        )
        if any(p in desc_lower for p in unit_phrases):
            return "unit"
        if not desc.strip():
            return "battlefield"
        return "spell"

    return c.card_type


def reclassify_and_hide(apps, schema_editor):
    Card = apps.get_model("riftbound", "RiftboundCard")

    # 1) Reclasificar card_type
    for c in Card.objects.all():
        new_type = classify(c)
        if new_type != c.card_type:
            c.card_type = new_type
            c.save(update_fields=["card_type"])

    # 2) Ocultar cartas con arte placeholder ("missing/...") hasta tener el arte real.
    Card.objects.filter(image_url__contains="/missing/", is_active=True).update(is_active=False)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("riftbound", "0005_fix_legend_colors_union"),
    ]

    operations = [
        migrations.RunPython(reclassify_and_hide, noop_reverse),
    ]
