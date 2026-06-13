"""
Seed AYDV blog spoiler cards from Cloudinary fetch mapping.

Expected mapping file (root project):
  aydv_blog_spoilers_mapping.json

Usage:
  python manage.py seed_aydv_blog_spoilers
"""

from __future__ import annotations

import json
import os
import re
import unicodedata

from django.core.management.base import BaseCommand
from cards.models import Card, Edition, Format, CardType, Rarity, Race


MAPPING_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "..", "..", "aydv_blog_spoilers_mapping.json",
)


CARDS = [
    {"key": "asmodeus", "name": "Asmodeus", "type_slug": "aliado"},
    {"key": "azi_del_abismo", "name": "Azi del Abismo", "type_slug": "aliado"},
    {"key": "azi_demoniaco", "name": "Azi Demoniaco", "type_slug": "aliado"},
    {"key": "azi_raoioita", "name": "Azi Raoioita", "type_slug": "aliado"},
    {"key": "azrael", "name": "Azrael", "type_slug": "aliado"},
    {"key": "baphomet", "name": "Baphomet", "type_slug": "aliado"},
    {"key": "belcebu", "name": "Belcebu", "type_slug": "aliado"},
    {"key": "cuerno_de_titan", "name": "Cuerno de Titan", "type_slug": "oro"},
    {"key": "dagon", "name": "Dagon", "type_slug": "aliado"},
    {"key": "demonios_del_abismo", "name": "Demonios del Abismo", "type_slug": "aliado"},
    {"key": "escamas_de_azi", "name": "Escamas de Azi", "type_slug": "oro"},
    {"key": "furfur", "name": "Furfur", "type_slug": "aliado"},
    {"key": "gran_dragon", "name": "Gran Dragon", "type_slug": "aliado"},
    {"key": "lahmu_inmortal", "name": "Lahmu Inmortal", "type_slug": "aliado"},
    {"key": "leviathan", "name": "Leviathan", "type_slug": "aliado"},
    {"key": "lucifer", "name": "Lucifer", "type_slug": "aliado"},
    {"key": "morgana", "name": "Morgana", "type_slug": "aliado"},
    {"key": "nefandos", "name": "Nefandos", "type_slug": "aliado"},
    {"key": "rugido_de_titan", "name": "Rugido de Titan", "type_slug": "talisman"},
    {"key": "samael", "name": "Samael", "type_slug": "aliado"},
    {"key": "satanas", "name": "Satanas", "type_slug": "aliado"},
    {"key": "titan_abismal", "name": "Titan Abismal", "type_slug": "aliado"},
    {"key": "titan_nephilim", "name": "Titan Nephilim", "type_slug": "aliado"},
    {"key": "valefor", "name": "Valefor", "type_slug": "aliado"},
    {"key": "wyrm_de_la_plaga", "name": "Wyrm de la Plaga", "type_slug": "aliado"},
]


# Race mapping provided by user (card-by-card) for BLOG allies.
RACE_BY_KEY = {
    "asmodeus": "sombra",
    "azi_demoniaco": "dragon",
    "azi_raoioita": "dragon",
    "azi_del_abismo": "dragon",
    "azrael": "sombra",
    "baphomet": "bestia",
    "belcebu": "sombra",
    "dagon": "dragon",
    "demonios_del_abismo": "bestia",
    "furfur": "bestia",
    "gran_dragon": "dragon",
    "lahmu_inmortal": "bestia",
    "leviathan": "dragon",
    "lucifer": "sombra",
    "morgana": "sombra",
    "nefandos": "bestia/dragon/sombra",
    "samael": "sombra",
    "satanas": "bestia",
    "titan_abismal": "sombra",
    "titan_nephilim": "sombra",
    "valefor": "dragon",
    "wyrm_de_la_plaga": "dragon",
}


def slugify_name(name: str) -> str:
    nfkd = unicodedata.normalize("NFKD", name.lower())
    stripped = "".join(c for c in nfkd if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "-", stripped).strip("-")


class Command(BaseCommand):
    help = "Seed AYDV blog spoiler cards from precomputed Cloudinary fetch mapping"

    def handle(self, *args, **options):
        imp_format = Format.objects.filter(code="imp").first()
        if not imp_format:
            self.stderr.write(self.style.ERROR("Format 'imp' not found"))
            return

        rarity = Rarity.objects.filter(slug="promo").first()

        if not os.path.exists(MAPPING_FILE):
            self.stderr.write(self.style.ERROR(f"Mapping file not found: {MAPPING_FILE}"))
            return

        with open(MAPPING_FILE, "r", encoding="utf-8") as f:
            mapping = json.load(f)

        self.stdout.write(f"Loaded mapping entries: {len(mapping)}")

        edition, created_edition = Edition.objects.update_or_create(
            myl_id="custom_aydv_blog_spoilers",
            defaults={
                "slug": "aydv-blog-spoilers",
                "title": "AYDV Blog Spoilers (Jun 2026)",
                "image": "https://casamyl.cl/cdn/shop/articles/SHOPIFY_23_1081x.png?v=1781362177",
                "date_release": "2026-06-13",
                "format": imp_format,
                "active": True,
            },
        )
        self.stdout.write(self.style.SUCCESS(
            f"{'Created' if created_edition else 'Updated'} edition: {edition.title}"
        ))

        created_count = 0
        updated_count = 0
        missing_url = 0
        missing_race = 0

        for idx, card_data in enumerate(CARDS, start=1):
            key = card_data["key"]
            image_url = mapping.get(key)
            if not image_url:
                missing_url += 1
                self.stdout.write(self.style.WARNING(f"  Missing URL for key={key}, skipped"))
                continue

            card_type = CardType.objects.filter(slug=card_data["type_slug"]).first()
            slug_base = slugify_name(card_data["name"])
            race = None
            if card_data["type_slug"] == "aliado":
                race_slug = RACE_BY_KEY.get(key)
                if race_slug:
                    race = Race.objects.filter(slug=race_slug).first()
                    if not race:
                        missing_race += 1
                        self.stdout.write(self.style.WARNING(
                            f"  Missing race slug='{race_slug}' for key={key}"
                        ))

            card, was_created = Card.objects.update_or_create(
                myl_id=f"custom_aydv_blog_{idx:03d}",
                defaults={
                    "edid": f"BLOG-{idx:03d}",
                    "slug": f"{slug_base}-aydv-blog",
                    "name": card_data["name"],
                    "edition": edition,
                    "rarity": rarity,
                    "race": race,
                    "card_type": card_type,
                    "cost": None,
                    "damage": None,
                    "ability": None,
                    "flavour": None,
                    "custom_image_url": image_url,
                },
            )

            if was_created:
                created_count += 1
            else:
                updated_count += 1

            status = "Created" if was_created else "Updated"
            self.stdout.write(f"  {status}: {card.name} ({card.edid})")

        self.stdout.write(self.style.SUCCESS(
            f"Done. Created={created_count} Updated={updated_count} "
            f"MissingURL={missing_url} MissingRace={missing_race}"
        ))
