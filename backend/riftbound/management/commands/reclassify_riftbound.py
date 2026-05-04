"""
Re-clasifica cartas Riftbound mal etiquetadas por el scraper.

Heurísticas (en orden, fuente: Riftbound Core Rules):
  1. Tipos especiales (rune/battlefield/legend) → no se tocan.
  2. Champion Unit: el nombre tiene formato "X, Y" y "X" aparece como subtype
     (ej. "Jinx, Rebel" con subtype 'Jinx').  Si tiene stats → unit.
  3. Si la descripción contiene `[ACTION]` o `[REACTION]` → spell
     (marcador oficial de hechizos). Excepción: champions con habilidades action.
  4. `might > 0` → unit (las unidades reales siempre tienen poder de combate).
  5. `might == 0` con `[TAP]` en la descripción → gear (artefactos con habilidades activadas).
  6. `might == 0` sin [TAP] → spell (efectos one-shot tipo "Deal X / Draw X").

Uso:
    python manage.py reclassify_riftbound [--dry-run]
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

from riftbound.models import RiftboundCard


def classify(c: RiftboundCard) -> str:
    if c.card_type in ("rune", "battlefield", "legend"):
        return c.card_type

    desc = (c.description or "")
    desc_lower = desc.lower()
    name = c.name or ""
    first = name.split(",")[0].strip() if "," in name else ""
    is_champion = bool(first) and first in (c.subtypes or [])

    has_action = "[action]" in desc_lower or "[reaction]" in desc_lower
    has_tap = "[tap]" in desc_lower

    # Champion-unit: nombre "X, Y" con X en subtypes (LEGEND • X). Tiene prioridad.
    if is_champion:
        return "champion"

    # Marcador explícito de spell
    if has_action:
        return "spell"

    # Unidad con poder de combate
    if c.might is not None and c.might > 0:
        return "unit"

    # might == 0 con [TAP] → gear
    if c.might == 0 and has_tap:
        return "gear"

    # might == 0 sin [TAP] y con energía → spell
    if c.might == 0 and c.energy is not None:
        return "spell"

    # Sin might pero con stats parciales: si tiene power == 0 y [TAP] → gear
    if c.might is None and c.power == 0 and has_tap:
        return "gear"

    # Sin might, con power y energía: probablemente unit (champion-like)
    if c.might is None and c.power is not None and c.energy is not None:
        return "unit"

    # Sin nada: si tiene descripción con palabras tipo "I enter / I attack / friendly units" es unit
    if c.might is None and c.energy is None:
        unit_phrases = ("i enter", "i attack", "i defend", "when i ", "i'm an", "i am ",
                         "i must", "i have ", "[assault]", "[tank]", "[accelerate]", "[vision]")
        if any(p in desc_lower for p in unit_phrases):
            return "unit"
        # Sin stats, sin descripción → battlefield (locaciones)
        if not desc.strip():
            return "battlefield"
        # default con descripción → spell
        return "spell"

    return c.card_type


class Command(BaseCommand):
    help = "Re-clasifica cartas Riftbound (unit/spell/gear/champion) según descripción y stats."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Solo muestra cambios")

    def handle(self, *args, **opts):
        dry = opts["dry_run"]
        changes: list[tuple[str, str, str, str]] = []

        for c in RiftboundCard.objects.all():
            new_type = classify(c)
            if new_type != c.card_type:
                changes.append((c.card_number, c.name, c.card_type, new_type))
                if not dry:
                    c.card_type = new_type
                    c.save(update_fields=["card_type"])

        for num, name, old, new in changes[:50]:
            self.stdout.write(f"  {num:12s}  {name[:32]:32s}  {old:8s} -> {new}")
        if len(changes) > 50:
            self.stdout.write(f"  ... y {len(changes) - 50} más")

        verb = "Cambiarian" if dry else "Cambiadas"
        self.stdout.write(self.style.SUCCESS(
            f"{verb} {len(changes)} cartas{' (dry-run)' if dry else ''}."
        ))


