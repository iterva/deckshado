"""
Seed/upload de cartas AYDV UR faltantes usando ImageKit.

Este comando permite dos flujos:
1) Upload local + upsert de cartas + generacion de mapping JSON.
2) Solo aplicar mapping JSON en PythonAnywhere (sin subir archivos).

Uso:
  python manage.py seed_aydv_ur_faltantes_imagekit
  python manage.py seed_aydv_ur_faltantes_imagekit --source-dir "C:/ruta/aydv ur faltantes"
  python manage.py seed_aydv_ur_faltantes_imagekit --env-file "C:/ruta/.env_imagekit"
  python manage.py seed_aydv_ur_faltantes_imagekit --apply-mapping-only
"""

from __future__ import annotations

import json
from pathlib import Path

import requests
from django.core.management.base import BaseCommand, CommandError

from cards.models import Card, CardType, Edition, Format, Rarity


UPLOAD_ENDPOINT = "https://upload.imagekit.io/api/v1/files/upload"
DEFAULT_SOURCE_DIR = Path(__file__).resolve().parents[5] / "aydv ur faltantes"
DEFAULT_ENV_FILE = Path(__file__).resolve().parents[5] / ".env_imagekit"
DEFAULT_FOLDER = "/deckshado/myl_cards/aydv_ur_faltantes_2026_07"
DEFAULT_MAPPING_FILE = Path(__file__).resolve().parents[4] / "aydv_ur_faltantes_imagekit_mapping.json"


CARD_SPECS = [
    {
        "filename": "172_010_guerra_celestial.webp",
        "public_id": "aydv_010_150_u_guerra_celestial",
        "myl_id": "custom_aydv_010_150_u",
        "edid": "AYDV-010-150-U",
        "slug": "guerra-celestial-aydv-150-u",
        "name": "Guerra Celestial",
        "type_slug": "talisman",
        "rarity_slug": "ultra-real",
        "cost": "1",
    },
    {
        "filename": "172_013_caida_del_alba.webp",
        "public_id": "aydv_013_150_u_caida_del_alba",
        "myl_id": "custom_aydv_013_150_u",
        "edid": "AYDV-013-150-U",
        "slug": "caida-del-alba-aydv-150-u",
        "name": "Caida del Alba",
        "type_slug": "talisman",
        "rarity_slug": "ultra-real",
        "cost": "1",
    },
    {
        "filename": "172_014_gran_diluvio.webp",
        "public_id": "aydv_014_150_u_gran_diluvio",
        "myl_id": "custom_aydv_014_150_u",
        "edid": "AYDV-014-150-U",
        "slug": "gran-diluvio-aydv-150-u",
        "name": "Gran Diluvio",
        "type_slug": "talisman",
        "rarity_slug": "ultra-real",
        "cost": "3",
    },
    {
        "filename": "172_015_vision_de_enoc.webp",
        "public_id": "aydv_015_150_u_vision_de_enoc",
        "myl_id": "custom_aydv_015_150_u",
        "edid": "AYDV-015-150-U",
        "slug": "vision-de-enoc-aydv-150-u",
        "name": "Vision de Enoc",
        "type_slug": "talisman",
        "rarity_slug": "ultra-real",
        "cost": "1",
    },
    {
        "filename": "172_016_septimo_sello.webp",
        "public_id": "aydv_016_150_u_septimo_sello",
        "myl_id": "custom_aydv_016_150_u",
        "edid": "AYDV-016-150-U",
        "slug": "septimo-sello-aydv-150-u",
        "name": "Septimo Sello",
        "type_slug": "talisman",
        "rarity_slug": "ultra-real",
        "cost": "2",
    },
    {
        "filename": "172_017_espada_del_juicio.webp",
        "public_id": "aydv_017_150_u_espada_del_juicio",
        "myl_id": "custom_aydv_017_150_u",
        "edid": "AYDV-017-150-U",
        "slug": "espada-del-juicio-aydv-150-u",
        "name": "Espada del Juicio",
        "type_slug": "arma",
        "rarity_slug": "ultra-real",
        "cost": "1",
    },
    {
        "filename": "172_018_el_arca.webp",
        "public_id": "aydv_018_150_u_el_arca",
        "myl_id": "custom_aydv_018_150_u",
        "edid": "AYDV-018-150-U",
        "slug": "el-arca-aydv-150-u",
        "name": "El Arca",
        "type_slug": "totem",
        "rarity_slug": "ultra-real",
        "cost": "1",
    },
    {
        "filename": "172_019_libro_de_enoc.webp",
        "public_id": "aydv_019_150_u_libro_de_enoc",
        "myl_id": "custom_aydv_019_150_u",
        "edid": "AYDV-019-150-U",
        "slug": "libro-de-enoc-aydv-150-u",
        "name": "Libro de Enoc",
        "type_slug": "oro",
        "rarity_slug": "ultra-real",
        "cost": "1",
    },
    {
        "filename": "172_020_libro_de_revelaciones.webp",
        "public_id": "aydv_020_150_u_libro_de_revelaciones",
        "myl_id": "custom_aydv_020_150_u",
        "edid": "AYDV-020-150-U",
        "slug": "libro-de-revelaciones-aydv-150-u",
        "name": "Libro de Revelaciones",
        "type_slug": "oro",
        "rarity_slug": "ultra-real",
        "cost": None,
    },
    {
        "filename": "172_090_tablas_del_juramento.webp",
        "public_id": "aydv_090_150_r_tablas_del_juramento",
        "myl_id": "custom_aydv_090_150_r",
        "edid": "AYDV-090-150-R",
        "slug": "tablas-del-juramento-aydv-150-r",
        "name": "Tablas del Juramento",
        "type_slug": "talisman",
        "rarity_slug": "real",
        "cost": None,
    },
    {
        "filename": "172_232_infernum_vox.webp",
        "public_id": "aydv_232_p_infernum_vox",
        "myl_id": "custom_aydv_232_p",
        "edid": "AYDV-232-P",
        "slug": "infernum-vox-aydv-p",
        "name": "Infernum Vox",
        "type_slug": "oro",
        "rarity_slug": "promo",
        "cost": None,
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


def _endpoint_from_env(env_map: dict[str, str]) -> str:
    endpoint = (
        env_map.get("IMAGEKIT_URL_ENDPOINT")
        or env_map.get("url")
        or ""
    ).strip().rstrip("/")
    return endpoint


class Command(BaseCommand):
    help = "Sube 11 cartas AYDV UR faltantes a ImageKit y hace upsert en BD"

    def add_arguments(self, parser):
        parser.add_argument(
            "--source-dir",
            default=str(DEFAULT_SOURCE_DIR),
            help="Carpeta con archivos de cartas faltantes",
        )
        parser.add_argument(
            "--env-file",
            default=str(DEFAULT_ENV_FILE),
            help="Archivo con credenciales de ImageKit",
        )
        parser.add_argument(
            "--folder",
            default=DEFAULT_FOLDER,
            help="Folder destino en ImageKit",
        )
        parser.add_argument(
            "--mapping-file",
            default=str(DEFAULT_MAPPING_FILE),
            help="Ruta de salida/entrada para mapping JSON",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="No sube archivos ni escribe cambios en BD",
        )
        parser.add_argument(
            "--apply-mapping-only",
            action="store_true",
            help="No sube archivos: solo aplica URLs desde mapping JSON",
        )

    def _ensure_edition(self):
        imp_format, _ = Format.objects.get_or_create(
            code="imp",
            defaults={"name": "Imperio"},
        )

        edition, _ = Edition.objects.update_or_create(
            myl_id="custom_aydv",
            defaults={
                "slug": "aydv",
                "title": "Angeles y Demonios: Vigilantes",
                "format": imp_format,
                "active": True,
            },
        )
        return edition

    def _load_mapping(self, mapping_file: Path) -> dict[str, str]:
        if not mapping_file.exists():
            raise CommandError(f"No existe mapping file: {mapping_file}")

        try:
            payload = json.loads(mapping_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise CommandError(f"JSON invalido en mapping file: {exc}") from exc

        records = payload.get("records")
        if not isinstance(records, list):
            raise CommandError("El mapping no contiene lista valida en 'records'.")

        urls: dict[str, str] = {}
        for rec in records:
            if not isinstance(rec, dict):
                continue
            public_id = (rec.get("public_id") or "").strip()
            image_url = (rec.get("imagekit_url") or "").strip()
            if public_id and image_url:
                urls[public_id] = image_url
        return urls

    def _resolve_card_type(self, slug: str | None):
        if not slug:
            return None
        return CardType.objects.filter(slug=slug).first()

    def _resolve_rarity(self, slug: str | None):
        if not slug:
            return None
        return Rarity.objects.filter(slug=slug).first()

    def _upsert_card(self, edition: Edition, spec: dict, image_url: str, dry_run: bool) -> str:
        card = Card.objects.filter(myl_id=spec["myl_id"]).first()
        if card is None:
            card = Card.objects.filter(edition=edition, edid=spec["edid"]).order_by("id").first()

        card_type = self._resolve_card_type(spec.get("type_slug"))
        rarity = self._resolve_rarity(spec.get("rarity_slug"))

        if card_type is None and spec.get("type_slug"):
            self.stdout.write(self.style.WARNING(
                f"WARN sin CardType '{spec['type_slug']}' para {spec['name']}"
            ))
        if rarity is None and spec.get("rarity_slug"):
            self.stdout.write(self.style.WARNING(
                f"WARN sin Rarity '{spec['rarity_slug']}' para {spec['name']}"
            ))

        defaults = {
            "myl_id": spec["myl_id"],
            "edid": spec["edid"],
            "slug": spec["slug"],
            "name": spec["name"],
            "edition": edition,
            "rarity": rarity,
            "race": None,
            "card_type": card_type,
            "cost": spec.get("cost"),
            "damage": None,
            "ability": None,
            "flavour": None,
            "custom_image_url": image_url,
        }

        if card is None:
            if dry_run:
                return "WOULD_CREATE"
            Card.objects.create(**defaults)
            return "CREATED"

        changed_fields: list[str] = []
        for key, value in defaults.items():
            current = getattr(card, key)
            if current != value:
                setattr(card, key, value)
                changed_fields.append(key)

        if not changed_fields:
            return "KEEP"

        if dry_run:
            return "WOULD_UPDATE"

        card.save(update_fields=changed_fields)
        return "UPDATED"

    def handle(self, *args, **options):
        source_dir = Path(options["source_dir"]).expanduser().resolve()
        env_file = Path(options["env_file"]).expanduser().resolve()
        folder = str(options["folder"]).strip() or DEFAULT_FOLDER
        mapping_file = Path(options["mapping_file"]).expanduser().resolve()
        dry_run = bool(options["dry_run"])
        apply_mapping_only = bool(options["apply_mapping_only"])

        edition = self._ensure_edition()

        if apply_mapping_only:
            mapping_urls = self._load_mapping(mapping_file)
            created = 0
            updated = 0
            kept = 0

            self.stdout.write(self.style.MIGRATE_HEADING("Aplicando mapping a cartas AYDV UR faltantes..."))
            for spec in CARD_SPECS:
                image_url = mapping_urls.get(spec["public_id"])
                if not image_url:
                    raise CommandError(
                        f"Falta URL en mapping para public_id={spec['public_id']}"
                    )

                status = self._upsert_card(edition, spec, image_url, dry_run=dry_run)
                if status in {"CREATED", "WOULD_CREATE"}:
                    created += 1
                elif status in {"UPDATED", "WOULD_UPDATE"}:
                    updated += 1
                else:
                    kept += 1

                self.stdout.write(
                    f"  {status}: {spec['name']} ({spec['edid']})"
                )

            self.stdout.write(
                self.style.SUCCESS(
                    f"Done. Created={created} Updated={updated} Kept={kept}"
                )
            )
            return

        if not source_dir.exists() or not source_dir.is_dir():
            raise CommandError(f"Source dir no existe: {source_dir}")

        env_map = _parse_env_file(env_file)
        auth = _build_auth(env_map)
        endpoint = _endpoint_from_env(env_map)

        uploads: list[dict[str, str]] = []
        created = 0
        updated = 0
        kept = 0

        self.stdout.write(self.style.MIGRATE_HEADING("Subiendo cartas a ImageKit y aplicando seed..."))

        for spec in CARD_SPECS:
            file_path = source_dir / spec["filename"]
            if not file_path.exists():
                raise CommandError(f"Falta archivo requerido: {file_path}")

            ext = file_path.suffix.lower() or ".webp"

            if dry_run:
                base = endpoint or "https://ik.imagekit.io/<cloud>"
                image_url = f"{base.rstrip('/')}/{folder.strip('/')}/{spec['public_id']}{ext}"
            else:
                with file_path.open("rb") as fp:
                    response = requests.post(
                        UPLOAD_ENDPOINT,
                        auth=auth,
                        files={"file": (file_path.name, fp, "application/octet-stream")},
                        data={
                            "fileName": f"{spec['public_id']}{ext}",
                            "folder": folder,
                            "useUniqueFileName": "false",
                            "overwriteFile": "true",
                            "isPrivateFile": "false",
                        },
                        timeout=90,
                    )

                if response.status_code >= 300:
                    raise CommandError(
                        f"ImageKit fallo ({response.status_code}) para {file_path.name}: {response.text[:400]}"
                    )

                payload = response.json()
                image_url = (payload.get("url") or "").strip()
                if not image_url:
                    raise CommandError(f"ImageKit no devolvio URL para {file_path.name}")

            status = self._upsert_card(edition, spec, image_url, dry_run=dry_run)
            if status in {"CREATED", "WOULD_CREATE"}:
                created += 1
            elif status in {"UPDATED", "WOULD_UPDATE"}:
                updated += 1
            else:
                kept += 1

            uploads.append(
                {
                    "filename": spec["filename"],
                    "name": spec["name"],
                    "edid": spec["edid"],
                    "myl_id": spec["myl_id"],
                    "public_id": spec["public_id"],
                    "imagekit_url": image_url,
                    "status": "ok",
                }
            )
            self.stdout.write(f"  {status}: {spec['name']} ({spec['edid']}) -> {image_url}")

        output = {
            "kind": "aydv_ur_faltantes_imagekit",
            "folder": folder,
            "records": uploads,
        }

        if not dry_run:
            mapping_file.write_text(
                json.dumps(output, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Uploads={len(uploads)} Created={created} Updated={updated} Kept={kept} Mapping={mapping_file}"
            )
        )
