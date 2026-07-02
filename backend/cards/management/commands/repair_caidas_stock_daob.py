"""
Repara cartas caidas y reemplaza 2 imagenes stock en cloud activo (daobfx9yb).

Cartas incluidas:
- CHI-05 Exorcismo de Carmen Marin
- CHI-08 Estacion Fantasma
- CHI-14 Machete del Abuelo
- CHI-16 Hospital San Jose
- TK26-15 Celebrar la Muerte
- TK26-18 Calaveras de Azucar

Uso:
  python manage.py repair_caidas_stock_daob
  python manage.py repair_caidas_stock_daob --source-dir "/ruta/cartas por subir 8"
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import cloudinary
import cloudinary.uploader
from django.core.management.base import BaseCommand, CommandError

from cards.models import Card


CLOUDINARY_FOLDER = "deckshado/extra_cards"
DEFAULT_SOURCE_DIR = Path(__file__).resolve().parents[5] / "cartas por subir 8"
MAPPING_FILE = Path(__file__).resolve().parents[4] / "cloudinary_mapping.json"


CARD_IMAGE_SPECS = [
    {
        "filename": "C-O-2-164_005_exorcismo_de_carmen_marin.webp",
        "public_id": "c-o-2_05",
        "myl_id": "custom_co2_05",
        "edid": "CHI-05",
        "edition_slug": "chile_oscuro_2",
        "name": "Exorcismo de Carmen Marin",
    },
    {
        "filename": "C-O-2-164_008_estacion_fantasma.webp",
        "public_id": "c-o-2_08",
        "myl_id": "custom_co2_08",
        "edid": "CHI-08",
        "edition_slug": "chile_oscuro_2",
        "name": "Estacion Fantasma",
    },
    {
        "filename": "C-O-2-164_014_machete_del_abuelo.webp",
        "public_id": "c-o-2_14",
        "myl_id": "custom_co2_14",
        "edid": "CHI-14",
        "edition_slug": "chile_oscuro_2",
        "name": "Machete del Abuelo",
    },
    {
        "filename": "C-O-2-164_016_hospital_san_jose.webp",
        "public_id": "c-o-2_16",
        "myl_id": "custom_co2_16",
        "edid": "CHI-16",
        "edition_slug": "chile_oscuro_2",
        "name": "Hospital San Jose",
    },
    {
        "filename": "tk-26-163_015_celebrar_la_muerte.webp",
        "public_id": "tk26_15",
        "myl_id": "custom_tk26_15",
        "edid": "15",
        "edition_slug": "toolkit_26_imp",
        "name": "Celebrar la Muerte",
    },
    {
        "filename": "tk-26-163_018_calaveras_azucar.webp",
        "public_id": "tk26_18",
        "myl_id": "custom_tk26_18",
        "edid": "18",
        "edition_slug": "toolkit_26_imp",
        "name": "Calaveras de Azucar",
    },
]


def _configure_cloudinary() -> None:
    cloudinary.config(
        cloud_name=(os.environ.get("CLOUDINARY_CLOUD_NAME") or "daobfx9yb"),
        api_key=os.environ.get("CLOUDINARY_API_KEY"),
        api_secret=os.environ.get("CLOUDINARY_API_SECRET"),
        secure=True,
    )


class Command(BaseCommand):
    help = "Repara 6 cartas con imagen caida/stock subiendo a daobfx9yb"

    def add_arguments(self, parser):
        parser.add_argument(
            "--source-dir",
            default=str(DEFAULT_SOURCE_DIR),
            help="Carpeta con los archivos de imagen a subir",
        )

    def _load_mapping(self) -> dict:
        if not MAPPING_FILE.exists():
            return {"extra_cards": {}}
        try:
            return json.loads(MAPPING_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise CommandError(f"No se pudo parsear {MAPPING_FILE}: {exc}") from exc

    def _save_mapping(self, mapping: dict) -> None:
        MAPPING_FILE.write_text(
            json.dumps(mapping, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def _update_card_url(self, spec: dict, url: str) -> int:
        updated = Card.objects.filter(myl_id=spec["myl_id"]).update(custom_image_url=url)
        if updated:
            return updated

        updated = Card.objects.filter(
            edid=spec["edid"],
            edition__slug=spec["edition_slug"],
        ).update(custom_image_url=url)
        if updated:
            return updated

        return Card.objects.filter(name__iexact=spec["name"]).update(custom_image_url=url)

    def handle(self, *args, **options):
        _configure_cloudinary()

        source_dir = Path(options["source_dir"]).expanduser().resolve()
        if not source_dir.exists() or not source_dir.is_dir():
            raise CommandError(f"Source dir no existe: {source_dir}")

        mapping = self._load_mapping()
        extra_cards = mapping.setdefault("extra_cards", {})

        uploaded = 0
        updated_cards = 0

        self.stdout.write(self.style.MIGRATE_HEADING("Subiendo imagenes a Cloudinary..."))

        for spec in CARD_IMAGE_SPECS:
            filepath = source_dir / spec["filename"]
            if not filepath.exists():
                raise CommandError(f"Falta archivo requerido: {filepath}")

            full_public_id = f"{CLOUDINARY_FOLDER}/{spec['public_id']}"
            result = cloudinary.uploader.upload(
                str(filepath),
                public_id=full_public_id,
                overwrite=True,
                resource_type="image",
            )

            url = (result.get("secure_url") or "").strip()
            if not url:
                raise CommandError(f"Cloudinary no devolvio secure_url para {filepath.name}")

            uploaded += 1
            self.stdout.write(f"  OK {spec['name']} -> {url}")

            updated = self._update_card_url(spec, url)
            if not updated:
                self.stdout.write(self.style.WARNING(f"  WARN sin match en BD: {spec['name']}"))
            else:
                updated_cards += updated

            ext = url.rsplit(".", 1)[-1].lower()
            extra_cards[f"{spec['public_id']}.{ext}"] = url

        self._save_mapping(mapping)

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Uploads: {uploaded}, cartas actualizadas: {updated_cards}, mapping: {MAPPING_FILE}"
            )
        )