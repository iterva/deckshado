"""
Añade la carta SFD-R03b (Mind Rune, segundo alt-art de Spiritforged).

Uso:
    python manage.py add_sfd_r03b
"""
from __future__ import annotations

import uuid

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from riftbound.models import RiftboundCard, RiftboundSet


CARD_NUMBER = "SFD-R03b"
NAME = "Mind Rune"
SET_CODE = "SFD"
EXTERNAL_ID = uuid.UUID("a03b5fd0-0000-4000-8000-000000000003")
CDN_URL = "https://res.cloudinary.com/dmvu6tuee/image/upload/riftbound/cards/sfd/sfd-r03b.jpg"
FALLBACK_IMAGE = CDN_URL


class Command(BaseCommand):
    help = "Crea o actualiza la carta SFD-R03b (Mind Rune alt-art b)."

    def add_arguments(self, parser):
        parser.add_argument("--cdn", default=CDN_URL)
        parser.add_argument("--image", default=FALLBACK_IMAGE)

    @transaction.atomic
    def handle(self, *args, **opts):
        cdn = opts["cdn"]
        img = opts["image"]

        rb_set = RiftboundSet.objects.filter(code=SET_CODE).first()
        if not rb_set:
            self.stdout.write(self.style.ERROR(f"No existe el set {SET_CODE}"))
            return

        card, created = RiftboundCard.objects.update_or_create(
            card_number=CARD_NUMBER,
            defaults={
                "external_id": EXTERNAL_ID,
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
                "description": "-",
                "flavor": "",
                "image_url": img,
                "image_url_small": "",
                "cdn_image_url": cdn,
                "source_url": "https://piltoverarchive.com/cards?page=15",
                "is_active": True,
            },
        )
        verb = "Creada" if created else "Actualizada"
        self.stdout.write(self.style.SUCCESS(
            f"{verb}: {card.card_number} — {card.name} (cdn='{card.cdn_image_url}')"
        ))
