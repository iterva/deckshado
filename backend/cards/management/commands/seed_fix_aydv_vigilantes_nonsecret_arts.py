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


API_CARDS_ENDPOINT = "https://api.myl.cl/cards/edition/ayd_vigilantes"
API_CDN_BASE = "https://api.myl.cl/static/cards"
DEFAULT_API_EDITION_ID = "166"
DEFAULT_FOLDER = "deckshado/myl_cards/aydv_nonsecret_fix_2026_07"
DEFAULT_MAPPING_FILE = Path(__file__).resolve().parents[4] / "aydv_vigilantes_nonsecret_mapping.json"

# Solo versiones no secretas objetivo (ultra/mega) para AYDV Vigilantes.
TARGET_API_SLUGS = [
    "angel_gabriel",
    "angel_jofiel",
    "belcebu",
    "belfegor",
    "caida_del_alba",
    "el_arca",
    "el_gran_descenso",
    "estirpe_maldita",
    "fuego_purificador",
    "gran_diluvio",
    "guerra_celestial",
    "leviathan",
    "lucifer",
    "miguel",
    "rafael",
    "satanas",
    "semyazza",
    "trono_del_cielo",
    "trono_del_dragon",
    "uriel",
    "zadquiel",
]


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

    if "ik.imagekit.io" not in (parsed.netloc or "").lower():
        return None

    path = (parsed.path or "").lstrip("/")
    if not path or "." not in path:
        return None
    return path


class Command(BaseCommand):
    help = "Corrige artes de no-secretas AYDV Vigilantes (secretas+9 legendarias)"

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
            help="ID de edicion para static/cards/<id>/<edid>.png (AYDV=166)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="No guarda cambios en BD",
        )
        parser.add_argument(
            "--progress-every",
            type=int,
            default=1,
            help="Imprime progreso cada N cartas (default: 1)",
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

    def _fetch_api_payload(self) -> dict[str, Any]:
        try:
            resp = requests.get(API_CARDS_ENDPOINT, timeout=45)
            resp.raise_for_status()
            payload = resp.json()
        except requests.RequestException as exc:
            raise CommandError(f"No se pudo descargar API AYDV: {exc}") from exc
        except ValueError as exc:
            raise CommandError("Respuesta invalida desde API AYDV") from exc

        if not isinstance(payload, dict):
            raise CommandError("Payload invalido desde API AYDV")
        return payload

    def _apply_mapping_only(
        self,
        edition: Edition,
        mapping_file: Path,
        dry_run: bool,
        progress_every: int,
    ) -> None:
        if not mapping_file.exists():
            raise CommandError(f"No existe mapping file: {mapping_file}")

        try:
            mapping = json.loads(mapping_file.read_text(encoding="utf-8"))
        except ValueError as exc:
            raise CommandError(f"Mapping JSON invalido: {mapping_file}") from exc

        if not isinstance(mapping, dict):
            raise CommandError("El mapping debe ser un objeto JSON de myl_id -> url")

        total = len(mapping)
        updated = 0
        kept = 0
        missing = 0

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"Aplicando mapping AYDV no-secretas ({total} entradas, cada {progress_every})..."
            )
        )

        for idx, (myl_id, image_url) in enumerate(mapping.items(), start=1):
            card = Card.objects.filter(edition=edition, myl_id=str(myl_id)).first()
            if not card:
                missing += 1
            else:
                image_url = str(image_url or "").strip()
                if image_url:
                    if card.custom_image_url == image_url:
                        kept += 1
                    else:
                        if not dry_run:
                            card.custom_image_url = image_url
                            card.save(update_fields=["custom_image_url"])
                        updated += 1

            if idx % progress_every == 0 or idx == total:
                pct = (idx / total) * 100 if total else 100
                self.stdout.write(
                    f"[apply {idx}/{total} {pct:.1f}%] Updated={updated} Kept={kept} Missing={missing}"
                )

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
        progress_every = max(1, int(options.get("progress_every") or 1))

        edition = Edition.objects.filter(slug="aydv").first()
        if not edition:
            raise CommandError("No existe la edicion 'aydv' en la base de datos")

        if apply_mapping_only:
            self._apply_mapping_only(
                edition=edition,
                mapping_file=mapping_file,
                dry_run=dry_run,
                progress_every=progress_every,
            )
            return

        cdn_uploader = self._ensure_repo_imports()
        os.environ["CDN_PROVIDER"] = "imagekit"

        payload = self._fetch_api_payload()
        api_cards = payload.get("cards", []) or []
        rarity_payload = payload.get("rarities", []) or []
        if not isinstance(api_cards, list):
            raise CommandError("Payload de API AYDV sin lista de cards")

        rarity_by_id = {
            str(item.get("id")): str(item.get("slug") or "").strip().lower()
            for item in rarity_payload
            if isinstance(item, dict)
        }

        api_by_slug: dict[str, dict[str, Any]] = {}
        for raw in api_cards:
            if not isinstance(raw, dict):
                continue
            slug = str(raw.get("slug") or "").strip()
            if slug:
                api_by_slug[slug] = raw

        targets: list[dict[str, Any]] = []
        missing_api: list[str] = []
        for slug in TARGET_API_SLUGS:
            raw = api_by_slug.get(slug)
            if raw is None:
                missing_api.append(slug)
                continue

            rarity_slug = rarity_by_id.get(str(raw.get("rarity")), "")
            if rarity_slug not in {"ultra-real", "mega-real"}:
                missing_api.append(slug)
                continue

            api_edid = _safe_api_edid(raw.get("edid"))
            if not api_edid:
                missing_api.append(slug)
                continue

            targets.append(
                {
                    "api_slug": slug,
                    "name_key": _norm(str(raw.get("name") or "")),
                    "slug_key": _norm(slug.replace("_", " ")),
                    "rarity_slug": rarity_slug,
                    "api_edid": api_edid,
                    "api_name": str(raw.get("name") or slug),
                }
            )

        if missing_api:
            self.stdout.write(self.style.WARNING(f"API missing/invalid slugs: {', '.join(sorted(missing_api))}"))

        if not targets:
            raise CommandError("No se pudieron resolver objetivos desde API AYDV")

        cards = list(Card.objects.filter(edition=edition).select_related("rarity").order_by("id"))

        by_key: dict[tuple[str, str], list[Card]] = {}
        for card in cards:
            rarity_slug = str(getattr(getattr(card, "rarity", None), "slug", "") or "").strip().lower()
            key = (_norm(card.name), rarity_slug)
            by_key.setdefault(key, []).append(card)

        selected: list[tuple[dict[str, Any], Card]] = []
        missing_local: list[str] = []
        used_ids: set[int] = set()

        for target in targets:
            primary_key = (target["name_key"], target["rarity_slug"])
            fallback_key = (target["slug_key"], target["rarity_slug"])
            candidates = by_key.get(primary_key, [])
            if not candidates and fallback_key != primary_key:
                candidates = by_key.get(fallback_key, [])
            if not candidates:
                missing_local.append(f"{target['api_slug']} ({target['rarity_slug']})")
                continue

            pick: Card | None = None
            for c in candidates:
                if c.id in used_ids:
                    continue
                local_edid = _extract_api_edid_candidate(c.edid)
                if local_edid and local_edid == target["api_edid"]:
                    pick = c
                    break

            if pick is None:
                for c in candidates:
                    if c.id not in used_ids:
                        pick = c
                        break

            if pick is None:
                missing_local.append(f"{target['api_slug']} ({target['rarity_slug']})")
                continue

            used_ids.add(pick.id)
            selected.append((target, pick))

        if missing_local:
            self.stdout.write(self.style.WARNING(f"Local missing targets: {', '.join(sorted(missing_local))}"))

        total = len(selected)
        if total == 0:
            raise CommandError("No hay cartas locales para corregir en AYDV")

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"AYDV Vigilantes no-secretas: corrigiendo {total} cartas especificas (no 293)"
            )
        )

        uploaded = 0
        failed_download = 0
        failed_upload = 0
        unchanged = 0

        mapping: dict[str, str] = {}
        if mapping_file.exists():
            try:
                existing = json.loads(mapping_file.read_text(encoding="utf-8"))
                if isinstance(existing, dict):
                    mapping = {str(k): str(v) for k, v in existing.items()}
            except ValueError:
                mapping = {}

        for idx, (target, card) in enumerate(selected, start=1):
            source_url = f"{API_CDN_BASE}/{api_edition_id}/{target['api_edid']}.png"
            label = f"{card.edid} {card.name} [{target['rarity_slug']}]"

            try:
                resp = requests.get(source_url, timeout=45)
                resp.raise_for_status()
            except requests.RequestException as exc:
                failed_download += 1
                self.stdout.write(self.style.WARNING(f"[{idx}/{total}] FAIL download {label} -> {exc}"))
                continue

            content = resp.content
            if not content:
                failed_download += 1
                self.stdout.write(self.style.WARNING(f"[{idx}/{total}] FAIL empty {label}"))
                continue

            shared_with_secret = False
            if (card.custom_image_url or "").strip():
                shared_with_secret = Card.objects.filter(
                    edition=edition,
                    rarity__slug="secreta",
                    custom_image_url=card.custom_image_url,
                ).exists()

            public_id = _extract_imagekit_public_id(card.custom_image_url)
            if not public_id or shared_with_secret:
                safe_name = _slugify(card.name)
                safe_myl_id = _slugify(str(card.myl_id or f"card-{card.id}"))
                public_id = (
                    f"{folder}/fixed_{target['api_edid']}_{safe_name}_{target['rarity_slug']}_{safe_myl_id}.png"
                )
                if shared_with_secret:
                    self.stdout.write(
                        self.style.WARNING(
                            f"[{idx}/{total}] INFO decouple secret URL -> {label}"
                        )
                    )

            if dry_run:
                fake_url = card.custom_image_url or f"https://ik.imagekit.io/<cloud>/{public_id}"
                if card.custom_image_url == fake_url:
                    unchanged += 1
                else:
                    uploaded += 1
                if card.myl_id:
                    mapping[str(card.myl_id)] = fake_url
                pct = (idx / total) * 100
                self.stdout.write(f"[{idx}/{total} {pct:.1f}%] DRY {label}")
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
                self.stdout.write(self.style.WARNING(f"[{idx}/{total}] FAIL upload {label} -> {exc}"))
                continue

            if card.custom_image_url == image_url:
                unchanged += 1
            else:
                card.custom_image_url = image_url
                card.save(update_fields=["custom_image_url"])
                uploaded += 1

            if card.myl_id:
                mapping[str(card.myl_id)] = image_url

            pct = (idx / total) * 100
            self.stdout.write(f"[{idx}/{total} {pct:.1f}%] OK {label}")

            if idx % progress_every == 0 or idx == total:
                self.stdout.write(
                    f"[progress {idx}/{total}] Uploaded={uploaded} Unchanged={unchanged} "
                    f"FailedDownload={failed_download} FailedUpload={failed_upload}"
                )

        mapping_file.parent.mkdir(parents=True, exist_ok=True)
        mapping_file.write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")

        self.stdout.write(
            self.style.SUCCESS(
                "Done. "
                f"Targets={total} | Uploaded={uploaded} | Unchanged={unchanged} | "
                f"FailedDownload={failed_download} | FailedUpload={failed_upload}"
            )
        )
        self.stdout.write(f"Mapping: {mapping_file}")
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN: no se guardaron cambios en BD."))
