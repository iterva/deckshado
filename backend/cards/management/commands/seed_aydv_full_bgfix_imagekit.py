from __future__ import annotations

import json
import re
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from django.core.management.base import BaseCommand, CommandError

from cards.models import Card

ROOT_DIR = Path(__file__).resolve().parents[4]
DEFAULT_MAPPING_FILE = ROOT_DIR / "aydv_full_bgfix_imagekit_mapping.json"
DEFAULT_ENV_FILE = ROOT_DIR.parent / ".env_imagekit"
DEFAULT_FOLDER = "/deckshado/myl_cards/aydv_full_bgfix_2026_07"
ACTIVE_CLOUDINARY = "daobfx9yb"
LEGACY_CLOUDINARY = ("drw7y27sm", "dmvu6tuee")


@dataclass
class ImageKitConfig:
    private_key: str
    url_endpoint: str


def _load_simple_env(path: Path) -> dict[str, str]:
    if not path.exists():
        raise CommandError(f"No existe env file: {path}")

    out: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        out[key.strip()] = value.strip().strip('"').strip("'")
    return out


def _resolve_imagekit_config(env_file: Path) -> ImageKitConfig:
    env = _load_simple_env(env_file)

    private_key = (env.get("private_key") or env.get("IMAGEKIT_PRIVATE_KEY") or "").strip()
    url_endpoint = (env.get("url") or env.get("IMAGEKIT_URL_ENDPOINT") or "").strip().rstrip("/")

    if not private_key:
        raise CommandError("Falta private_key/IMAGEKIT_PRIVATE_KEY en env file")
    if not url_endpoint:
        raise CommandError("Falta url/IMAGEKIT_URL_ENDPOINT en env file")

    return ImageKitConfig(private_key=private_key, url_endpoint=url_endpoint)


def _sanitize_part(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "-", value or "")
    cleaned = re.sub(r"-+", "-", cleaned).strip("-")
    return cleaned or "file"


def _detect_ext_from_url(url: str) -> str:
    try:
        path = urlparse(url).path.lower()
    except Exception:
        path = (url or "").lower()

    for ext in ("jpg", "jpeg", "png", "webp"):
        if f".{ext}" in path:
            return ext
    return "jpg"


def _mime_for_ext(ext: str) -> str:
    ext = (ext or "").lower()
    if ext in {"jpg", "jpeg"}:
        return "image/jpeg"
    if ext == "png":
        return "image/png"
    if ext == "webp":
        return "image/webp"
    return "application/octet-stream"


def _rewrite_cloudinary_host(url: str, cloud_name: str) -> str:
    if not isinstance(url, str) or not url:
        return url
    return re.sub(
        r"res\.cloudinary\.com/[^/]+",
        f"res.cloudinary.com/{cloud_name}",
        url,
        count=1,
        flags=re.IGNORECASE,
    )


def _candidate_source_urls(url: str) -> list[str]:
    out: list[str] = []
    if not url:
        return out

    out.append(url)
    lower = url.lower()
    if "res.cloudinary.com/" in lower:
        out.append(_rewrite_cloudinary_host(url, ACTIVE_CLOUDINARY))
        for legacy in LEGACY_CLOUDINARY:
            out.append(_rewrite_cloudinary_host(url, legacy))

    # Keep order but deduplicate exact repeats.
    dedup: list[str] = []
    seen = set()
    for item in out:
        if item in seen:
            continue
        seen.add(item)
        dedup.append(item)
    return dedup


def _download_image_bytes(source_url: str) -> tuple[bytes, str]:
    last_exc: Exception | None = None
    for candidate in _candidate_source_urls(source_url):
        try:
            r = requests.get(candidate, timeout=180)
            r.raise_for_status()
            return r.content, candidate
        except Exception as exc:
            last_exc = exc
            continue

    if last_exc:
        raise last_exc
    raise RuntimeError("No se pudo descargar la imagen")


def _edge_connected(mask: Any) -> Any:
    import numpy as np

    h, w = mask.shape
    bg = np.zeros((h, w), dtype=bool)
    q: deque[tuple[int, int]] = deque()

    for x in range(w):
        if mask[0, x] and not bg[0, x]:
            bg[0, x] = True
            q.append((0, x))
        if mask[h - 1, x] and not bg[h - 1, x]:
            bg[h - 1, x] = True
            q.append((h - 1, x))

    for y in range(h):
        if mask[y, 0] and not bg[y, 0]:
            bg[y, 0] = True
            q.append((y, 0))
        if mask[y, w - 1] and not bg[y, w - 1]:
            bg[y, w - 1] = True
            q.append((y, w - 1))

    while q:
        y, x = q.popleft()
        if y > 0 and mask[y - 1, x] and not bg[y - 1, x]:
            bg[y - 1, x] = True
            q.append((y - 1, x))
        if y + 1 < h and mask[y + 1, x] and not bg[y + 1, x]:
            bg[y + 1, x] = True
            q.append((y + 1, x))
        if x > 0 and mask[y, x - 1] and not bg[y, x - 1]:
            bg[y, x - 1] = True
            q.append((y, x - 1))
        if x + 1 < w and mask[y, x + 1] and not bg[y, x + 1]:
            bg[y, x + 1] = True
            q.append((y, x + 1))

    return bg


def _crop_background(image_bytes: bytes) -> tuple[bytes, tuple[int, int], tuple[int, int], tuple[int, int, int, int]]:
    import numpy as np
    from PIL import Image

    img = Image.open(BytesIO(image_bytes)).convert("RGB")
    before = img.size
    rgb = np.array(img, dtype=np.uint8)

    maxc = rgb.max(axis=2).astype("int16")
    minc = rgb.min(axis=2).astype("int16")
    sat = maxc - minc
    val = maxc

    candidate_bg = (sat <= 58) & (val >= 100)
    bg = _edge_connected(candidate_bg)
    fg = ~bg

    ys, xs = np.where(fg)
    if ys.size == 0 or xs.size == 0:
        box = (0, 0, before[0], before[1])
        after = before
        out = BytesIO()
        img.save(out, format="JPEG", quality=95, optimize=True)
        return out.getvalue(), before, after, box

    x0 = int(xs.min())
    x1 = int(xs.max()) + 1
    y0 = int(ys.min())
    y1 = int(ys.max()) + 1
    box = (x0, y0, x1, y1)

    cropped = img.crop(box)
    after = cropped.size
    out = BytesIO()
    cropped.save(out, format="JPEG", quality=95, optimize=True)
    return out.getvalue(), before, after, box


def _upload_imagekit(config: ImageKitConfig, folder: str, file_name: str, content: bytes, mime_type: str) -> str:
    resp = requests.post(
        "https://upload.imagekit.io/api/v1/files/upload",
        auth=(config.private_key, ""),
        data={
            "fileName": file_name,
            "folder": folder,
            "useUniqueFileName": "false",
            "overwriteFile": "true",
        },
        files={
            "file": (file_name, content, mime_type),
        },
        timeout=180,
    )

    if resp.status_code >= 300:
        raise RuntimeError(f"ImageKit upload failed ({resp.status_code}): {resp.text[:300]}")

    body = resp.json()
    url = body.get("url")
    if not url:
        raise RuntimeError("ImageKit upload ok pero sin url")
    return url


class Command(BaseCommand):
    help = "Recorta fondo claro conectado al borde en cartas AYDV* y sube resultado a ImageKit"

    def add_arguments(self, parser):
        parser.add_argument("--slug-prefix", default="aydv", help="Prefijo de edición a procesar (default: aydv)")
        parser.add_argument("--folder", default=DEFAULT_FOLDER, help="Folder destino en ImageKit")
        parser.add_argument("--mapping-file", default=str(DEFAULT_MAPPING_FILE), help="JSON mapping de salida/entrada")
        parser.add_argument("--env-file", default=str(DEFAULT_ENV_FILE), help="Env con private_key/url de ImageKit")
        parser.add_argument("--limit", type=int, default=0, help="Limita cantidad de cartas (debug)")
        parser.add_argument("--dry-run", action="store_true", help="No guarda DB ni sube a ImageKit")
        parser.add_argument("--apply-mapping-only", action="store_true", help="Solo aplica mapping JSON a custom_image_url")

    def handle(self, *args, **options):
        mapping_file = Path(options["mapping_file"]).resolve()

        if options["apply_mapping_only"]:
            self._apply_mapping_only(mapping_file=mapping_file, dry_run=bool(options["dry_run"]))
            return

        env_file = Path(options["env_file"]).resolve()
        config = _resolve_imagekit_config(env_file)

        slug_prefix = str(options["slug_prefix"]).strip().lower()
        folder = str(options["folder"]).strip() or DEFAULT_FOLDER
        limit = int(options["limit"] or 0)
        dry_run = bool(options["dry_run"])

        qs = (
            Card.objects
            .select_related("edition")
            .filter(edition__slug__startswith=slug_prefix)
            .exclude(custom_image_url__isnull=True)
            .exclude(custom_image_url="")
            .order_by("edition__slug", "edid", "id")
        )

        if limit > 0:
            qs = qs[:limit]

        cards = list(qs)
        if not cards:
            raise CommandError("No se encontraron cartas para procesar")

        self.stdout.write(self.style.MIGRATE_HEADING(f"Procesando {len(cards)} cartas ({slug_prefix}*)"))

        records: list[dict[str, Any]] = []
        ok = 0
        fail = 0

        for idx, card in enumerate(cards, 1):
            source_url = (card.custom_image_url or "").strip()
            rec: dict[str, Any] = {
                "card_id": card.id,
                "myl_id": card.myl_id,
                "edid": card.edid,
                "name": card.name,
                "edition_slug": card.edition.slug,
                "source_url": source_url,
                "status": "pending",
            }
            try:
                source_bytes, fetched_from = _download_image_bytes(source_url)
                rec["fetched_from"] = fetched_from

                cropped_bytes, before, after, box = _crop_background(source_bytes)
                rec["size_before"] = [before[0], before[1]]
                rec["size_after"] = [after[0], after[1]]
                rec["crop_box"] = [box[0], box[1], box[2], box[3]]

                ext = _detect_ext_from_url(source_url)
                file_name = f"{_sanitize_part(card.myl_id)}_{_sanitize_part(card.edid)}.{ext}"

                if dry_run:
                    new_url = f"{config.url_endpoint}{folder.rstrip('/')}/{file_name}"
                else:
                    new_url = _upload_imagekit(
                        config=config,
                        folder=folder,
                        file_name=file_name,
                        content=cropped_bytes,
                        mime_type=_mime_for_ext(ext),
                    )
                    if card.custom_image_url != new_url:
                        card.custom_image_url = new_url
                        card.save(update_fields=["custom_image_url"])

                rec["imagekit_url"] = new_url
                rec["status"] = "ok"
                ok += 1
            except Exception as exc:
                rec["status"] = "error"
                rec["error"] = str(exc)
                fail += 1

            records.append(rec)
            self.stdout.write(f"[{idx}/{len(cards)}] {card.edid} {card.name}: {rec['status']}")

        payload = {
            "kind": "aydv_full_bgfix_imagekit",
            "slug_prefix": slug_prefix,
            "folder": folder,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "dry_run": dry_run,
            "records": records,
        }

        mapping_file.parent.mkdir(parents=True, exist_ok=True)
        mapping_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS(f"OK={ok} FAIL={fail}"))
        self.stdout.write(self.style.SUCCESS(f"Mapping guardado en: {mapping_file}"))

        if fail > 0 and not dry_run:
            raise CommandError(f"Finalizado con errores: {fail}")

    def _apply_mapping_only(self, mapping_file: Path, dry_run: bool):
        if not mapping_file.exists():
            raise CommandError(f"No existe mapping file: {mapping_file}")

        body = json.loads(mapping_file.read_text(encoding="utf-8"))
        records = body.get("records", [])
        if not records:
            raise CommandError("Mapping sin records")

        updated = 0
        missing = 0
        skipped = 0

        for rec in records:
            if rec.get("status") != "ok":
                skipped += 1
                continue

            myl_id = rec.get("myl_id")
            edid = rec.get("edid")
            new_url = rec.get("imagekit_url")
            if not myl_id or not edid or not new_url:
                skipped += 1
                continue

            card = Card.objects.filter(myl_id=myl_id, edid=edid).first()
            if not card:
                missing += 1
                continue

            if card.custom_image_url == new_url:
                skipped += 1
                continue

            if not dry_run:
                card.custom_image_url = new_url
                card.save(update_fields=["custom_image_url"])
            updated += 1

        self.stdout.write(self.style.SUCCESS(f"apply-mapping updated={updated} missing={missing} skipped={skipped}"))
