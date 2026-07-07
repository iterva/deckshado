"""
Seed de cartas del blog "Raza Caballero y todo lo que necesitas saber".

Uso:
  python manage.py seed_aydv_blog_caballero
  python manage.py seed_aydv_blog_caballero --skip-url-check
  python manage.py seed_aydv_blog_caballero --mapping-file /ruta/aydv_blog_caballero_mapping.json
"""

from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from cards.models import Card, CardType, Edition, Format, Race, Rarity

from ._mapping_health import validate_mapping_urls


DEFAULT_MAPPING_FILE = (
    Path(__file__).resolve().parents[4] / "aydv_blog_caballero_mapping.json"
)


CARD_SPECS = [
    {
        "myl_id": "custom_aydv_blog_cab_001",
        "edid": "AYDV-CAB-001",
        "slug": "miguel-el-capitan-aydv-cab",
        "name": "Miguel (El Capitan)",
        "cloudinary_id": "aydv_cab_miguel",
        "rarity_slug": "ultrareal",
        "ability": "Descarta dos cartas de la mano del oponente.",
    },
    {
        "myl_id": "custom_aydv_blog_cab_002",
        "edid": "AYDV-CAB-002",
        "slug": "zadquiel-aydv-cab",
        "name": "Zadquiel",
        "cloudinary_id": "aydv_cab_zadquiel",
        "rarity_slug": "megareal",
        "ability": "Nombra una carta de la mano rival para que no pueda jugarse hasta tu proximo turno.",
    },
    {
        "myl_id": "custom_aydv_blog_cab_003",
        "edid": "AYDV-CAB-003",
        "slug": "danel-aydv-cab",
        "name": "Danel",
        "cloudinary_id": "aydv_cab_danel",
        "rarity_slug": "real",
        "ability": "Ambos jugadores descartan; si descartas un Arma obtienes ventaja.",
    },
    {
        "myl_id": "custom_aydv_blog_cab_004",
        "edid": "AYDV-CAB-004",
        "slug": "camael-aydv-cab",
        "name": "Camael",
        "cloudinary_id": "aydv_cab_camael",
        "rarity_slug": "real",
        "ability": "Cada vez que juegues un Arma, fuerzas descarte al oponente.",
    },
    {
        "myl_id": "custom_aydv_blog_cab_005",
        "edid": "AYDV-CAB-005",
        "slug": "remiel-aydv-cab",
        "name": "Remiel",
        "cloudinary_id": "aydv_cab_remiel",
        "rarity_slug": "real",
        "ability": "Busca Aliados y Armas para mantener consistencia de recursos.",
    },
    {
        "myl_id": "custom_aydv_blog_cab_006",
        "edid": "AYDV-CAB-006",
        "slug": "raguel-aydv-cab",
        "name": "Raguel",
        "cloudinary_id": "aydv_cab_raguel",
        "rarity_slug": "cortesano",
        "ability": "Castiga estrategias que ponen multiples Oros o abusan de Talismanes.",
    },
    {
        "myl_id": "custom_aydv_blog_cab_007",
        "edid": "AYDV-CAB-007",
        "slug": "arturo-de-bretana-aydv-cab",
        "name": "Arturo de Bretana",
        "cloudinary_id": "aydv_cab_arturo_bretana",
        "rarity_slug": "set-inmortal",
        "ability": "Aliado inmortal que complementa la estrategia de Armas de Caballero.",
    },
]


class Command(BaseCommand):
    help = "Seed de cartas blog Caballero (AYDV) usando mapping ya subido a Cloudinary"

    def add_arguments(self, parser):
        parser.add_argument(
            "--mapping-file",
            default=str(DEFAULT_MAPPING_FILE),
            help="Ruta al mapping JSON (cloudinary_id -> url)",
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

    def _load_mapping(self, mapping_file: Path) -> dict[str, str]:
        if not mapping_file.exists():
            raise CommandError(f"No existe mapping file: {mapping_file}")

        try:
            payload = json.loads(mapping_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise CommandError(f"JSON invalido en mapping file: {exc}") from exc

        if not isinstance(payload, dict):
            raise CommandError("El mapping debe ser un objeto JSON (cloudinary_id -> url).")

        mapping: dict[str, str] = {}
        for key, value in payload.items():
            if not isinstance(key, str):
                continue
            if not isinstance(value, str):
                continue
            mapping[key.strip()] = value.strip()

        return mapping

    def handle(self, *args, **options):
        mapping_file = Path(options["mapping_file"]).expanduser().resolve()
        image_map = self._load_mapping(mapping_file)

        required_ids = {c["cloudinary_id"] for c in CARD_SPECS}
        missing = sorted(required_ids - set(image_map.keys()))
        if missing:
            raise CommandError(
                "Faltan imagenes en mapping para IDs requeridos: " + ", ".join(missing)
            )

        validate_mapping_urls(
            {cid: image_map[cid] for cid in sorted(required_ids)},
            self,
            "AYDV Blog Caballero",
            skip_check=options["skip_url_check"],
            timeout=max(1, int(options["url_check_timeout"])),
        )

        imp_format, _ = Format.objects.get_or_create(
            code="imp",
            defaults={"name": "Imperio"},
        )

        edition, edition_created = Edition.objects.update_or_create(
            myl_id="custom_aydv_blog_caballero",
            defaults={
                "slug": "aydv-blog-caballero",
                "title": "AYDV Blog Caballero (Jul 2026)",
                "image": image_map.get("aydv_cab_miguel", ""),
                "format": imp_format,
                "active": True,
            },
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"{'Created' if edition_created else 'Updated'} edition: {edition.title}"
            )
        )

        card_type = CardType.objects.filter(slug="aliado").first()
        if not card_type:
            raise CommandError("No existe CardType con slug 'aliado'.")

        race = Race.objects.filter(slug="caballero").first()
        if not race:
            race, _ = Race.objects.get_or_create(
                myl_id="custom_caballero",
                slug="caballero",
                defaults={"name": "Caballero"},
            )

        created_count = 0
        updated_count = 0

        for spec in CARD_SPECS:
            rarity = Rarity.objects.filter(slug=spec["rarity_slug"]).first()
            image_url = image_map[spec["cloudinary_id"]]

            card, was_created = Card.objects.update_or_create(
                myl_id=spec["myl_id"],
                defaults={
                    "edid": spec["edid"],
                    "slug": spec["slug"],
                    "name": spec["name"],
                    "edition": edition,
                    "rarity": rarity,
                    "race": race,
                    "card_type": card_type,
                    "cost": None,
                    "damage": None,
                    "ability": spec["ability"],
                    "flavour": "",
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
