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
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from django.core.management.base import BaseCommand, CommandError

from cards.models import Card, Edition


API_CDN_BASE = "https://api.myl.cl/static/cards"
API_CARDS_ENDPOINT = "https://api.myl.cl/cards/edition/ayd_vigilantes"
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
    "gehena",
    "dulce canasta",
    "don de belial",
    "serafin",
    "santo santo santo",
    "mano de destruccion",
    "miguel grau",
    "lanza argenta",
    "nefandos",
    "jinete de la peste",
    "jinete del hambre",
    "jinete de la muerte",
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


def _safe_api_edid(raw: Any) -> str | None:
    text = str(raw or "").strip()
    if not text:
        return None
    if text.isdigit():
        return text.zfill(3)
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
        parser.add_argument(
            "--start-index",
            type=int,
            default=1,
            help="Indice 1-based inicial sobre cartas AYDV ordenadas por id (default: 1)",
        )
        parser.add_argument(
            "--end-index",
            type=int,
            default=0,
            help="Indice 1-based final sobre cartas AYDV ordenadas por id (0 = hasta el final)",
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

    def _fetch_api_cards(self) -> list[dict[str, Any]]:
        try:
            resp = requests.get(API_CARDS_ENDPOINT, timeout=45)
            resp.raise_for_status()
            payload = resp.json()
        except requests.RequestException as exc:
            raise CommandError(f"No se pudo descargar API AYDV: {exc}") from exc
        except ValueError as exc:
            raise CommandError("Respuesta invalida desde API AYDV") from exc

        cards = payload.get("cards", []) if isinstance(payload, dict) else []
        if not isinstance(cards, list):
            raise CommandError("Payload de API AYDV sin lista de cards")
        return cards

    def _build_api_indexes(
        self,
        api_cards: list[dict[str, Any]],
    ) -> tuple[dict[str, list[dict[str, Any]]], dict[str, dict[str, Any]], list[tuple[str, dict[str, Any]]]]:
        by_name: dict[str, list[dict[str, Any]]] = {}
        by_edid: dict[str, dict[str, Any]] = {}
        flat: list[tuple[str, dict[str, Any]]] = []

        for raw in api_cards:
            name_key = _norm(str(raw.get("name") or ""))
            edid_key = _safe_api_edid(raw.get("edid"))
            if not name_key or not edid_key:
                continue
            by_name.setdefault(name_key, []).append(raw)
            by_edid[edid_key] = raw
            flat.append((name_key, raw))

        return by_name, by_edid, flat

    def _pick_from_name_matches(
        self,
        card: Card,
        candidates: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        if not candidates:
            return None
        if len(candidates) == 1:
            return candidates[0]

        # Preferir match por EDID local cuando hay multiples cartas con mismo nombre.
        local_edid = _extract_api_edid_candidate(card.edid)
        if local_edid:
            for c in candidates:
                if _safe_api_edid(c.get("edid")) == local_edid:
                    return c

        # Fallback estable: menor edid numerico.
        ordered = sorted(candidates, key=lambda x: int(_safe_api_edid(x.get("edid")) or "999"))
        return ordered[0]

    def _best_fuzzy_api_match(
        self,
        card: Card,
        api_flat: list[tuple[str, dict[str, Any]]],
    ) -> dict[str, Any] | None:
        target = _norm(card.name)
        if not target:
            return None

        best_score = 0.0
        best_raw: dict[str, Any] | None = None
        for api_name, raw in api_flat:
            score = SequenceMatcher(None, target, api_name).ratio()
            if score > best_score:
                best_score = score
                best_raw = raw

        if best_raw is None:
            return None
        if best_score < 0.90:
            return None
        return best_raw

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
        start_index = max(1, int(options.get("start_index") or 1))
        end_index = int(options.get("end_index") or 0)
        if end_index and end_index < start_index:
            raise CommandError("--end-index debe ser mayor o igual a --start-index")

        edition = Edition.objects.filter(slug="aydv").first()
        if not edition:
            raise CommandError("No existe la edicion 'aydv' en la base de datos")

        if apply_mapping_only:
            self._apply_mapping_only(edition=edition, mapping_file=mapping_file, dry_run=dry_run)
            return

        cdn_uploader = self._ensure_repo_imports()
        os.environ["CDN_PROVIDER"] = "imagekit"

        api_cards = self._fetch_api_cards()
        by_name, _by_edid, api_flat = self._build_api_indexes(api_cards)

        cards = list(
            Card.objects.filter(edition=edition)
            .order_by("id")
        )

        total = len(cards)
        uploaded = 0
        skipped_protected = 0
        skipped_no_api_match = 0
        failed_download = 0
        failed_upload = 0
        fuzzy_matched = 0

        mapping: dict[str, str] = {}
        if mapping_file.exists():
            try:
                existing = json.loads(mapping_file.read_text(encoding="utf-8"))
                if isinstance(existing, dict):
                    mapping = {str(k): str(v) for k, v in existing.items()}
            except ValueError:
                # Si el archivo existe pero no es JSON valido, se regenera desde cero al final.
                mapping = {}

        range_text = f"indices {start_index}-{end_index or total}"
        self.stdout.write(self.style.MIGRATE_HEADING(f"Descargando desde API MYL y sobrescribiendo en ImageKit ({range_text})..."))

        for idx, card in enumerate(cards, start=1):
            if idx < start_index:
                continue
            if end_index and idx > end_index:
                break

            if self._is_protected(card):
                skipped_protected += 1
                continue

            card_name_key = _norm(card.name)
            api_raw = self._pick_from_name_matches(card, by_name.get(card_name_key, []))
            if api_raw is None:
                api_raw = self._best_fuzzy_api_match(card, api_flat)
                if api_raw is not None:
                    fuzzy_matched += 1

            api_edid = _safe_api_edid(api_raw.get("edid") if api_raw else None)
            if not api_edid:
                skipped_no_api_match += 1
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
                f"NoApiMatchSkip={skipped_no_api_match} | "
                f"FuzzyMatched={fuzzy_matched} | "
                f"FailedDownload={failed_download} | "
                f"FailedUpload={failed_upload}"
            )
        )
        self.stdout.write(f"Mapping: {mapping_file}")
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN: no se guardaron cambios en BD."))
