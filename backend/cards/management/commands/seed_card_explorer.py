"""
Seed the 1511 card-explorer cards (alt arts + missing Primera Era cards).
Reads card_explorer_mapping.json and card_explorer_raw.json from project root.

Usage on PythonAnywhere:
  cd ~/deckshado/Proyecto-deckshado/backend
  python manage.py seed_card_explorer
"""
import json
import os
import re
from urllib.parse import unquote

from django.core.management.base import BaseCommand
from cards.models import Card, Edition, Race, CardType


# Project root (Proyecto-deckshado/, one level above backend/)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
RAW_FILE = os.path.join(PROJECT_ROOT, "card_explorer_raw.json")
MAPPING_FILE = os.path.join(PROJECT_ROOT, "card_explorer_mapping.json")

EDITION_IDS = {
    "el-reto": 104,
    "mundo-gotico": 105,
    "la-ira-del-nahual": 106,
    "ragnarok": 107,
    "espiritu-de-dragon": 108,
}

RACE_IDS = {
    "caballero": 2, "dragón": 12, "dragon": 12, "fairy": 7, "faerie": 7,
    "cazador": 22, "vampiro": 21, "licántropo": 20, "licantropo": 20,
    "bestia": 3, "chamán": 23, "chaman": 23, "guerrero": 5,
    "abominación": 25, "abominacion": 25, "bárbaro": 6, "barbaro": 6,
    "dios": 24, "kami": 26, "xian": 27, "criaturas": 28,
    "campeón": 32, "campeon": 32, "sin raza": 1,
}


def classify_card(url: str):
    decoded = unquote(url).lower()

    race_patterns = [
        (r"razas/1\.\-?\s*caballero", "el-reto", 1, "caballero"),
        (r"razas/2\.\-?\s*dragon", "el-reto", 1, "dragon"),
        (r"razas/3\.\-?\s*faerie", "el-reto", 1, "fairy"),
        (r"razas/4\.\-?\s*cazador", "mundo-gotico", 1, "cazador"),
        (r"razas/5\.\-?\s*lic", "mundo-gotico", 1, "licántropo"),
        (r"razas/6\.\-?\s*vampiro", "mundo-gotico", 1, "vampiro"),
        (r"razas/7\.\-?\s*bestia", "la-ira-del-nahual", 1, "bestia"),
        (r"razas/8\.\-?\s*cham", "la-ira-del-nahual", 1, "chamán"),
        (r"razas/9\.\-?\s*guerrero", "la-ira-del-nahual", 1, "guerrero"),
        (r"razas/10\.\-?\s*abominaci", "ragnarok", 1, "abominación"),
        (r"razas/11\.\-?\s*b.rbaro", "ragnarok", 1, "bárbaro"),
        (r"razas/12\.\-?\s*dios", "ragnarok", 1, "dios"),
        (r"razas/13\.\-?\s*criaturas", "espiritu-de-dragon", 1, "criaturas"),
        (r"razas/14\.\-?\s*campe", "espiritu-de-dragon", 1, "campeón"),
        (r"razas/15\.\-?\s*kami", "espiritu-de-dragon", 1, "kami"),
        (r"razas/16\.\-?\s*xian", "espiritu-de-dragon", 1, "xian"),
    ]

    support_patterns = [
        (r"soporte/1\.\-?\s*el\s*reto/armas", "el-reto", 3, "sin raza"),
        (r"soporte/1\.\-?\s*el\s*reto/t.tems", "el-reto", 4, "sin raza"),
        (r"soporte/1\.\-?\s*el\s*reto/talismanes", "el-reto", 2, "sin raza"),
        (r"soporte/1\.\-?\s*el\s*reto/oros", "el-reto", 5, "sin raza"),
        (r"soporte/2\.\-?\s*mundo\s*g.tico/armas", "mundo-gotico", 3, "sin raza"),
        (r"soporte/2\.\-?\s*mundo\s*g.tico/t.tems", "mundo-gotico", 4, "sin raza"),
        (r"soporte/2\.\-?\s*mundo\s*g.tico/talismanes", "mundo-gotico", 2, "sin raza"),
        (r"soporte/2\.\-?\s*mundo\s*g.tico/oros", "mundo-gotico", 5, "sin raza"),
        (r"soporte/3\.\-?\s*la\s*ira.*?/armas", "la-ira-del-nahual", 3, "sin raza"),
        (r"soporte/3\.\-?\s*la\s*ira.*?/t.tems", "la-ira-del-nahual", 4, "sin raza"),
        (r"soporte/3\.\-?\s*la\s*ira.*?/talismanes", "la-ira-del-nahual", 2, "sin raza"),
        (r"soporte/3\.\-?\s*la\s*ira.*?/oros", "la-ira-del-nahual", 5, "sin raza"),
        (r"soporte/4\.\-?\s*ragnarok/armas", "ragnarok", 3, "sin raza"),
        (r"soporte/4\.\-?\s*ragnarok/t.tems", "ragnarok", 4, "sin raza"),
        (r"soporte/4\.\-?\s*ragnarok/talismanes", "ragnarok", 2, "sin raza"),
        (r"soporte/4\.\-?\s*ragnarok/oros", "ragnarok", 5, "sin raza"),
        (r"soporte/5\.\-?\s*esp.ritu/armas", "espiritu-de-dragon", 3, "sin raza"),
        (r"soporte/5\.\-?\s*esp.ritu.*?/t.tems", "espiritu-de-dragon", 4, "sin raza"),
        (r"soporte/5\.\-?\s*esp.ritu.*?/talismanes", "espiritu-de-dragon", 2, "sin raza"),
        (r"soporte/5\.\-?\s*esp.ritu.*?/oros", "espiritu-de-dragon", 5, "sin raza"),
    ]

    alt_patterns = [
        (r"artes\s*alternativos/el\s*reto/caballero", "el-reto", 1, "caballero"),
        (r"artes\s*alternativos/el\s*reto/dragon", "el-reto", 1, "dragon"),
        (r"artes\s*alternativos/el\s*reto/faerie", "el-reto", 1, "fairy"),
        (r"artes\s*alternativos/el\s*reto/armas", "el-reto", 3, "sin raza"),
        (r"artes\s*alternativos/el\s*reto/totem", "el-reto", 4, "sin raza"),
        (r"artes\s*alternativos/el\s*reto/talim", "el-reto", 2, "sin raza"),
        (r"artes\s*alternativos/el\s*reto/oros", "el-reto", 5, "sin raza"),
        (r"artes\s*alternativos/mundo\s*gotico/cazador", "mundo-gotico", 1, "cazador"),
        (r"artes\s*alternativos/mundo\s*gotico/vampiro", "mundo-gotico", 1, "vampiro"),
        (r"artes\s*alternativos/mundo\s*gotico/licantropo", "mundo-gotico", 1, "licántropo"),
        (r"artes\s*alternativos/mundo\s*gotico/armas", "mundo-gotico", 3, "sin raza"),
        (r"artes\s*alternativos/mundo\s*gotico/talismanes", "mundo-gotico", 2, "sin raza"),
        (r"artes\s*alternativos/mundo\s*gotico/oro", "mundo-gotico", 5, "sin raza"),
        (r"artes\s*alternativos/la\s*ira/bestias", "la-ira-del-nahual", 1, "bestia"),
        (r"artes\s*alternativos/la\s*ira/chaman", "la-ira-del-nahual", 1, "chamán"),
        (r"artes\s*alternativos/la\s*ira/guerrero", "la-ira-del-nahual", 1, "guerrero"),
        (r"artes\s*alternativos/la\s*ira/armas", "la-ira-del-nahual", 3, "sin raza"),
        (r"artes\s*alternativos/la\s*ira/totems", "la-ira-del-nahual", 4, "sin raza"),
        (r"artes\s*alternativos/la\s*ira/talisman", "la-ira-del-nahual", 2, "sin raza"),
        (r"artes\s*alternativos/la\s*ira/oro", "la-ira-del-nahual", 5, "sin raza"),
    ]

    expansion_patterns = [
        (r"mundos\s*perdidos.*?/tombstone", "mundo-gotico", 1, "cazador"),
        (r"mundos\s*perdidos.*?/nube\s*roja", "la-ira-del-nahual", 1, "guerrero"),
        (r"mundos\s*perdidos.*?/xinnian\s*2026", "espiritu-de-dragon", 1, "campeón"),
    ]

    nuevas_edition_patterns = [
        (r"nuevas\s*4\.0/el\s*reto", "el-reto", 1, "sin raza"),
        (r"nuevas\s*4\.0/gotico", "mundo-gotico", 1, "sin raza"),
        (r"nuevas\s*4\.0/ira", "la-ira-del-nahual", 1, "sin raza"),
        (r"nuevas\s*4\.0/ragnarok", "ragnarok", 1, "sin raza"),
        (r"nuevas\s*4\.0/esperitu", "espiritu-de-dragon", 1, "sin raza"),
        (r"nuevas\s*4\.0/colmillo", "mundo-gotico", 1, "licántropo"),
    ]

    faltantes_patterns = [
        (r"cartas\s*faltantes/reto", "el-reto", 1, "sin raza"),
        (r"cartas\s*faltantes/gotico", "mundo-gotico", 1, "sin raza"),
        (r"cartas\s*faltantes/ira", "la-ira-del-nahual", 1, "sin raza"),
        (r"cartas\s*faltantes/ragnarok", "ragnarok", 1, "sin raza"),
        (r"cartas\s*faltantes/espiritu", "espiritu-de-dragon", 1, "sin raza"),
    ]

    pe_faltantes_patterns = [
        (r"pe\s*comp/cartas\s*faltantes/espiritu", "espiritu-de-dragon", 1, "sin raza"),
    ]

    for patterns in [race_patterns, support_patterns, alt_patterns,
                     expansion_patterns, nuevas_edition_patterns,
                     faltantes_patterns, pe_faltantes_patterns]:
        for pattern, edition, card_type, race in patterns:
            if re.search(pattern, decoded):
                race_id = RACE_IDS.get(race, 1)
                return (edition, card_type, race_id)

    if re.search(r"pe\s*comp/oros/", decoded):
        return ("el-reto", 5, 1)
    if "cofradia" in decoded:
        return ("el-reto", 1, 1)
    if "toolkit 2026" in decoded:
        return ("el-reto", 1, 1)
    if "lootbox2025" in decoded:
        return ("el-reto", 1, 1)
    if "nuevascofra" in decoded:
        return ("el-reto", 2, 1)
    if "/nuevas/" in decoded:
        return ("el-reto", 1, 1)
    if "cole racial 2" in decoded:
        if "espiritu" in decoded:
            return ("espiritu-de-dragon", 1, 1)
        return ("el-reto", 1, 1)
    if "cartas aniversario" in decoded:
        return ("el-reto", 1, 1)
    if "correcioneas" in decoded:
        return ("el-reto", 1, 1)

    return None


PE_EDITIONS = [
    {"id": 104, "myl_id": "pe_01", "slug": "el_reto", "title": "PE - El Reto"},
    {"id": 105, "myl_id": "pe_02", "slug": "mundo_gotico", "title": "PE - Mundo Gótico"},
    {"id": 106, "myl_id": "pe_03", "slug": "ira_del_nahual", "title": "PE - La Ira del Nahual"},
    {"id": 107, "myl_id": "pe_04", "slug": "ragnarok", "title": "PE - Ragnarok"},
    {"id": 108, "myl_id": "pe_05", "slug": "espiritu_del_dragon", "title": "PE - Espíritu de Dragón"},
]


class Command(BaseCommand):
    help = "Seed 1511 card-explorer PE cards (alt arts + missing)"

    def _ensure_pe_editions(self):
        """Create PE format and editions if they don't exist."""
        from cards.models import Format
        fmt, created = Format.objects.get_or_create(code="pe", defaults={"name": "Primera Era"})
        if created:
            self.stdout.write(f"  Created format: {fmt.name}")
        for ed_data in PE_EDITIONS:
            obj, created = Edition.objects.get_or_create(
                id=ed_data["id"],
                defaults={
                    "myl_id": ed_data["myl_id"],
                    "slug": ed_data["slug"],
                    "title": ed_data["title"],
                    "format": fmt,
                    "active": True,
                },
            )
            if created:
                self.stdout.write(f"  Created edition: {obj.title}")

    def handle(self, *args, **options):
        if not os.path.exists(RAW_FILE):
            self.stderr.write(f"ERROR: {RAW_FILE} not found")
            return
        if not os.path.exists(MAPPING_FILE):
            self.stderr.write(f"ERROR: {MAPPING_FILE} not found")
            return

        self._ensure_pe_editions()

        raw_cards = json.load(open(RAW_FILE, "r", encoding="utf-8"))
        mapping = json.load(open(MAPPING_FILE, "r", encoding="utf-8"))

        # Build reverse lookup: source_url → cloudinary_url
        url_to_cloudinary = {}
        for edition_slug, cards in mapping.items():
            for card_name, data in cards.items():
                url_to_cloudinary[data["source_url"]] = data["cloudinary_url"]

        self.stdout.write(f"Raw cards: {len(raw_cards)}, Cloudinary URLs: {len(url_to_cloudinary)}")

        # Get existing card URLs to avoid duplicates
        existing_urls = set(
            Card.objects.filter(edition_id__in=EDITION_IDS.values())
            .values_list("custom_image_url", flat=True)
        )

        # Get last myl_id number
        last_card = (
            Card.objects.filter(myl_id__startswith="pe_")
            .extra(select={"num": "CAST(SUBSTR(myl_id, 4) AS INTEGER)"})
            .order_by("-num")
            .first()
        )
        next_id = int(last_card.myl_id.split("_")[1]) + 1 if last_card else 1309

        # Track name occurrences per edition for variant naming
        from django.db.models import Count
        name_counts = {}
        for card in Card.objects.filter(edition_id__in=EDITION_IDS.values()).values("name", "edition_id"):
            key = (card["name"], card["edition_id"])
            name_counts[key] = name_counts.get(key, 0) + 1

        created = 0
        skipped = 0
        unclassified = 0

        for card_data in raw_cards:
            name = card_data["name"]
            url = card_data["url"]

            cloudinary_url = url_to_cloudinary.get(url)
            if not cloudinary_url:
                continue
            if cloudinary_url in existing_urls:
                skipped += 1
                continue

            result = classify_card(url)
            if not result:
                unclassified += 1
                continue

            edition_slug, card_type_id, race_id = result
            edition_id = EDITION_IDS[edition_slug]

            # Variant name
            key = (name, edition_id)
            count = name_counts.get(key, 0)
            display_name = f"{name} (v{count + 1})" if count > 0 else name
            name_counts[key] = count + 1

            myl_id = f"pe_{next_id:04d}"
            slug = re.sub(r'[^a-z0-9]+', '-', display_name.lower()).strip('-')

            Card.objects.create(
                name=display_name,
                slug=slug,
                myl_id=myl_id,
                edid=0,
                custom_image_url=cloudinary_url,
                card_type_id=card_type_id,
                edition_id=edition_id,
                race_id=race_id,
                cost="",
                damage="",
                ability="",
                flavour="",
            )
            existing_urls.add(cloudinary_url)
            created += 1
            next_id += 1

            if created % 100 == 0:
                self.stdout.write(f"  {created} creadas...")

        self.stdout.write(self.style.SUCCESS(
            f"\nDone! Created: {created}, Skipped: {skipped}, Unclassified: {unclassified}"
        ))
