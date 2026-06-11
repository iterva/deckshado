"""
Descarga cartas faltantes desde https://api.riftcodex.com y las inserta en la DB.

Uso:
    python manage.py seed_riftcodex_missing
    python manage.py seed_riftcodex_missing --dry-run   # solo muestra sin insertar
"""
from __future__ import annotations

import time

import requests
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from riftbound.models import RiftboundCard, RiftboundSet


# Mapeo de tipos de la API a nuestro modelo
TYPE_MAP = {
    "Unit": "unit",
    "Spell": "spell",
    "Gear": "gear",
    "Legend": "legend",
    "Rune": "rune",
    "Battlefield": "battlefield",
}

RARITY_MAP = {
    "Common": "common",
    "Uncommon": "uncommon",
    "Rare": "rare",
    "Epic": "epic",
    "Showcase": "showcase",
    "Promo": "promo",
}


class Command(BaseCommand):
    help = "Descarga cartas faltantes de api.riftcodex.com y las inserta en la DB"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Solo mostrar qué se insertaría, sin tocar la DB",
        )
        parser.add_argument(
            "--file", default=None,
            help="Ruta a JSON pre-descargado (si PA no puede acceder a la API)",
        )

    def handle(self, *args, **opts):
        dry_run = opts["dry_run"]

        # 1. Fetch all cards from API or load from file
        if opts["file"]:
            import json
            from pathlib import Path
            path = Path(opts["file"])
            if not path.exists():
                self.stderr.write(self.style.ERROR(f"No existe: {path}"))
                return
            self.stdout.write(f"Cargando cartas desde {path}...")
            all_api_cards = json.loads(path.read_text(encoding="utf-8"))
        else:
            self.stdout.write("Descargando cartas de api.riftcodex.com...")
            all_api_cards = self._fetch_all_cards()
        self.stdout.write(f"  Total en API: {len(all_api_cards)}")

        # 2. Get local card_numbers
        local_ids = set(RiftboundCard.objects.values_list("card_number", flat=True))
        self.stdout.write(f"  Total en DB local: {len(local_ids)}")

        # 3. Find missing
        missing = []
        for card in all_api_cards:
            normalized = self._normalize_id(card)
            if normalized not in local_ids:
                missing.append((normalized, card))

        self.stdout.write(f"  Faltantes: {len(missing)}")

        if not missing:
            self.stdout.write(self.style.SUCCESS("No hay cartas faltantes."))
            return

        if dry_run:
            for norm_id, card in sorted(missing, key=lambda x: x[0]):
                self.stdout.write(f"  [DRY] {norm_id:15} {card['name']}")
            return

        # 4. Insert missing cards
        created = 0
        with transaction.atomic():
            for norm_id, card in missing:
                set_obj = self._get_or_create_set(card)
                cls = card.get("classification") or {}
                attrs = card.get("attributes") or {}
                text = card.get("text") or {}
                media = card.get("media") or {}
                meta = card.get("metadata") or {}

                card_type = TYPE_MAP.get(cls.get("type", ""), "unit")
                rarity = RARITY_MAP.get(cls.get("rarity", ""), "common")
                colors = [c.lower() for c in (cls.get("domain") or [])]

                # Determine variant
                variant = ""
                if meta.get("alternate_art"):
                    variant = "Alt-art"
                elif meta.get("overnumbered"):
                    variant = "Overnumbered"
                elif meta.get("signature"):
                    variant = "Signature"

                supertype = cls.get("supertype") or ""

                obj, was_created = RiftboundCard.objects.update_or_create(
                    card_number=norm_id,
                    defaults={
                        "name": card.get("name", norm_id),
                        "slug": slugify(meta.get("clean_name") or card.get("name", norm_id))[:220],
                        "set": set_obj,
                        "card_type": card_type,
                        "supertype": supertype,
                        "subtypes": card.get("tags") or [],
                        "rarity": rarity,
                        "variant": variant,
                        "colors": colors,
                        "energy": attrs.get("energy"),
                        "power": attrs.get("power"),
                        "might": attrs.get("might"),
                        "description": text.get("plain") or "",
                        "flavor": text.get("flavour") or "",
                        "image_url": media.get("image_url") or "",
                        "image_url_small": "",
                        "source_url": "",
                        "raw": {},
                    },
                )
                if was_created:
                    created += 1

        self.stdout.write(self.style.SUCCESS(
            f"Seed completado: {created} cartas creadas de {len(missing)} faltantes."
        ))

    def _fetch_all_cards(self) -> list[dict]:
        """Fetch all pages from the riftcodex API."""
        all_cards = []
        page = 1
        while True:
            resp = requests.get(
                "https://api.riftcodex.com/cards",
                params={"page": page, "size": 50},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            all_cards.extend(data["items"])
            if page >= data["pages"]:
                break
            page += 1
            time.sleep(0.3)
        return all_cards

    def _normalize_id(self, card: dict) -> str:
        """Convert API riftbound_id (e.g. 'unl-060a-219') to our format (e.g. 'UNL-060a')."""
        api_id = card.get("riftbound_id", "")
        meta = card.get("metadata") or {}
        parts = api_id.split("-")

        if len(parts) >= 3:
            normalized = f"{parts[0].upper()}-{parts[1]}"
        elif len(parts) == 2:
            normalized = f"{parts[0].upper()}-{parts[1]}"
        else:
            normalized = api_id.upper()

        # Signature cards have * suffix in our DB
        if meta.get("signature"):
            normalized += "*"

        return normalized

    def _get_or_create_set(self, card: dict) -> RiftboundSet | None:
        """Get or create the set for a card."""
        set_info = card.get("set")
        if not set_info:
            return None
        set_code = set_info.get("set_id", "").upper()
        set_name = set_info.get("label", set_code)
        if not set_code:
            return None
        obj, _ = RiftboundSet.objects.get_or_create(
            code=set_code,
            defaults={"name": set_name},
        )
        return obj
