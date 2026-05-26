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
    "UNL-011",  # Fresh Beans
    "UNL-019",  # Blighted Battleaxe
    "UNL-039",  # Soul Sword
    "UNL-045",  # Forgotten Signpost
    "UNL-049",  # Honeyfruit
    "UNL-074",  # Frigid Jewel
    "UNL-078",  # Sprite Fountain
    "UNL-085",  # Sumpworks Map
    "UNL-096",  # Hunter's Machete
    "UNL-133",  # Blast Cone
    "UNL-158",  # Shepherd's Heirloom
    "UNL-161",  # Divining Shells
    "UNL-174",  # Shard of Undoing
    "UNL-188",  # Hextech Gauntlets
}


# Cartas mal clasificadas que en realidad son units (tag "UNIT" visible).
FORCE_UNIT_NUMBERS = {
    "UNL-002",  # Inferna
    "UNL-012",  # Lord Broadmane
    "UNL-018",  # Yeti Brawler
    "UNL-021",  # Grim Apothecary
    "UNL-053",  # Scuttle Crab
    "UNL-060",  # Vilemaw
    "UNL-060a",  # Vilemaw (variant)
    "UNL-071",  # Chakram Dancer
    "UNL-093",  # Dragonsoul Sage
    "UNL-166",  # Stalking Wolf
    "UNL-194",  # Shadow
}


# Cartas mal clasificadas que en realidad son battlefields.
FORCE_BATTLEFIELD_NUMBERS = {
    "OGN-284",  # Obelisk of Power
    "OGN-285",  # Reaver's Row
    "OGN-290",  # The Arena's Greatest
    "OGN-292",  # The Dreaming Tree
}


# Colores canonicos por card_number base (ignora sufijo `*`).
CANONICAL_COLORS = {
    "OGS-017": ["chaos", "fury"],   # Annie, Dark Child
    "SFD-181": ["fury", "mind"],    # Rumble, Mechanized Menace
    "SFD-203": ["body", "chaos"],   # Sivir, Battle Mistress
}


# Descripciones de battlefields extraidas manualmente de las imagenes oficiales.
# El scraper no captura este texto porque esta rotado 180deg en las cartas verticales.
BATTLEFIELD_DESCRIPTIONS = {
    # --- OGN ---
    "OGN-275": "When you hold here, play a 1 Recruit unit token in your base.",
    "OGN-276": "Increase the points needed to win the game by 1.",
    "OGN-277": "When a unit moves from here, give it +1 Might this turn.",
    "OGN-278": "You may hide an additional card here.",
    "OGN-279": "When you defend here, choose a unit. It gains Shield 2 this combat. (+2 Might while it's a defender.)",
    "OGN-280": "When you hold here, draw 1.",
    "OGN-281": "When you hold here, you may return your Chosen Champion from your trash to your Champion Zone if it is empty.",
    "OGN-282": "When you conquer here, you may spend a buff to draw 1.",
    "OGN-283": "When you hold here, buff a unit here. (If it doesn't have a buff, it gets a +1 Might buff.)",
    "OGN-286": "When you hold here, activate the conquer effects of units here.",
    "OGN-287": "When you conquer here, recycle one of your runes.",
    "OGN-288": "When you hold here, you may channel 1 rune exhausted.",
    "OGN-289": "When you conquer here, ready 2 runes at the end of this turn.",
    "OGN-291": "When you conquer here, look at the top two cards of your Main Deck. You may recycle one or both of them. Put those you don't back in any order.",
    "OGN-293": "When you hold here, if you have 7+ units here, you win the game.",
    "OGN-294": "Units here have +1 Might. (This includes attackers.)",
    "OGN-295": "Units can't move from here to base.",
    "OGN-296": "Spells and abilities affecting units here each deal 1 Bonus Damage. (Each instance of damage the spell deals is increased by 1.)",
    "OGN-297": "Units here have Ganking. (They can move from battlefield to battlefield.)",
    "OGN-298": "When you conquer here, discard 1, then draw 1.",
    # --- SFD ---
    "SFD-207": "When you conquer here, you may pay 1 and return a unit you control here to its owner's hand. If you do, play a 2 Power Sand Soldier unit token here.",
    "SFD-208": "While you control this battlefield, friendly legends have \"[Recycle]: Attach an Equipment you control to a unit you control.\"",
    "SFD-209": "Players can't score here until their third turn.",
    "SFD-210": "When you conquer here, you may pay 1 to ready your legend.",
    "SFD-211": "While you control this battlefield, friendly REPEAT costs cost 1 less.",
    "SFD-212": "When you conquer here, put the top 2 cards of your Main Deck into your trash.",
    "SFD-213": "While you control this battlefield, the first friendly non-token gear played each turn costs 1 less.",
    "SFD-214": "When you hold here, you may pay 4 Power to score 1 point.",
    "SFD-215": "When you defend here, reveal the top card of your Main Deck. If it's a spell, put it in your hand. Otherwise, recycle it.",
    "SFD-216": "Units can't be played here.",
    "SFD-217": "When you conquer here, draw 1 for each other battlefield you or allies control.",
    "SFD-218": "When you conquer here with one or more MIGHTY units, you may pay 1 to draw 1. (A unit is Mighty while it has 5+ Might.)",
    "SFD-219": "When you hold here, each player channels 1 rune exhausted.",
    "SFD-220": "When you conquer here, you may pay 1 to play a Gold gear token exhausted.",
    "SFD-221": "When you conquer here, you may ready a friendly gear. If it's an Equipment, you may detach it.",
    # --- UNL ---
    "UNL-205": "When a player plays a spell, they may give a unit they control here +1 Might this turn.",
    "UNL-206": "If a unit here would die during combat, its controller may pay 3 to heal it, exhaust it, and recall it instead.",
    "UNL-207": "When you hold here, you may move a unit at a battlefield to its base.",
    "UNL-208": "Units here with TEMPORARY have SHIELD. (+1 Might while they're defenders.)",
    "UNL-209": "At the start of your Beginning Phase, you may kill a unit you control here to draw 1. (This happens before scoring.)",
    "UNL-210": "While a unit here is defending alone, it has -2 Might. (It's alone if there are no other friendly units here.)",
    "UNL-211": "While you control this battlefield, when you play a spell, if you spent 4 or more, PREDICT. (Look at the top card of your Main Deck. You may recycle it.)",
    "UNL-212": "At the start of each player's Beginning Phase, deal 1 to each unit here. (This happens before scoring.)",
    "UNL-213": "Units here have \"[Recycle]: Gain 1 XP.\"",
    "UNL-214": "When a unit here is returned to a player's hand, that player may pay 1 to channel 1 rune exhausted.",
    "UNL-215": "The first time a player plays a non-token unit here each turn, they may move another unit they control here to its base.",
    "UNL-216": "When you hold here, give your next spell this turn REPEAT equal to its base cost. (You may pay the additional cost to repeat the spell's effect.)",
    "UNL-217": "When you conquer here, if you assigned 3 or more excess damage, play a 1 Bird unit token with DEFLECT.",
    "UNL-218": "When a player plays a unit here, they may pay 1 to BUFF it. (Give it a +1 buff if it doesn't have one.)",
    "UNL-219": "When you hold here, your non-token units cost 1 more to play this turn.",
}


class Command(BaseCommand):
    help = "Re-aplica fixes manuales de Riftbound (legend overrides + unificacion de colores)."

    def handle(self, *args, **opts):
        # Conjunto de overrides manuales: estas cartas NO deben tocarse por la heuristica.
        manual_overrides = LEGEND_NUMBERS | FORCE_GEAR_NUMBERS | FORCE_UNIT_NUMBERS | FORCE_BATTLEFIELD_NUMBERS

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

        # 1.d) Forzar `card_type=battlefield` en cartas mal clasificadas.
        forced_bf = 0
        for card in RiftboundCard.objects.all():
            base = (card.card_number or "").rstrip("*").strip()
            if base in FORCE_BATTLEFIELD_NUMBERS and card.card_type != "battlefield":
                card.card_type = "battlefield"
                card.save(update_fields=["card_type"])
                forced_bf += 1
        self.stdout.write(self.style.SUCCESS(f"Forzadas a battlefield: {forced_bf}"))

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

        # 4) Descripciones de battlefields (texto oculto por estar rotado en la imagen).
        bf_desc = 0
        for base, desc in BATTLEFIELD_DESCRIPTIONS.items():
            for card in RiftboundCard.objects.filter(card_number__startswith=base):
                # Solo escribir si esta vacio para no pisar overrides manuales del scraper.
                if not (card.description or "").strip():
                    card.description = desc
                    card.save(update_fields=["description"])
                    bf_desc += 1
        self.stdout.write(self.style.SUCCESS(f"Descripciones de battlefield aplicadas: {bf_desc}"))

        self.stdout.write(self.style.SUCCESS("Fixes Riftbound re-aplicados OK."))
