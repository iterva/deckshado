"""
Reseed idempotente de cartas AYDV del blog usando mapping de ImageKit.

Uso:
  python manage.py seed_aydv_blog_cards_imagekit
  python manage.py seed_aydv_blog_cards_imagekit --dry-run
  python manage.py seed_aydv_blog_cards_imagekit --mapping C:/ruta/myl_cards_imagekit_mapping.json
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

from django.core.management.base import BaseCommand

from cards.models import Card, CardType, Edition, Race, Rarity


CARDS = [
    # Guerrero
    {"public_id": "myl_cards/cain-3", "name": "Caín", "type_slug": "aliado", "race_slug": "guerrero", "rarity_slug": "ultra-real"},
    {"public_id": "myl_cards/beleth-6", "name": "Beleth", "type_slug": "aliado", "race_slug": "guerrero", "rarity_slug": "mega-real"},
    {"public_id": "myl_cards/gog-16", "name": "Gog", "type_slug": "aliado", "race_slug": "guerrero", "rarity_slug": "real"},
    {"public_id": "myl_cards/nimrod-18", "name": "Nimrod", "type_slug": "aliado", "race_slug": "guerrero", "rarity_slug": "real"},
    {"public_id": "myl_cards/canaan-17", "name": "Canaán", "type_slug": "aliado", "race_slug": "guerrero", "rarity_slug": "real"},
    {"public_id": "myl_cards/el-bandido-egipcio-11", "name": "El Bandido Egipcio", "type_slug": "aliado", "race_slug": "guerrero", "rarity_slug": "cortesano"},
    {"public_id": "myl_cards/rito-del-bandido-23", "name": "Rito de Bandido", "type_slug": "talisman", "race_slug": None, "rarity_slug": "cortesano"},
    {"public_id": "myl_cards/daga-del-bandido-024", "name": "Daga del Bandido", "type_slug": "arma", "race_slug": None, "rarity_slug": "vasallo"},
    {"public_id": "myl_cards/tesoro-de-bandido-30", "name": "Tesoro del Bandido", "type_slug": "oro", "race_slug": None, "rarity_slug": "vasallo"},
    # Sacerdote
    {"public_id": "myl_cards/rafael-08", "name": "Rafael", "type_slug": "aliado", "race_slug": "sacerdote", "rarity_slug": "ultra-real"},
    {"public_id": "myl_cards/uriel-04", "name": "Uriel", "type_slug": "aliado", "race_slug": "sacerdote", "rarity_slug": "mega-real"},
    {"public_id": "myl_cards/juan-de-patmos-024", "name": "Juan de Patmos", "type_slug": "aliado", "race_slug": "sacerdote", "rarity_slug": "real"},
    {"public_id": "myl_cards/abraham-023", "name": "Abraham", "type_slug": "aliado", "race_slug": "sacerdote", "rarity_slug": "real"},
    {"public_id": "myl_cards/matusalen-22", "name": "Matusalén", "type_slug": "aliado", "race_slug": "sacerdote", "rarity_slug": "real"},
    {"public_id": "myl_cards/jared-16", "name": "Jared", "type_slug": "aliado", "race_slug": "sacerdote", "rarity_slug": "cortesano"},
    {"public_id": "myl_cards/lamec-15", "name": "Lamec", "type_slug": "aliado", "race_slug": "sacerdote", "rarity_slug": "cortesano"},
    {"public_id": "myl_cards/cuatro-esposas-7", "name": "Cuatro Esposas", "type_slug": "aliado", "race_slug": "sacerdote", "rarity_slug": "vasallo"},
    {"public_id": "myl_cards/antipas-16", "name": "Antipas", "type_slug": "aliado", "race_slug": "sacerdote", "rarity_slug": "vasallo"},
    # Eterno
    {"public_id": "myl_cards/angel-gabriel-04", "name": "Ángel Gabriel", "type_slug": "aliado", "race_slug": "eterno", "rarity_slug": "secreta"},
    {"public_id": "myl_cards/el-angel-y-su-juicio", "name": "El Ángel y su Juicio", "type_slug": "talisman", "race_slug": None, "rarity_slug": "promo"},
    {"public_id": "myl_cards/angel-redentor-02", "name": "Ángel Redentor", "type_slug": "aliado", "race_slug": "eterno", "rarity_slug": "promo"},
    {"public_id": "myl_cards/angel-jofiel-04", "name": "Ángel Jofiel", "type_slug": "aliado", "race_slug": "eterno", "rarity_slug": "mega-real"},
    {"public_id": "myl_cards/angel-metatron-10", "name": "Ángel Metatrón", "type_slug": "aliado", "race_slug": "eterno", "rarity_slug": "real"},
    {"public_id": "myl_cards/angel-raziel-07", "name": "Ángel Raziel", "type_slug": "aliado", "race_slug": "eterno", "rarity_slug": "real"},
    {"public_id": "myl_cards/angel-sandalfon-27", "name": "Ángel Sandalfón", "type_slug": "aliado", "race_slug": "eterno", "rarity_slug": "real"},
    {"public_id": "myl_cards/shango-08", "name": "Shangó", "type_slug": "aliado", "race_slug": "eterno", "rarity_slug": "real"},
    # Héroe
    {"public_id": "myl_cards/enoc-7", "name": "Enoc", "type_slug": "aliado", "race_slug": "heroe", "rarity_slug": "ultra-real"},
    {"public_id": "myl_cards/noe-7", "name": "Noé", "type_slug": "aliado", "race_slug": "heroe", "rarity_slug": "mega-real"},
    {"public_id": "myl_cards/cam-19", "name": "Cam", "type_slug": "aliado", "race_slug": "heroe", "rarity_slug": "real"},
    {"public_id": "myl_cards/elias-20", "name": "Elías", "type_slug": "aliado", "race_slug": "heroe", "rarity_slug": "real"},
    {"public_id": "myl_cards/abel-21", "name": "Abel", "type_slug": "aliado", "race_slug": "heroe", "rarity_slug": "real"},
    {"public_id": "myl_cards/los-senalados-13", "name": "Los Señalados", "type_slug": "aliado", "race_slug": "heroe", "rarity_slug": "cortesano"},
    {"public_id": "myl_cards/sem-14", "name": "Sem", "type_slug": "aliado", "race_slug": "heroe", "rarity_slug": "cortesano"},
    {"public_id": "myl_cards/jafet-13", "name": "Jafet", "type_slug": "aliado", "race_slug": "heroe", "rarity_slug": "vasallo"},
    {"public_id": "myl_cards/martires-214", "name": "Mártires", "type_slug": "aliado", "race_slug": "heroe", "rarity_slug": "vasallo"},
]


def normalize_text(value: str | None) -> str:
    text = (value or "").lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def slugify_name(value: str) -> str:
    text = normalize_text(value)
    return re.sub(r"\s+", "-", text).strip("-")


def resolve_mapping_path(explicit_path: str | None) -> Path:
    if explicit_path:
        return Path(explicit_path).expanduser().resolve()

    here = Path(__file__).resolve()
    candidates = [
        here.parents[5] / "myl_cards_imagekit_mapping.json",  # repo root
        here.parents[4] / "myl_cards_imagekit_mapping.json",  # Proyecto-deckshado root
    ]
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]


class Command(BaseCommand):
    help = "Reseed idempotente de cartas AYDV blog + ImageKit"

    def add_arguments(self, parser):
        parser.add_argument(
            "--mapping",
            type=str,
            default=None,
            help="Ruta al JSON con source_url/public_id/imagekit_url",
        )
        parser.add_argument(
            "--edition-slug",
            type=str,
            default="aydv",
            help="Slug de edición destino (default: aydv)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Muestra cambios sin guardar",
        )

    def handle(self, *args, **options):
        mapping_path = resolve_mapping_path(options.get("mapping"))
        if not mapping_path.exists():
            self.stderr.write(self.style.ERROR(f"No existe mapping: {mapping_path}"))
            return

        with mapping_path.open("r", encoding="utf-8") as fh:
            mapping_items = json.load(fh)

        image_url_by_public_id = {}
        for item in mapping_items:
            public_id = (item.get("public_id") or "").strip().lower()
            image_url = (item.get("imagekit_url") or "").strip()
            if public_id and image_url and not item.get("error"):
                image_url_by_public_id[public_id] = image_url

        edition_slug = options["edition_slug"]
        dry_run = options["dry_run"]
        edition = Edition.objects.filter(slug=edition_slug).first()
        if not edition:
            self.stderr.write(self.style.ERROR(f"No existe edición con slug='{edition_slug}'"))
            return

        cards_in_edition = list(
            Card.objects.filter(edition=edition).select_related("card_type", "race", "rarity")
        )
        by_normalized_name = {}
        for card in cards_in_edition:
            key = normalize_text(card.name)
            by_normalized_name.setdefault(key, []).append(card)

        created = 0
        updated = 0
        kept = 0
        missing_img = 0
        missing_ref = 0

        for idx, row in enumerate(CARDS, start=1):
            image_url = image_url_by_public_id.get(row["public_id"].lower())
            if not image_url:
                missing_img += 1
                self.stdout.write(self.style.WARNING(
                    f"[{idx:02d}] MISS_IMG {row['name']} ({row['public_id']})"
                ))
                continue

            card_type = CardType.objects.filter(slug=row["type_slug"]).first()
            rarity = Rarity.objects.filter(slug=row["rarity_slug"]).first()
            race = Race.objects.filter(slug=row["race_slug"]).first() if row["race_slug"] else None
            if card_type is None or rarity is None or (row["race_slug"] and race is None):
                missing_ref += 1
                self.stdout.write(self.style.WARNING(
                    f"[{idx:02d}] MISS_REF {row['name']} type={row['type_slug']} "
                    f"race={row['race_slug']} rarity={row['rarity_slug']}"
                ))
                continue

            normalized_name = normalize_text(row["name"])
            candidates = by_normalized_name.get(normalized_name, [])
            existing = None
            for candidate in candidates:
                if candidate.card_type_id == card_type.id:
                    existing = candidate
                    break
            if existing is None and candidates:
                existing = candidates[0]

            target_race = race if row["type_slug"] == "aliado" else None

            if existing:
                changed_fields = []
                if existing.custom_image_url != image_url:
                    existing.custom_image_url = image_url
                    changed_fields.append("custom_image_url")
                if existing.card_type_id != card_type.id:
                    existing.card_type = card_type
                    changed_fields.append("card_type")
                if existing.rarity_id != rarity.id:
                    existing.rarity = rarity
                    changed_fields.append("rarity")
                target_race_id = target_race.id if target_race else None
                if existing.race_id != target_race_id:
                    existing.race = target_race
                    changed_fields.append("race")

                if changed_fields:
                    if not dry_run:
                        existing.save(update_fields=changed_fields)
                    updated += 1
                    self.stdout.write(
                        f"[{idx:02d}] {'WOULD_UPDATE' if dry_run else 'UPDATED'} "
                        f"{existing.name} ({existing.edid}) -> {', '.join(changed_fields)}"
                    )
                else:
                    kept += 1
                    self.stdout.write(f"[{idx:02d}] KEEP {existing.name} ({existing.edid})")
                continue

            edid = f"B{idx:03d}"
            myl_id = f"cbg{idx:03d}"
            slug = f"{slugify_name(row['name'])}-{edition_slug}"

            if dry_run:
                created += 1
                self.stdout.write(f"[{idx:02d}] WOULD_CREATE {row['name']} ({edid})")
                continue

            card = Card.objects.create(
                myl_id=myl_id,
                edid=edid,
                slug=slug,
                name=row["name"],
                edition=edition,
                rarity=rarity,
                race=target_race,
                card_type=card_type,
                cost=None,
                damage=None,
                ability=None,
                flavour=None,
                custom_image_url=image_url,
            )
            created += 1
            by_normalized_name.setdefault(normalized_name, []).append(card)
            self.stdout.write(f"[{idx:02d}] CREATED {card.name} ({card.edid})")

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("SUMMARY"))
        self.stdout.write(f"MAPPING_FILE {mapping_path}")
        self.stdout.write(f"CREATED {created}")
        self.stdout.write(f"UPDATED {updated}")
        self.stdout.write(f"KEPT {kept}")
        self.stdout.write(f"MISSING_IMG {missing_img}")
        self.stdout.write(f"MISSING_REF {missing_ref}")
        self.stdout.write(f"TOTAL_TARGET {len(CARDS)}")
        if not dry_run:
            self.stdout.write(f"AYDV_TOTAL {Card.objects.filter(edition=edition).count()}")
