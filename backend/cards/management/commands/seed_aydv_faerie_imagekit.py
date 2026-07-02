"""
Seed de cartas Faerie (blog meta) para Angeles y Demonios: Vigilantes usando ImageKit.

Este comando:
- Lee el mapping generado en meta_faerie_blog_pdf_imagekit_mapping.json
- Toma solo las imagenes del blog (descarta banner y entradas de PDF)
- Crea/actualiza la edicion AYDV y upsertea 9 cartas Faerie

Uso local/PA:
    python manage.py seed_aydv_faerie_imagekit
    python manage.py seed_aydv_faerie_imagekit --skip-url-check
    python manage.py seed_aydv_faerie_imagekit --mapping-file /ruta/meta_faerie_blog_pdf_imagekit_mapping.json
"""

from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from cards.models import Card, CardType, Edition, Format, Race

from ._mapping_health import validate_mapping_urls


DEFAULT_MAPPING_FILE = (
    Path(__file__).resolve().parents[4] / "meta_faerie_blog_pdf_imagekit_mapping.json"
)


CARD_SPECS = [
    {
        "source_filename": "Arakiel-11.png",
        "myl_id": "custom_aydv_faerie_arakiel",
        "edid": "AYDV-11",
        "slug": "arakiel-aydv",
        "name": "Arakiel",
    },
    {
        "source_filename": "Armaros-14.png",
        "myl_id": "custom_aydv_faerie_armaros",
        "edid": "AYDV-14",
        "slug": "armaros-aydv",
        "name": "Armaros",
    },
    {
        "source_filename": "Gadriel-13.png",
        "myl_id": "custom_aydv_faerie_gadriel",
        "edid": "AYDV-13",
        "slug": "gadriel-aydv",
        "name": "Gadriel",
    },
    {
        "source_filename": "Sariel-05.png",
        "myl_id": "custom_aydv_faerie_sariel",
        "edid": "AYDV-05",
        "slug": "sariel-aydv",
        "name": "Sariel",
    },
    {
        "source_filename": "Turiel-9-1.png",
        "myl_id": "custom_aydv_faerie_turiel",
        "edid": "AYDV-09",
        "slug": "turiel-aydv",
        "name": "Turiel",
    },
    {
        "source_filename": "Yehadiel-29.png",
        "myl_id": "custom_aydv_faerie_yehadiel",
        "edid": "AYDV-29",
        "slug": "yehadiel-aydv",
        "name": "Yehadiel",
    },
    {
        "source_filename": "Yomiel-10.png",
        "myl_id": "custom_aydv_faerie_yomiel",
        "edid": "AYDV-10",
        "slug": "yomiel-aydv",
        "name": "Yomiel",
    },
    {
        "source_filename": "ezequiel-15.png",
        "myl_id": "custom_aydv_faerie_ezequiel",
        "edid": "AYDV-15",
        "slug": "ezequiel-aydv",
        "name": "Ezequiel",
    },
    {
        "source_filename": "semyazza-05.png",
        "myl_id": "custom_aydv_faerie_semyazza",
        "edid": "AYDV-S5",
        "slug": "semyazza-aydv",
        "name": "Semyazza",
    },
]


class Command(BaseCommand):
    help = "Seed de cartas Faerie AYDV usando mapping ImageKit"

    def add_arguments(self, parser):
        parser.add_argument(
            "--mapping-file",
            default=str(DEFAULT_MAPPING_FILE),
            help="Ruta al JSON de mapping generado por la subida a ImageKit",
        )
        parser.add_argument(
            "--skip-url-check",
            action="store_true",
            help="Omite validacion HTTP de URLs antes del seed",
        )
        parser.add_argument(
            "--url-check-timeout",
            type=int,
            default=10,
            help="Timeout en segundos para health check de URLs",
        )

    def _load_image_map(self, mapping_file: Path) -> dict[str, str]:
        if not mapping_file.exists():
            raise CommandError(f"No existe mapping file: {mapping_file}")

        try:
            payload = json.loads(mapping_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise CommandError(f"JSON invalido en mapping file: {exc}") from exc

        records = payload.get("records")
        if not isinstance(records, list):
            raise CommandError("El mapping no contiene una lista valida en 'records'.")

        image_map: dict[str, str] = {}
        for rec in records:
            if not isinstance(rec, dict):
                continue
            if rec.get("kind") != "blog":
                continue
            if rec.get("status") != "ok":
                continue

            source_url = (rec.get("source_url") or "").strip()
            imagekit_url = (rec.get("imagekit_url") or "").strip()
            if not source_url or not imagekit_url:
                continue

            filename = Path(source_url).name.lower()
            if "banner" in filename:
                continue

            image_map[filename] = imagekit_url

        return image_map

    def handle(self, *args, **options):
        mapping_file = Path(options["mapping_file"]).expanduser().resolve()
        image_map = self._load_image_map(mapping_file)

        required_files = {c["source_filename"].lower() for c in CARD_SPECS}
        missing = sorted(required_files - set(image_map.keys()))
        if missing:
            raise CommandError(
                "Faltan imagenes en el mapping para cartas requeridas: "
                + ", ".join(missing)
            )

        validate_mapping_urls(
            {k: image_map[k] for k in sorted(required_files)},
            self,
            "AYDV Faerie ImageKit",
            skip_check=options["skip_url_check"],
            timeout=max(1, int(options["url_check_timeout"])),
        )

        imp_format, _ = Format.objects.get_or_create(
            code="imp",
            defaults={"name": "Imperio"},
        )

        edition, edition_created = Edition.objects.update_or_create(
            myl_id="custom_aydv",
            defaults={
                "slug": "aydv",
                "title": "Angeles y Demonios: Vigilantes",
                "image": image_map.get("semyazza-05.png", ""),
                "date_release": "2025-07-03",
                "format": imp_format,
                "active": True,
            },
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"{'Created' if edition_created else 'Updated'} edition: {edition.title}"
            )
        )

        aliado_type, _ = CardType.objects.get_or_create(
            slug="aliado",
            defaults={"myl_id": "custom_aliado", "name": "Aliado"},
        )
        faerie_race, _ = Race.objects.get_or_create(
            slug="faerie",
            defaults={"myl_id": "custom_faerie", "name": "Faerie"},
        )

        created_count = 0
        updated_count = 0

        for spec in CARD_SPECS:
            source_filename = spec["source_filename"].lower()
            image_url = image_map[source_filename]

            existing = Card.objects.filter(
                edition=edition,
                name__iexact=spec["name"],
            ).order_by("id").first()

            if existing:
                changed_fields = []
                if (existing.custom_image_url or "") != image_url:
                    existing.custom_image_url = image_url
                    changed_fields.append("custom_image_url")
                if not existing.card_type_id:
                    existing.card_type = aliado_type
                    changed_fields.append("card_type")
                if not existing.race_id:
                    existing.race = faerie_race
                    changed_fields.append("race")

                if changed_fields:
                    existing.save(update_fields=changed_fields)

                updated_count += 1
                self.stdout.write(
                    f"  Updated existing: {existing.name} ({existing.edid})"
                )
                continue

            card, was_created = Card.objects.update_or_create(
                myl_id=spec["myl_id"],
                defaults={
                    "edid": spec["edid"],
                    "slug": spec["slug"],
                    "name": spec["name"],
                    "edition": edition,
                    "rarity": None,
                    "race": faerie_race,
                    "card_type": aliado_type,
                    "cost": None,
                    "damage": None,
                    "ability": "Texto pendiente de carga oficial.",
                    "flavour": "Carta cargada desde blog oficial de Vigilantes.",
                    "custom_image_url": image_url,
                },
            )
            if was_created:
                created_count += 1
            else:
                updated_count += 1
            status = "Created" if was_created else "Updated"
            self.stdout.write(f"  {status}: {card.name} ({card.edid})")

        self.stdout.write(
            self.style.SUCCESS(
                f"Done! Created: {created_count}, Updated: {updated_count}, Total: {len(CARD_SPECS)}"
            )
        )
