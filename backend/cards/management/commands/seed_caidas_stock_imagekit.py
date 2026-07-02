"""
Seed/reparacion de 6 cartas (caidas y stock) usando ImageKit.

Sube las imagenes a ImageKit y actualiza Card.custom_image_url.

Uso:
  python manage.py seed_caidas_stock_imagekit
  python manage.py seed_caidas_stock_imagekit --source-dir "C:/ruta/cartas por subir 8"
  python manage.py seed_caidas_stock_imagekit --env-file "C:/ruta/.env_imagekit copy"
"""

from __future__ import annotations

import json
from pathlib import Path

import requests
from django.core.management.base import BaseCommand, CommandError

from cards.models import Card


UPLOAD_ENDPOINT = "https://upload.imagekit.io/api/v1/files/upload"
DEFAULT_SOURCE_DIR = Path(__file__).resolve().parents[5] / "cartas por subir 8"
DEFAULT_ENV_FILE = Path(__file__).resolve().parents[5] / ".env_imagekit copy"
DEFAULT_FOLDER = "/deckshado/extra_cards"
MAPPING_FILE = Path(__file__).resolve().parents[4] / "caidas_stock_imagekit_mapping.json"


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


def _parse_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        raise CommandError(f"No existe env file: {path}")

    data: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def _build_auth(env_map: dict[str, str]) -> tuple[str, str]:
    private_key = (
        env_map.get("IMAGEKIT_PRIVATE_KEY")
        or env_map.get("private_key")
        or ""
    ).strip()
    if not private_key:
        raise CommandError("No se encontro IMAGEKIT_PRIVATE_KEY/private_key en el env file")
    return private_key, ""


class Command(BaseCommand):
    help = "Sube 6 imagenes caidas/stock a ImageKit y actualiza custom_image_url"

    def add_arguments(self, parser):
        parser.add_argument(
            "--source-dir",
            default=str(DEFAULT_SOURCE_DIR),
            help="Carpeta con los archivos a subir",
        )
        parser.add_argument(
            "--env-file",
            default=str(DEFAULT_ENV_FILE),
            help="Archivo con credenciales ImageKit",
        )
        parser.add_argument(
            "--folder",
            default=DEFAULT_FOLDER,
            help="Folder destino en ImageKit (default: /deckshado/extra_cards)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="No sube ni guarda cambios en BD",
        )

    def _update_card_url(self, spec: dict, image_url: str, dry_run: bool) -> int:
        by_myl = Card.objects.filter(myl_id=spec["myl_id"])
        if by_myl.exists():
            if not dry_run:
                return by_myl.update(custom_image_url=image_url)
            return by_myl.count()

        by_edid = Card.objects.filter(
            edid=spec["edid"],
            edition__slug=spec["edition_slug"],
        )
        if by_edid.exists():
            if not dry_run:
                return by_edid.update(custom_image_url=image_url)
            return by_edid.count()

        by_name = Card.objects.filter(name__iexact=spec["name"])
        if by_name.exists():
            if not dry_run:
                return by_name.update(custom_image_url=image_url)
            return by_name.count()

        return 0

    def handle(self, *args, **options):
        source_dir = Path(options["source_dir"]).expanduser().resolve()
        env_file = Path(options["env_file"]).expanduser().resolve()
        folder = str(options["folder"]).strip() or DEFAULT_FOLDER
        dry_run = bool(options["dry_run"])

        if not source_dir.exists() or not source_dir.is_dir():
            raise CommandError(f"Source dir no existe: {source_dir}")

        env_map = _parse_env_file(env_file)
        auth = _build_auth(env_map)

        uploads: list[dict[str, str]] = []
        updated_cards = 0

        self.stdout.write(self.style.MIGRATE_HEADING("Subiendo imagenes a ImageKit..."))

        for spec in CARD_IMAGE_SPECS:
            filepath = source_dir / spec["filename"]
            if not filepath.exists():
                raise CommandError(f"Falta archivo requerido: {filepath}")

            if dry_run:
                fake_url = f"https://ik.imagekit.io/<cloud>{folder}/{spec['public_id']}.webp"
                uploads.append({
                    "name": spec["name"],
                    "public_id": spec["public_id"],
                    "imagekit_url": fake_url,
                    "source_file": str(filepath),
                })
                updated_cards += self._update_card_url(spec, fake_url, dry_run=True)
                self.stdout.write(f"  DRY {spec['name']} -> {fake_url}")
                continue

            with filepath.open("rb") as fp:
                response = requests.post(
                    UPLOAD_ENDPOINT,
                    auth=auth,
                    files={"file": (filepath.name, fp, "application/octet-stream")},
                    data={
                        "fileName": f"{spec['public_id']}{filepath.suffix.lower()}",
                        "folder": folder,
                        "useUniqueFileName": "false",
                        "overwriteFile": "true",
                        "isPrivateFile": "false",
                    },
                    timeout=90,
                )

            if response.status_code >= 300:
                raise CommandError(
                    f"ImageKit fallo ({response.status_code}) para {filepath.name}: {response.text[:400]}"
                )

            payload = response.json()
            image_url = (payload.get("url") or "").strip()
            if not image_url:
                raise CommandError(f"ImageKit no devolvio url para {filepath.name}: {payload}")

            uploads.append({
                "name": spec["name"],
                "public_id": spec["public_id"],
                "imagekit_url": image_url,
                "source_file": str(filepath),
            })
            self.stdout.write(f"  OK {spec['name']} -> {image_url}")

            matches = self._update_card_url(spec, image_url, dry_run=False)
            if matches:
                updated_cards += matches
            else:
                self.stdout.write(self.style.WARNING(f"  WARN sin match en BD: {spec['name']}"))

        output = {
            "kind": "caidas_stock_imagekit",
            "folder": folder,
            "records": uploads,
        }

        if not dry_run:
            MAPPING_FILE.write_text(
                json.dumps(output, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Uploads: {len(uploads)}, cartas actualizadas: {updated_cards}, mapping: {MAPPING_FILE}"
            )
        )
