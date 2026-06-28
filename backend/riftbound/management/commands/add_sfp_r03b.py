"""
Añade la carta SFP-R03b (Mind Rune, alt-art promo de Spiritforged).

Uso:
    python manage.py add_sfp_r03b
    python manage.py add_sfp_r03b --dry-run
"""
from __future__ import annotations

import uuid

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from riftbound.models import RiftboundCard, RiftboundSet


CARD_NUMBER = "SFP-R03b"
NAME = "Mind Rune"
SET_CODE = "SFP"
SET_NAME = "Spiritforged Promos"
# Conservamos este UUID para poder migrar el registro si antes existia como SFD-R03b.
EXTERNAL_ID = uuid.UUID("a03b5fd0-0000-4000-8000-000000000003")
DEFAULT_IMAGE = "https://cmsassets.rgpub.io/sanity/images/dsfx7636/game_data_live/eb4559c507f09cabc3735973a1b20d83688d2f9d-744x1039.png"


class Command(BaseCommand):
    help = "Crea o actualiza la carta SFP-R03b (Mind Rune promo alt-art)."

    def add_arguments(self, parser):
        parser.add_argument("--cdn", default="", help="URL CDN propia (opcional).")
        parser.add_argument("--image", default=DEFAULT_IMAGE, help="URL de imagen base.")
        parser.add_argument("--dry-run", action="store_true", help="No escribe cambios en DB.")

    @transaction.atomic
    def handle(self, *args, **opts):
        cdn = (opts.get("cdn") or "").strip()
        img = (opts.get("image") or "").strip()
        dry_run = bool(opts.get("dry_run"))

        rb_set, set_created = RiftboundSet.objects.get_or_create(
            code=SET_CODE,
            defaults={"name": SET_NAME},
        )
        if not set_created and rb_set.name != SET_NAME:
            rb_set.name = SET_NAME
            if not dry_run:
                rb_set.save(update_fields=["name"])

        # Priorizamos card_number (si ya existe), y si no, migramos por external_id.
        card = RiftboundCard.objects.filter(card_number=CARD_NUMBER).first()
        migrated_from_number = None
        if not card:
            card = RiftboundCard.objects.filter(external_id=EXTERNAL_ID).first()
            if card and card.card_number != CARD_NUMBER:
                migrated_from_number = card.card_number

        payload = {
            "name": NAME,
            "slug": slugify(f"{NAME}-{CARD_NUMBER}"),
            "set": rb_set,
            "card_type": "rune",
            "supertype": "",
            "subtypes": [],
            "rarity": "showcase",
            "variant": "Alt Art",
            "colors": ["mind"],
            "energy": 0,
            "power": 0,
            "might": 0,
            "description": ".",
            "flavor": "",
            "image_url": img,
            "image_url_small": "",
            "cdn_image_url": cdn,
            "source_url": "https://piltoverarchive.com/cards?page=15",
            "is_active": True,
        }

        action = "actualizada"
        if card:
            if not dry_run:
                card.card_number = CARD_NUMBER
                for field, value in payload.items():
                    setattr(card, field, value)
                card.save()
        else:
            action = "creada"
            if not dry_run:
                card = RiftboundCard.objects.create(
                    card_number=CARD_NUMBER,
                    external_id=EXTERNAL_ID,
                    **payload,
                )

        if dry_run:
            self.stdout.write(self.style.WARNING(
                f"[DRY-RUN] Carta {CARD_NUMBER} lista para upsert (set={SET_CODE})."
            ))
            return

        migrate_note = ""
        if migrated_from_number:
            migrate_note = f" (migrada desde {migrated_from_number})"

        self.stdout.write(self.style.SUCCESS(
            f"Carta {action}: {CARD_NUMBER} - {NAME}{migrate_note}"
        ))
