"""
Re-aplica todos los fixes manuales que normalmente viven en migraciones
(0008 force_legends_overrides + 0009 refix_legend_colors).

Hay que correrlo SIEMPRE despues de `load_riftbound_cards`, porque el
loader pisa los campos `card_type` y `colors` con los valores del JSON
del scraper, deshaciendo los overrides manuales.
"""
from __future__ import annotations

from collections import defaultdict

from django.core.management.base import BaseCommand

from riftbound.models import RiftboundCard
from riftbound.management.commands.reclassify_riftbound import classify


# Cartas que la heuristica del scraper no detecta como `legend` y deben serlo.
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


# Colores canonicos por card_number base (ignora sufijo `*`).
CANONICAL_COLORS = {
    "OGS-017": ["chaos", "fury"],   # Annie, Dark Child
    "SFD-181": ["fury", "mind"],    # Rumble, Mechanized Menace
    "SFD-203": ["body", "chaos"],   # Sivir, Battle Mistress
}


class Command(BaseCommand):
    help = "Re-aplica fixes manuales de Riftbound (legend overrides + unificacion de colores)."

    def handle(self, *args, **opts):
        # 0) Reclasificacion heuristica unit/spell/gear/battlefield/legend
        # (replica la migracion 0006 reclassify_and_hide).
        reclassified = 0
        for card in RiftboundCard.objects.all():
            new_type = classify(card)
            if new_type != card.card_type:
                card.card_type = new_type
                card.save(update_fields=["card_type"])
                reclassified += 1
        self.stdout.write(self.style.SUCCESS(f"Reclasificadas por heuristica: {reclassified}"))

        # 0.b) Ocultar cartas con arte placeholder ("/missing/").
        hidden = RiftboundCard.objects.filter(
            image_url__contains="/missing/", is_active=True
        ).update(is_active=False)
        self.stdout.write(self.style.SUCCESS(f"Ocultas (placeholder /missing/): {hidden}"))

        # 1) Forzar `card_type=legend` en cartas mal clasificadas.
        forced = 0
        for card in RiftboundCard.objects.all():
            base = (card.card_number or "").rstrip("*").strip()
            if base in LEGEND_NUMBERS and card.card_type != "legend":
                card.card_type = "legend"
                card.save(update_fields=["card_type"])
                forced += 1
        self.stdout.write(self.style.SUCCESS(f"Forzadas a legend: {forced}"))

        # 2) Override explicito de colores por card_number.
        overridden = 0
        for card in RiftboundCard.objects.all():
            base = (card.card_number or "").rstrip("*").strip()
            if base in CANONICAL_COLORS:
                canonical = sorted(CANONICAL_COLORS[base])
                if sorted(card.colors or []) != canonical:
                    card.colors = canonical
                    card.save(update_fields=["colors"])
                    overridden += 1
        self.stdout.write(self.style.SUCCESS(f"Colores canonicos aplicados: {overridden}"))

        # 3) Unificar colores entre variantes que comparten nombre (legends).
        groups: dict[str, list] = defaultdict(list)
        for c in RiftboundCard.objects.filter(card_type="legend"):
            groups[c.name].append(c)

        unified = 0
        for name, cards in groups.items():
            union = sorted({col for c in cards for col in (c.colors or [])})
            if not union:
                continue
            for c in cards:
                if sorted(c.colors or []) != union:
                    c.colors = union
                    c.save(update_fields=["colors"])
                    unified += 1
        self.stdout.write(self.style.SUCCESS(f"Colores unificados entre variantes: {unified}"))

        self.stdout.write(self.style.SUCCESS("Fixes Riftbound re-aplicados OK."))
