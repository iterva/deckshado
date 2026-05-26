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


# Cartas que la heuristica clasifica como `spell` (u otro) pero en realidad son gears.
# Fuente: revision manual de imagenes (tag "GEAR" visible en la carta).
FORCE_GEAR_NUMBERS = {
    "OGN-040",  # Seal of Rage
    "OGN-060",  # Mask of Foresight
    "OGN-063",  # Spirit's Refuge
    "OGN-072",  # Solari Shrine
    "OGN-077",  # Zhonya's Hourglass
    "OGN-081",  # Seal of Focus
    "OGN-098",  # Energy Conduit
    "OGN-101",  # Mushroom Pouch
    "OGN-120",  # Seal of Insight
    "OGN-143",  # Pirate's Haven
    "OGN-152",  # Mistfall
    "OGN-160",  # Dazzling Aurora
    "OGN-163",  # Seal of Strength
    "OGN-182",  # Scrapheap
    "OGN-204",  # Seal of Discord
    "OGN-212",  # Forge of the Future
    "OGN-227",  # Symbol of the Solari
    "OGN-228",  # Vanguard Helm
    "OGN-245",  # Seal of Unity
    "SFD-009",  # Serrated Dirk
    "SFD-016",  # Recurve Bow
    "SFD-022",  # Long Sword
    "SFD-030",  # Skyfall of Areion
    "SFD-033",  # Doran's Shield
    "SFD-042",  # Brutalizer
    "SFD-051",  # Guardian Angel
    "SFD-056",  # Sterak's Gage
    "SFD-059",  # Svellsongur
    "SFD-063",  # Chemtech Cask
    "SFD-064",  # Cloth Armor
    "SFD-073",  # Experimental Hexplate
    "SFD-083",  # Hextech Anomaly
    "SFD-086",  # World Atlas
    "SFD-090",  # The Zero Drive
    "SFD-095",  # Doran's Blade
    "SFD-102",  # Hexdrinker
    "SFD-104",  # Petricite Monument
    "SFD-108",  # Warmog's Armor
    "SFD-115",  # Trinity Force
    "SFD-117",  # Ancient Henge
    "SFD-118",  # Boneshiver
    "SFD-124",  # Doran's Ring
    "SFD-133",  # Boots of Swiftness
    "SFD-134",  # Cull
    "SFD-139",  # Edge of Night
    "SFD-144",  # Spirit Wheel
    "SFD-150",  # Last Rites
    "SFD-153",  # Eye of the Herald
    "SFD-161",  # B.F. Sword
    "SFD-169",  # Altar of Memories
    "SFD-172",  # Sacred Shears
    "SFD-178",  # Blade of the Ruined King
    "SFD-186",  # Spinning Axe
    "SFD-190",  # Forgefire Cape
    "SFD-191",  # Rabadon's Deathcrown
    "SFD-192",  # Shurelya's Requiem
    "SFD-222",  # Seal of Rage
    "SFD-226",  # Seal of Focus
    "SFD-229",  # Seal of Insight
    "SFD-231",  # Seal of Strength
    "SFD-234",  # Seal of Discord
    "SFD-238",  # Seal of Unity
}


# Cartas mal clasificadas que en realidad son units (tag "UNIT" visible).
FORCE_UNIT_NUMBERS = {
    "UNL-002",  # Inferna
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
        # Conjunto de overrides manuales: estas cartas NO deben tocarse por la heuristica.
        manual_overrides = LEGEND_NUMBERS | FORCE_GEAR_NUMBERS | FORCE_UNIT_NUMBERS

        # 0) Reclasificacion heuristica unit/spell/gear/battlefield/legend
        # (replica la migracion 0006 reclassify_and_hide).
        reclassified = 0
        for card in RiftboundCard.objects.all():
            base = (card.card_number or "").rstrip("*").strip()
            if base in manual_overrides:
                continue  # respeta overrides manuales
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

        # 1.b) Forzar `card_type=gear` en cartas mal clasificadas (spells que son gears).
        forced_gear = 0
        for card in RiftboundCard.objects.all():
            base = (card.card_number or "").rstrip("*").strip()
            if base in FORCE_GEAR_NUMBERS and card.card_type != "gear":
                card.card_type = "gear"
                card.save(update_fields=["card_type"])
                forced_gear += 1
        self.stdout.write(self.style.SUCCESS(f"Forzadas a gear: {forced_gear}"))

        # 1.c) Forzar `card_type=unit` en cartas mal clasificadas (units que aparecen como spell).
        forced_unit = 0
        for card in RiftboundCard.objects.all():
            base = (card.card_number or "").rstrip("*").strip()
            if base in FORCE_UNIT_NUMBERS and card.card_type != "unit":
                card.card_type = "unit"
                card.save(update_fields=["card_type"])
                forced_unit += 1
        self.stdout.write(self.style.SUCCESS(f"Forzadas a unit: {forced_unit}"))

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
