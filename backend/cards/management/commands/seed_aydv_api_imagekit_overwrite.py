"""
Sobrescribe imagenes AYDV en ImageKit usando como fuente la API oficial de MYL.

Flujo recomendado:
1) Local (con acceso a api.myl.cl):
   python manage.py seed_aydv_api_imagekit_overwrite --mapping-file ../aydv_api_imagekit_mapping.json

2) PythonAnywhere (sin acceso a api.myl.cl):
   python manage.py seed_aydv_api_imagekit_overwrite --apply-mapping-only --mapping-file ../aydv_api_imagekit_mapping.json

Notas:
- Se omiten cartas protegidas (JO + nombres protegidos de AYDV).
- Si la carta ya tiene URL ImageKit, intenta reutilizar su path como public_id para overwrite real.
"""

from __future__ import annotations

import json
import os
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from django.core.management.base import BaseCommand, CommandError

from cards.models import Card, Edition


API_CDN_BASE = "https://api.myl.cl/static/cards"
DEFAULT_MAPPING_FILE = Path(__file__).resolve().parents[4] / "aydv_api_imagekit_mapping.json"
DEFAULT_FOLDER = "deckshado/myl_cards/aydv_api_sync_2026_07"
DEFAULT_API_EDITION_ID = "166"

PROTECTED_IMAGE_NAMES = {
    "serpiente del eden",
    "la serpiente del eden",
    "acabar esperanza",
    "acabar la esperanza",
    "agabar esperanza",
    "agabar la esperanza",
    "guerrillero rodriguez",
    "el oro",
    "infernum vox",
}


def _norm(text: str | None) -> str:
    value = (text or "").strip().replace("�", "")
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _slugify(text: str) -> str:
    base = _norm(text).replace(" ", "-")
    base = re.sub(r"-+", "-", base).strip("-")
    return base or "carta"


def _extract_api_edid_candidate(local_edid: str | None) -> str | None:
    value = (local_edid or "").strip().upper()
    if re.fullmatch(r"\d{3}", value):
        return value

    # Ej: AYDV-123 o AYDV-243-P -> 123 / 243
    m = re.fullmatch(r"AYDV-(\d{3})(?:-[A-Z])?", value)
    if m:
        return m.group(1)
    return None


def _extract_imagekit_public_id(url: str | None) -> str | None:
    raw = (url or "").strip()
    if not raw:
        return None
    try:
        parsed = urlparse(raw)
    except Exception:
        return None

    host = (parsed.netloc or "").lower()
    if "ik.imagekit.io" not in host:
        return None

    path = (parsed.path or "").lstrip("/")
    if not path or "." not in path:
        return None
    return path


class Command(BaseCommand):
    help = "Sobrescribe imagenes AYDV en ImageKit usando fuente oficial API MYL"

    def add_arguments(self, parser):
        parser.add_argument(
            "--mapping-file",
            default=str(DEFAULT_MAPPING_FILE),
            help="Ruta de mapping JSON (myl_id -> imagekit_url)",
        )
        parser.add_argument(
            "--apply-mapping-only",
            action="store_true",
            help="No descarga/sube: solo aplica mapping en BD",
        )
        parser.add_argument(
            "--folder",
            default=DEFAULT_FOLDER,
            help="Folder ImageKit para cartas sin public_id existente",
        )
        parser.add_argument(
            "--api-edition-id",
            default=DEFAULT_API_EDITION_ID,
            help="ID de edicion en API para static/cards/<id>/<edid>.png (AYDV=166)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="No guarda cambios en BD",
        )

    def _ensure_repo_imports(self) -> Any:
        repo_root = Path(__file__).resolve().parents[4]
        if str(repo_root) not in sys.path:
            sys.path.insert(0, str(repo_root))

        try:
            import cdn_uploader  # type: ignore
        except Exception as exc:
            raise CommandError(f"No se pudo importar cdn_uploader: {exc}") from exc
        return cdn_uploader

    def _is_protected(self, card: Card) -> bool:
        if (card.myl_id or "").startswith("cbg"):
            return True
        return _norm(card.name) in PROTECTED_IMAGE_NAMES

    def _apply_mapping_only(self, edition: Edition, mapping_file: Path, dry_run: bool) -> None:
        if not mapping_file.exists():
            raise CommandError(f"No existe mapping file: {mapping_file}")

        try:
            mapping = json.loads(mapping_file.read_text(encoding="utf-8"))
        except ValueError as exc:
            raise CommandError(f"Mapping JSON invalido: {mapping_file}") from exc

        if not isinstance(mapping, dict):
            raise CommandError("El mapping debe ser un objeto JSON de myl_id -> url")

        updated = 0
        kept = 0
        missing = 0

        for myl_id, image_url in mapping.items():
            card = Card.objects.filter(edition=edition, myl_id=str(myl_id)).first()
            if not card:
                missing += 1
                continue

            image_url = str(image_url or "").strip()
            if not image_url:
                continue

            if card.custom_image_url == image_url:
                kept += 1
                continue

            if not dry_run:
                card.custom_image_url = image_url
                card.save(update_fields=["custom_image_url"])
            updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Apply mapping done. Updated={updated} Kept={kept} MissingCards={missing}"
            )
        )
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN: no se guardaron cambios en BD."))

    def handle(self, *args, **options):
        mapping_file = Path(options["mapping_file"]).expanduser().resolve()
        apply_mapping_only = bool(options["apply_mapping_only"])
        folder = str(options["folder"] or DEFAULT_FOLDER).strip().strip("/")
        api_edition_id = str(options["api_edition_id"] or DEFAULT_API_EDITION_ID).strip()
        dry_run = bool(options["dry_run"])

        edition = Edition.objects.filter(slug="aydv").first()
        if not edition:
            raise CommandError("No existe la edicion 'aydv' en la base de datos")

        if apply_mapping_only:
            self._apply_mapping_only(edition=edition, mapping_file=mapping_file, dry_run=dry_run)
            return

        cdn_uploader = self._ensure_repo_imports()
        os.environ["CDN_PROVIDER"] = "imagekit"

        cards = list(
            Card.objects.filter(edition=edition)
            .order_by("id")
        )

        total = len(cards)
        uploaded = 0
        skipped_protected = 0
        skipped_no_api_edid = 0
        failed_download = 0
        failed_upload = 0

        mapping: dict[str, str] = {}

        self.stdout.write(self.style.MIGRATE_HEADING("Descargando desde API MYL y sobrescribiendo en ImageKit..."))

        for idx, card in enumerate(cards, start=1):
            if self._is_protected(card):
                skipped_protected += 1
                continue

            api_edid = _extract_api_edid_candidate(card.edid)
            if not api_edid:
                skipped_no_api_edid += 1
                continue

            source_url = f"{API_CDN_BASE}/{api_edition_id}/{api_edid}.png"
            try:
                resp = requests.get(source_url, timeout=45)
                resp.raise_for_status()
            except requests.RequestException:
                failed_download += 1
                self.stdout.write(self.style.WARNING(f"[{idx}/{total}] FAIL download: {card.edid} {card.name}"))
                continue

            content = resp.content
            if not content:
                failed_download += 1
                self.stdout.write(self.style.WARNING(f"[{idx}/{total}] FAIL empty: {card.edid} {card.name}"))
                continue

            public_id = _extract_imagekit_public_id(card.custom_image_url)
            if not public_id:
                safe_name = _slugify(card.name)
                public_id = f"{folder}/{api_edid}_{safe_name}.png"

            if dry_run:
                # En dry-run no ejecutamos upload para evitar consumo de cuota.
                mapping[card.myl_id] = card.custom_image_url or f"https://ik.imagekit.io/<cloud>/{public_id}"
                uploaded += 1
                self.stdout.write(f"[{idx}/{total}] DRY {card.edid} {card.name}")
                continue

            try:
                image_url = cdn_uploader.upload_bytes(
                    content=content,
                    public_id=public_id,
                    default_ext="png",
                    mime_type="image/png",
                    overwrite=True,
                )
            except Exception as exc:
                failed_upload += 1
                self.stdout.write(self.style.WARNING(f"[{idx}/{total}] FAIL upload: {card.edid} {card.name} -> {exc}"))
                continue

            mapping[card.myl_id] = image_url
            uploaded += 1

            if not dry_run and card.custom_image_url != image_url:
                card.custom_image_url = image_url
                card.save(update_fields=["custom_image_url"])

            self.stdout.write(f"[{idx}/{total}] OK {card.edid} {card.name}")

        # Persistir mapping para aplicar en PythonAnywhere sin tocar API.
        mapping_file.parent.mkdir(parents=True, exist_ok=True)
        mapping_file.write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")

        self.stdout.write(
            self.style.SUCCESS(
                "Done. "
                f"Uploaded={uploaded} | "
                f"ProtectedSkip={skipped_protected} | "
                f"NoApiEdidSkip={skipped_no_api_edid} | "
                f"FailedDownload={failed_download} | "
                f"FailedUpload={failed_upload}"
            )
        )
        self.stdout.write(f"Mapping: {mapping_file}")
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN: no se guardaron cambios en BD."))
