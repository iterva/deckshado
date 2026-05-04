"""
Re-clasifica cartas Riftbound mal etiquetadas por el scraper.

Heurísticas (en orden):
  1. Champion Unit: si el nombre tiene formato "X, Y" y "X" aparece como subtype,
     es un Champion Unit (ej: "Jinx, Rebel" con subtype 'Jinx').
  2. Si el tipo es 'other' y tiene `might` → 'unit' (units siempre tienen might).
  3. Si el tipo es 'other' y la descripción contiene palabras de spell
     ([REACTION], [Action], "Play a unit", "Move an enemy", "Give") → 'spell'.

Uso:
    python manage.py reclassify_riftbound [--dry-run]
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

from riftbound.models import RiftboundCard


SPELL_KEYWORDS = (
    "[REACTION]", "[Action]", "Move an enemy", "Move a friendly",
    "Give a unit", "Give a friendly", "Play a unit",
    "Look at the top", "Each player looks at",
)


class Command(BaseCommand):
    help = "Re-clasifica cartas Riftbound con tipo 'other' incorrecto."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Solo muestra cambios")

    def handle(self, *args, **opts):
        dry = opts["dry_run"]
        changes: list[tuple[str, str, str, str]] = []

        for c in RiftboundCard.objects.all():
            if c.card_type in ("rune", "battlefield", "legend"):
                continue
            new_type = c.card_type

            # 1) Champion unit por nombre + subtype
            first_word = c.name.split(",")[0].strip() if "," in c.name else ""
            if first_word and first_word in (c.subtypes or []):
                if c.card_type in ("other", "spell"):
                    new_type = "unit"

            # 2) 'other' con might → unit
            elif c.card_type == "other" and c.might is not None:
                new_type = "unit"

            # 3) 'other' con palabras clave de spell
            elif c.card_type == "other" and c.description:
                desc = c.description
                if any(k in desc for k in SPELL_KEYWORDS):
                    new_type = "spell"

            if new_type != c.card_type:
                changes.append((c.card_number, c.name, c.card_type, new_type))
                if not dry:
                    c.card_type = new_type
                    c.save(update_fields=["card_type"])

        for num, name, old, new in changes[:40]:
            self.stdout.write(f"  {num:12s}  {name:35s}  {old:10s} → {new}")
        if len(changes) > 40:
            self.stdout.write(f"  ... y {len(changes) - 40} más")

        verb = "Cambiarían" if dry else "Cambiadas"
        self.stdout.write(self.style.SUCCESS(
            f"{verb} {len(changes)} cartas{' (dry-run)' if dry else ''}."
        ))

