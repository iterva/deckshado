"""
Importa cartas Riftbound desde un JSON producido por `scrape_riftbound.py`.

Uso:
    python manage.py load_riftbound_cards --file ../riftbound_cards.json
"""
from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from riftbound.models import (
    RiftboundCard, RiftboundSet, RiftboundIcon, RiftboundFormat,
)


class Command(BaseCommand):
    help = "Importa cartas Riftbound desde un archivo JSON"

    def add_arguments(self, parser):
        parser.add_argument("--file", required=True, help="Ruta al JSON de cartas")
        parser.add_argument(
            "--icons", default=None,
            help="Ruta opcional a JSON de iconos (kind, code, image_url)",
        )

    def handle(self, *args, **opts):
        path = Path(opts["file"])
        if not path.exists():
            raise CommandError(f"No existe: {path}")

        data = json.loads(path.read_text(encoding="utf-8"))
        cards = data if isinstance(data, list) else data.get("cards", [])

        # Asegurar formato Standard
        RiftboundFormat.objects.get_or_create(
            code="standard", defaults={"name": "Standard", "is_active": True},
        )

        created = updated = 0
        with transaction.atomic():
            for raw in cards:
                number = raw.get("card_number") or raw.get("number")
                if not number:
                    self.stderr.write(f"Salto carta sin número: {raw.get('name')}")
                    continue

                set_obj = None
                if (set_code := raw.get("set_code")):
                    set_obj, _ = RiftboundSet.objects.get_or_create(
                        code=set_code,
                        defaults={"name": raw.get("set_name") or set_code},
                    )
                    if raw.get("set_name") and set_obj.name != raw["set_name"]:
                        set_obj.name = raw["set_name"]
                        set_obj.save(update_fields=["name"])

                defaults = {
                    "name": raw.get("name", number),
                    "slug": slugify(raw.get("name", number))[:220],
                    "set": set_obj,
                    "card_type": (raw.get("card_type") or "unit").lower(),
                    "supertype": raw.get("supertype") or "",
                    "subtypes": raw.get("subtypes") or [],
                    "rarity": (raw.get("rarity") or "common").lower(),
                    "variant": raw.get("variant") or "",
                    "colors": [c.lower() for c in (raw.get("colors") or [])],
                    "energy": raw.get("energy"),
                    "power": raw.get("power"),
                    "might": raw.get("might"),
                    "description": raw.get("description") or "",
                    "flavor": raw.get("flavor") or "",
                    "image_url": raw.get("image_url") or "",
                    "image_url_small": raw.get("image_url_small") or "",
                    "source_url": raw.get("source_url") or "",
                    # No persistimos `raw` para mantener la BD ligera. El JSON
                    # de origen es la fuente de verdad si hace falta re-cargar.
                    "raw": {},
                }
                if (eid := raw.get("external_id")):
                    defaults["external_id"] = eid

                # Buscar primero por external_id (UUID) para soportar
                # renombrados de card_number entre deploys del scraper.
                existing = None
                if eid:
                    existing = RiftboundCard.objects.filter(external_id=eid).first()
                if existing:
                    # Si el card_number cambió, lo actualizamos también.
                    for field, val in {**defaults, "card_number": number}.items():
                        setattr(existing, field, val)
                    existing.save()
                    updated += 1
                else:
                    obj, was_created = RiftboundCard.objects.update_or_create(
                        card_number=number, defaults=defaults,
                    )
                    if was_created:
                        created += 1
                    else:
                        updated += 1

        # Iconos opcionales
        if opts["icons"]:
            ipath = Path(opts["icons"])
            if ipath.exists():
                icons = json.loads(ipath.read_text(encoding="utf-8"))
                for ic in icons:
                    RiftboundIcon.objects.update_or_create(
                        kind=ic["kind"], code=ic["code"],
                        defaults={
                            "label": ic.get("label", ""),
                            "image_url": ic["image_url"],
                            "cdn_image_url": ic.get("cdn_image_url", ""),
                        },
                    )
                self.stdout.write(self.style.SUCCESS(f"Iconos importados: {len(icons)}"))

        self.stdout.write(self.style.SUCCESS(
            f"Cartas: {created} creadas, {updated} actualizadas (total {created+updated})"
        ))

        # Re-aplicar fixes manuales (legend overrides + colores) que viven
        # solo en migraciones one-shot y se pisan con cada recarga.
        from django.core.management import call_command
        self.stdout.write("Re-aplicando fixes manuales...")
        call_command("apply_riftbound_fixes")
