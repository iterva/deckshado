import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import html
import io
import re
import zipfile
from functools import wraps
from urllib.parse import urlparse

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.text import slugify
from django.views.decorators.http import require_http_methods

from cards.admin_tools import host_from_url, upload_image_bytes_to_imagekit, upload_image_url_to_imagekit
from cards.forms import SessionImagekitEnvForm, default_allowed_image_hosts, parse_session_env

from .forms_admin import (
    BulkRiftboundCardCsvForm,
    BulkRiftboundSetCsvForm,
    RiftboundBanlistEntryForm,
    RiftboundCardForm,
    RiftboundSetForm,
    SourceRiftboundGalleryForm,
    csv_rows,
    upsert_card_row,
    upsert_set_row,
)
from .models import RiftboundBanlistEntry, RiftboundCard, RiftboundFormat, RiftboundSet


SESSION_KEY_IMAGEKIT = "cards_admin_imagekit_session"
SESSION_KEY_RIFTBOUND_SOURCE_PREPARED = "riftbound_admin_source_prepared"
SESSION_KEY_RIFTBOUND_UPLOAD_RESULT = "riftbound_admin_upload_result"

RIFTBOUND_GALLERY_HOSTS = {"playriftbound.com", "www.playriftbound.com", "riftbound.leagueoflegends.com"}
RIFTBOUND_IMAGE_HOSTS = {"cmsassets.rgpub.io"}
_IMG_TAG_RE = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
_NEXT_DATA_RE = re.compile(
    r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
    flags=re.IGNORECASE | re.DOTALL,
)
_RAW_CMS_URL_RE = re.compile(r'https?:\\?/\\?/cmsassets\.rgpub\.io[^"\'\s<>]+', flags=re.IGNORECASE)


def _safe_download_name(raw: str, fallback: str = "card.png") -> str:
    value = (raw or "").strip() or fallback
    base, dot, ext = value.rpartition(".")
    if not dot:
        base = value
        ext = ""
    safe_base = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in base).strip("_")
    safe_base = safe_base[:160] or "card"
    safe_ext = "".join(ch for ch in ext.lower() if ch.isalnum())[:8]
    return f"{safe_base}.{safe_ext}" if safe_ext else safe_base


def _normalize_image_url(url: str) -> str:
    return (url or "").split("?", 1)[0].strip()


def _extract_attr(tag: str, attr: str) -> str:
    match = re.search(rf"\b{attr}\s*=\s*(?:\"([^\"]*)\"|'([^']*)')", tag, flags=re.IGNORECASE)
    if not match:
        return ""
    return match.group(1) or match.group(2) or ""


def _riftbound_name_from_alt(alt_text: str, fallback: str) -> str:
    text = html.unescape(alt_text or "").strip()
    if ":" in text:
        text = text.split(":", 1)[1].strip()
    if "." in text:
        text = text.split(".", 1)[0].strip()
    text = re.sub(r"\s+", " ", text).strip(" -")
    return text or fallback


def _guess_card_number(image_url: str, set_code: str, index: int) -> str:
    image_name = (urlparse(image_url).path.rsplit("/", 1)[-1] or "").strip()
    stem = image_name.rsplit(".", 1)[0] if "." in image_name else image_name
    candidate = re.sub(r"[^A-Za-z0-9-]", "", stem).upper()
    if 3 <= len(candidate) <= 20 and any(ch.isdigit() for ch in candidate):
        return candidate
    return f"{set_code}-{index:03d}"[:20]


def _extract_numeric_text(value) -> str:
    if isinstance(value, dict):
        raw = value.get("id")
        if raw in (None, ""):
            raw = value.get("label")
    else:
        raw = value
    text = str(raw or "").strip()
    if not text:
        return ""
    return text if re.fullmatch(r"-?\d+", text) else ""


def _html_to_plain_text(text_html: str) -> str:
    text = html.unescape(text_html or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _extract_cards_items_from_next_data(root) -> list[dict]:
    candidate_lists: list[list[dict]] = []

    def _walk(node):
        if isinstance(node, dict):
            cards = node.get("cards")
            if isinstance(cards, dict):
                items = cards.get("items")
                if isinstance(items, list) and items and isinstance(items[0], dict):
                    candidate_lists.append(items)
            for value in node.values():
                _walk(value)
        elif isinstance(node, list):
            for value in node:
                _walk(value)

    _walk(root)
    if not candidate_lists:
        return []
    return max(candidate_lists, key=len)


def _collect_cards_from_next_data_html(
    html_text: str,
    max_cards: int,
    fallback_set_code: str,
    set_filter: str = "",
) -> list[dict[str, str]]:
    match = _NEXT_DATA_RE.search(html_text or "")
    if not match:
        return []

    try:
        payload = json.loads(match.group(1))
    except Exception:
        return []

    items = _extract_cards_items_from_next_data(payload)
    if not items:
        return []

    type_allowed = {"champion", "legend", "unit", "spell", "gear", "battlefield", "rune", "other"}
    rarity_allowed = {"common", "uncommon", "rare", "epic", "legendary", "champion", "promo", "other"}

    rows: list[dict[str, str]] = []
    seen_urls: set[str] = set()
    seen_numbers: set[str] = set()

    for item in items:
        if not isinstance(item, dict):
            continue

        card_image = item.get("cardImage") or {}
        image_url_raw = str(card_image.get("url") or "").strip()
        image_url = _normalize_image_url(image_url_raw.replace("\\/", "/"))
        parsed = urlparse(image_url)
        if parsed.netloc.lower() not in RIFTBOUND_IMAGE_HOSTS:
            continue
        if image_url in seen_urls:
            continue
        seen_urls.add(image_url)

        name = str(item.get("name") or "").strip()
        if not name:
            name = _riftbound_name_from_alt(str(card_image.get("accessibilityText") or ""), f"Riftbound {len(rows) + 1}")

        public_code = str(item.get("publicCode") or "").strip()
        card_number_match = re.search(r"([A-Za-z0-9]+-\d+[A-Za-z]?)", public_code)
        if card_number_match:
            card_number = card_number_match.group(1).upper()
        else:
            collector = item.get("collectorNumber")
            collector_text = _extract_numeric_text(collector)
            if collector_text:
                card_number = f"{fallback_set_code}-{int(collector_text):03d}"
            else:
                card_number = _guess_card_number(image_url, set_code=fallback_set_code, index=len(rows) + 1)

        if card_number in seen_numbers:
            card_number = _guess_card_number(image_url, set_code=fallback_set_code, index=len(rows) + 1)
        seen_numbers.add(card_number)

        set_value = item.get("set") or {}
        set_data = set_value.get("value") if isinstance(set_value, dict) else {}
        set_id = str((set_data or {}).get("id") or "").strip().upper()
        set_code = set_id or fallback_set_code

        if set_filter and set_code != set_filter:
            continue

        type_data = item.get("cardType") or {}
        type_list = type_data.get("type") if isinstance(type_data, dict) else None
        type_id = "unit"
        if isinstance(type_list, list) and type_list:
            type_id = str((type_list[0] or {}).get("id") or "unit").strip().lower()
        if type_id not in type_allowed:
            type_id = "unit"

        rarity_data = item.get("rarity") or {}
        rarity_value = rarity_data.get("value") if isinstance(rarity_data, dict) else {}
        rarity_id = str((rarity_value or {}).get("id") or "common").strip().lower()
        if rarity_id not in rarity_allowed:
            rarity_id = "other"

        text_data = item.get("text") or {}
        rich_text = text_data.get("richText") if isinstance(text_data, dict) else {}
        body_html = str((rich_text or {}).get("body") or "")
        description = _html_to_plain_text(body_html)

        energy = _extract_numeric_text((item.get("energy") or {}).get("value") if isinstance(item.get("energy"), dict) else item.get("energy"))
        power = _extract_numeric_text((item.get("power") or {}).get("value") if isinstance(item.get("power"), dict) else item.get("power"))
        might = _extract_numeric_text((item.get("might") or {}).get("value") if isinstance(item.get("might"), dict) else item.get("might"))

        image_name = (parsed.path.rsplit("/", 1)[-1] or "card.png").strip()
        ext = ".png"
        if "." in image_name:
            maybe_ext = "." + image_name.rsplit(".", 1)[-1].lower()
            if re.fullmatch(r"\.[a-z0-9]{2,5}", maybe_ext):
                ext = maybe_ext
        slug_name = slugify(name) or f"riftbound_{len(rows) + 1:03d}"

        rows.append(
            {
                "card_number": card_number,
                "name": name,
                "set_code": set_code,
                "slug": slug_name,
                "card_type": type_id,
                "rarity": rarity_id,
                "energy": energy,
                "power": power,
                "might": might,
                "description": description,
                "flavor": "",
                "image_url": image_url,
                "cdn_image_url": "",
                "is_active": "1",
                "file_name": _safe_download_name(f"{card_number}_{slug_name}{ext}"),
            }
        )

        if len(rows) >= max_cards:
            break

    return rows


def _iter_fallback_image_urls(html_text: str):
    # 1) Intentar atributos de etiquetas img por compatibilidad con fuentes estáticas.
    for tag in _IMG_TAG_RE.findall(html_text):
        for attr in ("src", "data-src", "srcset", "data-srcset"):
            raw = _extract_attr(tag, attr)
            if not raw:
                continue
            first = raw.split(",", 1)[0].strip().split(" ", 1)[0]
            decoded = html.unescape(first).replace("\\/", "/")
            if decoded:
                yield decoded

    # 2) Fallback para páginas SPA/SSR: URLs embebidas en JSON/script.
    for match in _RAW_CMS_URL_RE.finditer(html_text or ""):
        decoded = html.unescape(match.group(0)).replace("\\/", "/")
        if decoded:
            yield decoded


def _is_likely_card_image(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.netloc.lower() not in RIFTBOUND_IMAGE_HOSTS:
        return False
    path = parsed.path or ""
    if "/game_data_live/" not in path:
        return False
    if not re.search(r"\.(png|jpe?g|webp)$", path, flags=re.IGNORECASE):
        return False
    dim = re.search(r"-(\d{2,4})x(\d{2,4})\.[a-z0-9]+$", path, flags=re.IGNORECASE)
    if not dim:
        return False
    width = int(dim.group(1))
    height = int(dim.group(2))
    return height >= width and height >= 900 and width >= 600


def _build_riftbound_bulk_csv_text(rows: list[dict[str, str]]) -> str:
    headers = [
        "card_number",
        "name",
        "set_code",
        "slug",
        "card_type",
        "rarity",
        "energy",
        "power",
        "might",
        "description",
        "flavor",
        "image_url",
        "cdn_image_url",
        "is_active",
    ]
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=headers)
    writer.writeheader()
    for row in rows:
        writer.writerow({h: row.get(h, "") for h in headers})
    return buffer.getvalue()


def _build_riftbound_upload_result_csv_text(rows: list[dict[str, str]]) -> str:
    headers = [
        "card_number",
        "name",
        "set_code",
        "slug",
        "card_type",
        "rarity",
        "energy",
        "power",
        "might",
        "description",
        "flavor",
        "image_url",
        "cdn_image_url",
        "is_active",
        "_upload_source",
        "_result",
        "_error",
    ]
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=headers)
    writer.writeheader()
    for row in rows:
        writer.writerow({h: row.get(h, "") for h in headers})
    return buffer.getvalue()


def _collect_cards_from_riftbound_gallery_html(html_text: str, max_cards: int, set_code: str) -> list[dict[str, str]]:
    # Camino principal: usa __NEXT_DATA__ cuando existe (incluye nombre y metadatos de carta).
    rows_from_next = _collect_cards_from_next_data_html(
        html_text,
        max_cards=max_cards,
        fallback_set_code=set_code,
        set_filter=set_code if set_code != "RIFT" else "",
    )
    if rows_from_next:
        return rows_from_next

    # Fallback: extracción por URLs embebidas cuando no hay datos estructurados.
    cards: list[dict[str, str]] = []
    seen_urls: set[str] = set()
    seen_numbers: set[str] = set()

    for raw_url in _iter_fallback_image_urls(html_text):
        image_url = _normalize_image_url(raw_url)
        parsed = urlparse(image_url)
        if parsed.scheme not in {"http", "https"}:
            continue
        if not _is_likely_card_image(image_url):
            continue
        if image_url in seen_urls:
            continue
        seen_urls.add(image_url)

        card_idx = len(cards) + 1
        fallback_name = f"Riftbound {card_idx}"
        name = fallback_name

        candidate_number = _guess_card_number(image_url, set_code=set_code, index=card_idx)
        card_number = candidate_number
        if card_number in seen_numbers:
            card_number = f"{set_code}-{card_idx:03d}"[:20]
        seen_numbers.add(card_number)

        image_name = (parsed.path.rsplit("/", 1)[-1] or "card.png").strip()
        ext = ".png"
        if "." in image_name:
            maybe_ext = "." + image_name.rsplit(".", 1)[-1].lower()
            if re.fullmatch(r"\.[a-z0-9]{2,5}", maybe_ext):
                ext = maybe_ext

        slug_name = slugify(name) or f"riftbound_{card_idx:03d}"

        cards.append(
            {
                "card_number": card_number,
                "name": name,
                "set_code": set_code,
                "slug": slug_name,
                "card_type": "unit",
                "rarity": "common",
                "energy": "",
                "power": "",
                "might": "",
                "description": "",
                "flavor": "",
                "image_url": image_url,
                "cdn_image_url": "",
                "is_active": "1",
                "file_name": _safe_download_name(f"{card_number}_{slug_name}{ext}"),
            }
        )

        if len(cards) >= max_cards:
            break

    if not cards:
        raise ValueError("No se encontraron imágenes de cartas en la galería de Riftbound.")
    return cards


def _collect_cards_from_riftbound_gallery(source_url: str, max_cards: int, set_code: str) -> list[dict[str, str]]:
    response = requests.get(source_url, timeout=90)
    response.raise_for_status()
    return _collect_cards_from_riftbound_gallery_html(response.text, max_cards=max_cards, set_code=set_code)


def _build_prepared_source_payload(cleaned: dict) -> dict:
    source_mode = str(cleaned.get("source_mode") or SourceRiftboundGalleryForm.SOURCE_MODE_URL).strip()
    source_url = str(cleaned.get("source_url") or "").strip()
    source_html_file = cleaned.get("source_html_file")
    source_html_text = str(cleaned.get("source_html_text") or "")
    raw_set_code = str(cleaned.get("set_code") or "").strip().upper()
    set_filter = "" if raw_set_code in {"", "TODOS", "TODO", "ALL", "*"} else raw_set_code
    fallback_set_code = set_filter or "RIFT"
    max_cards = int(cleaned.get("max_cards") or 1200)
    generate_bulk_csv = bool(cleaned.get("generate_bulk_csv"))

    # Fallback automático: si el usuario aporta HTML manual, úselo aunque no haya
    # cambiado explícitamente el selector de modo.
    if source_html_file:
        source_mode = SourceRiftboundGalleryForm.SOURCE_MODE_HTML_FILE
    elif source_html_text.strip():
        source_mode = SourceRiftboundGalleryForm.SOURCE_MODE_HTML_TEXT

    if source_mode == SourceRiftboundGalleryForm.SOURCE_MODE_URL:
        parsed = urlparse(source_url)
        host = parsed.netloc.lower().strip()
        path = (parsed.path or "").lower()
        if host not in RIFTBOUND_GALLERY_HOSTS or "/card-gallery" not in path:
            raise ValueError("La URL no corresponde a una galería de Riftbound soportada.")
        rows = _collect_cards_from_riftbound_gallery(source_url, max_cards=max_cards, set_code=fallback_set_code)
    elif source_mode == SourceRiftboundGalleryForm.SOURCE_MODE_HTML_FILE:
        uploaded = source_html_file
        if not uploaded:
            raise ValueError("Debe subir un archivo HTML.")
        html_text = uploaded.read().decode("utf-8", errors="replace")
        rows = _collect_cards_from_riftbound_gallery_html(html_text, max_cards=max_cards, set_code=fallback_set_code)
    elif source_mode == SourceRiftboundGalleryForm.SOURCE_MODE_HTML_TEXT:
        html_text = source_html_text
        rows = _collect_cards_from_riftbound_gallery_html(html_text, max_cards=max_cards, set_code=fallback_set_code)
    else:
        raise ValueError("Modo de fuente no soportado.")

    if set_filter:
        rows = [row for row in rows if str(row.get("set_code") or "").strip().upper() == set_filter]
        if not rows:
            raise ValueError(f"No se encontraron cartas para set_code '{set_filter}'.")

    csv_text = _build_riftbound_bulk_csv_text(rows) if generate_bulk_csv else ""

    cards_for_download = [
        {
            "name": row.get("name", ""),
            "card_number": row.get("card_number", ""),
            "set_code": row.get("set_code", ""),
            "image_url": row.get("image_url", ""),
            "file_name": row.get("file_name", ""),
        }
        for row in rows
    ]

    return {
        "source_mode": source_mode,
        "source_url": source_url,
        "set_code": fallback_set_code,
        "set_code_filter": set_filter,
        "cards": cards_for_download,
        "csv_text": csv_text,
        "generate_bulk_csv": generate_bulk_csv,
    }


def _prepared_source_from_session(request) -> dict:
    payload = request.session.get(SESSION_KEY_RIFTBOUND_SOURCE_PREPARED) or {}
    cards = payload.get("cards")
    if not isinstance(cards, list):
        return {}
    return payload


def _upload_result_from_session(request) -> dict:
    payload = request.session.get(SESSION_KEY_RIFTBOUND_UPLOAD_RESULT) or {}
    csv_text = payload.get("csv_text") or ""
    if not csv_text:
        return {}
    return payload


def _download_prepared_csv(request):
    payload = _prepared_source_from_session(request)
    csv_text = payload.get("csv_text") or ""
    if not csv_text:
        return HttpResponseBadRequest("No hay CSV preparado para descarga.")

    set_code = str(payload.get("set_code_filter") or "ALL").strip().upper()
    response = HttpResponse(csv_text, content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="riftbound_bulk_cards_{set_code}.csv"'
    return response


def _download_upload_result_csv(request):
    payload = _upload_result_from_session(request)
    csv_text = payload.get("csv_text") or ""
    if not csv_text:
        return HttpResponseBadRequest("No hay CSV resultado para descarga.")

    set_code = str(payload.get("set_code") or "RIFT").strip().upper()
    response = HttpResponse(csv_text, content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="riftbound_bulk_cards_result_{set_code}.csv"'
    return response


def _download_prepared_image(request):
    payload = _prepared_source_from_session(request)
    cards = payload.get("cards") or []
    raw_index = (request.GET.get("i") or "").strip()
    if not raw_index.isdigit():
        return HttpResponseBadRequest("Índice de imagen inválido.")

    index = int(raw_index)
    if index < 0 or index >= len(cards):
        return HttpResponseBadRequest("Índice de imagen fuera de rango.")

    item = cards[index]
    image_url = str(item.get("image_url") or "").strip()
    parsed = urlparse(image_url)
    if parsed.netloc.lower() not in RIFTBOUND_IMAGE_HOSTS:
        return HttpResponseBadRequest("Host de imagen no permitido.")

    try:
        response = requests.get(image_url, timeout=90)
        response.raise_for_status()
    except Exception as exc:
        return HttpResponseBadRequest(f"No se pudo descargar la imagen remota: {exc}")

    content_type = (response.headers.get("Content-Type") or "application/octet-stream").split(";", 1)[0].strip()
    if not content_type.startswith("image/"):
        content_type = "application/octet-stream"

    file_name = _safe_download_name(item.get("file_name") or "card.png")
    out = HttpResponse(response.content, content_type=content_type)
    out["Content-Disposition"] = f'attachment; filename="{file_name}"'
    return out


def _download_prepared_images_zip(request):
    payload = _prepared_source_from_session(request)
    cards = payload.get("cards") or []
    if not cards:
        return HttpResponseBadRequest("No hay imágenes preparadas para descarga masiva.")

    zip_buffer = io.BytesIO()
    used_names: set[str] = set()
    errors: list[str] = []

    def _fetch_one(idx: int, item: dict):
        image_url = str(item.get("image_url") or "").strip()
        parsed = urlparse(image_url)
        if parsed.netloc.lower() not in RIFTBOUND_IMAGE_HOSTS:
            return idx, None, None, f"{idx}. Host no permitido: {image_url}"

        try:
            # Timeout corto para evitar que una imagen congele toda la descarga.
            response = requests.get(image_url, timeout=(8, 20))
            response.raise_for_status()
        except Exception as exc:
            return idx, None, None, f"{idx}. Error descargando {image_url}: {exc}"

        file_name = _safe_download_name(item.get("file_name") or f"card_{idx}.png")
        return idx, file_name, response.content, ""

    fetched: list[tuple[int, str, bytes]] = []
    max_workers = min(12, max(1, len(cards)))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {
            executor.submit(_fetch_one, idx, item): idx
            for idx, item in enumerate(cards, start=1)
        }

        for future in as_completed(future_map):
            idx, file_name, content, error_text = future.result()
            if error_text:
                errors.append(error_text)
                continue
            if not file_name or content is None:
                errors.append(f"{idx}. Respuesta inválida al descargar imagen")
                continue
            fetched.append((idx, file_name, content))

    with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for idx, file_name, content in sorted(fetched, key=lambda x: x[0]):
            name_root, dot, ext = file_name.rpartition(".")
            if not dot:
                name_root = file_name
                ext = ""

            unique_name = file_name
            sequence = 2
            while unique_name in used_names:
                unique_name = f"{name_root}_{sequence}.{ext}" if ext else f"{name_root}_{sequence}"
                sequence += 1

            used_names.add(unique_name)
            archive.writestr(unique_name, content)

        if errors:
            archive.writestr("_errores_descarga.txt", "\n".join(errors))

    if not used_names:
        return HttpResponseBadRequest("No se pudo descargar ninguna imagen válida para el ZIP.")

    set_code = str(payload.get("set_code_filter") or "ALL").strip().upper()
    zip_buffer.seek(0)
    out = HttpResponse(zip_buffer.getvalue(), content_type="application/zip")
    out["Content-Disposition"] = f'attachment; filename="riftbound_images_{set_code}.zip"'
    return out


def _image_content_type_from_name(file_name: str) -> str:
    lower = (file_name or "").strip().lower()
    if lower.endswith(".png"):
        return "image/png"
    if lower.endswith(".jpg") or lower.endswith(".jpeg"):
        return "image/jpeg"
    if lower.endswith(".webp"):
        return "image/webp"
    return "application/octet-stream"


def _card_number_key(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9-]", "", str(value or "").strip().upper())


def _open_images_zip_index(uploaded_file):
    file_name = str(getattr(uploaded_file, "name", "") or "").strip()
    if file_name and not file_name.lower().endswith(".zip"):
        raise ValueError("Solo se soporta archivo ZIP para carga masiva de imágenes.")

    raw = uploaded_file.read()
    if not raw:
        raise ValueError("El ZIP de imágenes está vacío.")

    zip_buffer = io.BytesIO(raw)
    archive = zipfile.ZipFile(zip_buffer)
    by_card: dict[str, str] = {}
    by_name: dict[str, str] = {}
    valid_ext = (".png", ".jpg", ".jpeg", ".webp")

    for info in archive.infolist():
        if info.is_dir():
            continue
        base_name = info.filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1].strip()
        if not base_name:
            continue
        if not base_name.lower().endswith(valid_ext):
            continue

        by_name.setdefault(base_name.lower(), info.filename)

        stem = base_name.rsplit(".", 1)[0]
        prefix = stem.split("_", 1)[0]
        key = _card_number_key(prefix)
        if key:
            by_card.setdefault(key, info.filename)

    return archive, by_card, by_name


def _find_image_member_for_row(row: dict[str, str], by_card: dict[str, str], by_name: dict[str, str]) -> str:
    card_number = _card_number_key(row.get("card_number", ""))
    if card_number and card_number in by_card:
        return by_card[card_number]

    image_url = str(row.get("image_url") or "").strip()
    if image_url:
        candidate_name = (urlparse(image_url).path.rsplit("/", 1)[-1] or "").strip().lower()
        if candidate_name and candidate_name in by_name:
            return by_name[candidate_name]

    return ""


def _redirect_next_or_default(request, default_view_name: str):
    next_url = (request.POST.get("next") or request.GET.get("next") or "").strip()
    if next_url and url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(next_url)
    return redirect(default_view_name)


def riftbound_admin_owner_required(view_func):
    @staff_member_required
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        owner_username = str(getattr(settings, "CARDS_ADMIN_OWNER_USERNAME", "iterva")).strip().lower()
        current_username = str(getattr(request.user, "username", "")).strip().lower()
        if current_username != owner_username:
            raise PermissionDenied("No autorizado")
        return view_func(request, *args, **kwargs)

    return _wrapped


@riftbound_admin_owner_required
@require_http_methods(["GET", "POST"])
def riftbound_admin_dashboard(request):
    imagekit_form = SessionImagekitEnvForm()

    if request.method == "POST" and request.POST.get("action") == "set_imagekit_session":
        imagekit_form = SessionImagekitEnvForm(request.POST, request.FILES)
        if imagekit_form.is_valid() and imagekit_form.cleaned_data.get("env_file"):
            env_file = imagekit_form.cleaned_data["env_file"]
            try:
                parsed = parse_session_env(env_file.read())
            except Exception as exc:
                messages.error(request, f"No se pudo cargar env de sesión: {exc}")
            else:
                request.session[SESSION_KEY_IMAGEKIT] = {
                    "public_key": parsed.public_key,
                    "private_key": parsed.private_key,
                    "url": parsed.url_endpoint,
                }
                messages.success(request, "Archivo env de sesión cargado correctamente para esta sesión.")
                return redirect("riftbound-admin-dashboard")

    if request.method == "POST" and request.POST.get("action") == "clear_imagekit_session":
        request.session.pop(SESSION_KEY_IMAGEKIT, None)
        messages.info(request, "Se eliminó la sesión de ImageKit cargada.")
        return redirect("riftbound-admin-dashboard")

    sets = RiftboundSet.objects.annotate(
        card_total=Count("cards"),
        active_cards=Count("cards", filter=Q(cards__is_active=True)),
    ).order_by("code")

    formats = RiftboundFormat.objects.annotate(entry_total=Count("banlist_entries")).order_by("code")

    return render(
        request,
        "riftbound/admin_dashboard.html",
        {
            "set_count": RiftboundSet.objects.count(),
            "card_count": RiftboundCard.objects.count(),
            "active_card_count": RiftboundCard.objects.filter(is_active=True).count(),
            "banlist_count": RiftboundBanlistEntry.objects.count(),
            "format_count": RiftboundFormat.objects.count(),
            "sets": sets,
            "formats": formats,
            "imagekit_form": imagekit_form,
            "imagekit_session": request.session.get(SESSION_KEY_IMAGEKIT),
        },
    )


@riftbound_admin_owner_required
@require_http_methods(["GET", "POST"])
def riftbound_admin_toggle_sets(request):
    sets_qs = RiftboundSet.objects.annotate(
        card_total=Count("cards"),
        active_cards=Count("cards", filter=Q(cards__is_active=True)),
    ).order_by("code")
    sets = list(sets_qs)

    if request.method == "POST":
        valid_ids = {item.id for item in sets}
        checked_ids: set[int] = set()
        for raw in request.POST.getlist("active_set_ids"):
            try:
                parsed = int(raw)
            except (TypeError, ValueError):
                continue
            if parsed in valid_ids:
                checked_ids.add(parsed)

        unchecked_ids = valid_ids - checked_ids

        sets_to_update: list[RiftboundSet] = []
        for item in sets:
            new_name = (request.POST.get(f"set_name_{item.id}") or "").strip()
            if not new_name:
                messages.error(request, f"El nombre del set {item.code} no puede estar vacío.")
                return redirect("riftbound-admin-toggle-sets")
            if new_name != item.name:
                item.name = new_name
                sets_to_update.append(item)

        renamed = 0
        if sets_to_update:
            RiftboundSet.objects.bulk_update(sets_to_update, ["name"])
            renamed = len(sets_to_update)

        activated_cards = 0
        deactivated_cards = 0
        if checked_ids:
            activated_cards = RiftboundCard.objects.filter(set_id__in=checked_ids).exclude(is_active=True).update(is_active=True)
        if unchecked_ids:
            deactivated_cards = RiftboundCard.objects.filter(set_id__in=unchecked_ids).exclude(is_active=False).update(is_active=False)

        messages.success(
            request,
            (
                f"Actualización completada. Sets renombrados: {renamed}. "
                f"Cartas activadas: {activated_cards}. Cartas desactivadas: {deactivated_cards}."
            ),
        )
        return redirect("riftbound-admin-toggle-sets")

    rows = []
    for item in sets:
        all_active = item.card_total > 0 and item.active_cards == item.card_total
        partially_active = item.card_total > 0 and 0 < item.active_cards < item.card_total
        rows.append(
            {
                "id": item.id,
                "code": item.code,
                "name": item.name,
                "card_total": item.card_total,
                "active_cards": item.active_cards,
                "all_active": all_active,
                "partially_active": partially_active,
            }
        )

    return render(request, "riftbound/admin_toggle_sets.html", {"sets_rows": rows})


@riftbound_admin_owner_required
@require_http_methods(["GET", "POST"])
def riftbound_admin_set_new(request):
    form = RiftboundSetForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Set creado correctamente.")
        return redirect("riftbound-admin-dashboard")
    return render(request, "cards/admin_entity_form.html", {"title": "Nuevo set Riftbound", "form": form})


@riftbound_admin_owner_required
@require_http_methods(["GET", "POST"])
def riftbound_admin_set_edit(request, set_id: int):
    set_obj = get_object_or_404(RiftboundSet, pk=set_id)
    form = RiftboundSetForm(request.POST or None, instance=set_obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Set actualizado correctamente.")
        return redirect("riftbound-admin-dashboard")
    return render(request, "cards/admin_entity_form.html", {"title": f"Editar set: {set_obj.code}", "form": form})


@riftbound_admin_owner_required
@require_http_methods(["GET"])
def riftbound_admin_set_cards(request, set_id: int):
    set_obj = get_object_or_404(RiftboundSet, pk=set_id)
    q = (request.GET.get("q") or "").strip()

    cards_qs = RiftboundCard.objects.filter(set=set_obj).order_by("card_number")
    if q:
        cards_qs = cards_qs.filter(name__icontains=q)

    return render(
        request,
        "riftbound/admin_set_cards.html",
        {
            "set_obj": set_obj,
            "cards": cards_qs[:1000],
            "q": q,
            "total": cards_qs.count(),
        },
    )


@riftbound_admin_owner_required
@require_http_methods(["GET", "POST"])
def riftbound_admin_card_new(request):
    form = RiftboundCardForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Carta Riftbound creada correctamente.")
        return redirect("riftbound-admin-dashboard")
    return render(request, "cards/admin_entity_form.html", {"title": "Nueva carta Riftbound", "form": form})


@riftbound_admin_owner_required
@require_http_methods(["GET", "POST"])
def riftbound_admin_card_edit(request, card_id: int):
    card = get_object_or_404(RiftboundCard, pk=card_id)
    form = RiftboundCardForm(request.POST or None, instance=card)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Carta Riftbound actualizada correctamente.")
        return redirect("riftbound-admin-dashboard")
    return render(request, "cards/admin_entity_form.html", {"title": f"Editar carta: {card.name}", "form": form})


@riftbound_admin_owner_required
@require_http_methods(["GET", "POST"])
def riftbound_admin_banlist_new(request):
    form = RiftboundBanlistEntryForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Entrada de banlist Riftbound creada correctamente.")
        return redirect("riftbound-admin-dashboard")
    return render(request, "cards/admin_entity_form.html", {"title": "Nueva entrada banlist Riftbound", "form": form})


@riftbound_admin_owner_required
@require_http_methods(["GET", "POST"])
def riftbound_admin_banlist_edit(request, entry_id: int):
    entry = get_object_or_404(RiftboundBanlistEntry, pk=entry_id)
    form = RiftboundBanlistEntryForm(request.POST or None, instance=entry)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Entrada de banlist Riftbound actualizada correctamente.")
        return _redirect_next_or_default(request, "riftbound-admin-dashboard")
    return render(request, "cards/admin_entity_form.html", {"title": f"Editar banlist: {entry.card.name}", "form": form})


@riftbound_admin_owner_required
@require_http_methods(["POST"])
def riftbound_admin_banlist_delete(request, entry_id: int):
    entry = get_object_or_404(RiftboundBanlistEntry, pk=entry_id)
    card_name = entry.card.name
    entry.delete()
    messages.success(request, f"Entrada de banlist eliminada: {card_name}.")
    return _redirect_next_or_default(request, "riftbound-admin-search")


@riftbound_admin_owner_required
@require_http_methods(["GET", "POST"])
def riftbound_admin_bulk_sets(request):
    form = BulkRiftboundSetCsvForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        processed = 0
        errors: list[str] = []
        for idx, row in enumerate(csv_rows(form.cleaned_data["csv_file"]), start=2):
            try:
                upsert_set_row(row)
                processed += 1
            except Exception as exc:
                errors.append(f"Línea {idx}: {exc}")

        if errors:
            messages.warning(request, f"Procesadas {processed} filas con {len(errors)} errores.")
            for err in errors[:10]:
                messages.error(request, err)
        else:
            messages.success(request, f"Carga de sets completada: {processed} filas.")

        return redirect("riftbound-admin-bulk-sets")

    return render(request, "riftbound/admin_bulk_sets.html", {"form": form})


@riftbound_admin_owner_required
@require_http_methods(["GET", "POST"])
def riftbound_admin_bulk_cards(request):
    if request.method == "GET":
        download_kind = (request.GET.get("download") or "").strip().lower()
        if download_kind == "csv":
            return _download_prepared_csv(request)
        if download_kind in {"upload_result_csv", "result_csv"}:
            return _download_upload_result_csv(request)
        if download_kind == "image":
            return _download_prepared_image(request)
        if download_kind in {"images_zip", "zip"}:
            return _download_prepared_images_zip(request)

    source_form = SourceRiftboundGalleryForm()
    form = BulkRiftboundCardCsvForm(request.POST or None, request.FILES or None)
    if request.method == "POST":
        action = (request.POST.get("action") or "upload_csv").strip().lower()

        if action == "prepare_source_cards":
            source_form = SourceRiftboundGalleryForm(request.POST, request.FILES)
            if source_form.is_valid():
                try:
                    prepared_payload = _build_prepared_source_payload(source_form.cleaned_data)
                except Exception as exc:
                    exc_text = str(exc)
                    if "ProxyError" in exc_text or "403 Forbidden" in exc_text:
                        messages.error(
                            request,
                            "No se pudo abrir la URL desde el servidor por restricción de proxy. "
                            "Use 'Desde archivo HTML' o 'Pegando HTML' para preparar la fuente.",
                        )
                    else:
                        messages.error(request, f"No se pudo preparar la fuente: {exc}")
                else:
                    request.session[SESSION_KEY_RIFTBOUND_SOURCE_PREPARED] = prepared_payload
                    messages.success(
                        request,
                        f"Fuente preparada correctamente. Cartas detectadas: {len(prepared_payload.get('cards') or [])}",
                    )
                    return redirect("riftbound-admin-bulk-cards")
            else:
                messages.error(request, "Revise los datos de la fuente antes de preparar.")

        elif action == "clear_prepared_source":
            request.session.pop(SESSION_KEY_RIFTBOUND_SOURCE_PREPARED, None)
            messages.info(request, "Se limpió la preparación de fuente.")
            return redirect("riftbound-admin-bulk-cards")

        elif action == "clear_upload_result":
            request.session.pop(SESSION_KEY_RIFTBOUND_UPLOAD_RESULT, None)
            messages.info(request, "Se limpió el CSV resultado de la última carga.")
            return redirect("riftbound-admin-bulk-cards")

        elif action == "upload_csv":
            is_async_upload = request.headers.get("x-requested-with", "").lower() == "xmlhttprequest"

            if not form.is_valid():
                if is_async_upload:
                    return JsonResponse(
                        {
                            "ok": False,
                            "message": "Revise los datos del formulario antes de procesar.",
                            "form_errors": form.errors,
                        },
                        status=400,
                    )
                messages.error(request, "Revise los datos del formulario antes de procesar.")
                return redirect("riftbound-admin-bulk-cards")

            processed = 0
            uploaded_to_imagekit = 0
            uploaded_from_zip = 0
            uploaded_from_url = 0
            created_set_codes: set[str] = set()
            errors: list[str] = []
            result_rows: list[dict[str, str]] = []

            do_upload = form.cleaned_data.get("upload_images_to_imagekit", False)
            auto_create_missing_sets = form.cleaned_data.get("auto_create_missing_sets", True)
            imagekit_folder = form.cleaned_data.get("imagekit_folder", "").strip() or "deckshado/riftbound/cards_admin_bulk"
            images_zip_file = form.cleaned_data.get("images_zip_file")
            session_env = request.session.get(SESSION_KEY_IMAGEKIT) or {}
            set_cache: dict[str, RiftboundSet] = {item.code: item for item in RiftboundSet.objects.only("id", "code", "name")}

            if do_upload and not session_env:
                if is_async_upload:
                    return JsonResponse(
                        {
                            "ok": False,
                            "message": "Debe cargar primero el archivo env de sesión de ImageKit para subir imágenes.",
                        },
                        status=400,
                    )
                messages.error(request, "Debe cargar primero el archivo env de sesión de ImageKit para subir imágenes.")
                return redirect("riftbound-admin-bulk-cards")

            allowed_hosts = default_allowed_image_hosts()
            archive = None
            archive_by_card: dict[str, str] = {}
            archive_by_name: dict[str, str] = {}

            if do_upload and images_zip_file:
                try:
                    archive, archive_by_card, archive_by_name = _open_images_zip_index(images_zip_file)
                except Exception as exc:
                    if is_async_upload:
                        return JsonResponse({"ok": False, "message": f"ZIP de imágenes inválido: {exc}"}, status=400)
                    messages.error(request, f"ZIP de imágenes inválido: {exc}")
                    return redirect("riftbound-admin-bulk-cards")

            try:
                for idx, row in enumerate(csv_rows(form.cleaned_data["csv_file"]), start=2):
                    current_row = dict(row)
                    upload_source = "none"
                    try:
                        current_set_code = (current_row.get("set_code") or "").strip().upper()
                        missing_set_before = bool(
                            auto_create_missing_sets and current_set_code and current_set_code not in set_cache
                        )
                        source_image = (current_row.get("image_url") or current_row.get("cdn_image_url") or "").strip()
                        if do_upload:
                            file_name = current_row.get("card_number", "rb-card")
                            member_name = _find_image_member_for_row(current_row, archive_by_card, archive_by_name) if archive else ""

                            if archive and member_name:
                                image_bytes = archive.read(member_name)
                                ct = _image_content_type_from_name(member_name)
                                uploaded_url = upload_image_bytes_to_imagekit(
                                    file_bytes=image_bytes,
                                    imagekit_private_key=session_env["private_key"],
                                    imagekit_url_endpoint=session_env["url"],
                                    folder=imagekit_folder,
                                    file_name=file_name,
                                    content_type=ct,
                                )
                                current_row["cdn_image_url"] = uploaded_url
                                uploaded_to_imagekit += 1
                                uploaded_from_zip += 1
                                upload_source = "zip"
                            elif source_image:
                                host = host_from_url(source_image)
                                if host not in allowed_hosts:
                                    raise ValueError(f"Host no permitido para subida: {host}")

                                uploaded_url = upload_image_url_to_imagekit(
                                    source_url=source_image,
                                    imagekit_private_key=session_env["private_key"],
                                    imagekit_url_endpoint=session_env["url"],
                                    folder=imagekit_folder,
                                    file_name=file_name,
                                )
                                current_row["cdn_image_url"] = uploaded_url
                                uploaded_to_imagekit += 1
                                uploaded_from_url += 1
                                upload_source = "url"
                            else:
                                raise ValueError("Sin imagen para subir: no se encontró en ZIP ni en image_url/cdn_image_url")

                        upsert_card_row(
                            current_row,
                            auto_create_missing_set=auto_create_missing_sets,
                            set_cache=set_cache,
                        )
                        if missing_set_before and current_set_code in set_cache:
                            created_set_codes.add(current_set_code)
                        processed += 1
                        result_row = dict(current_row)
                        result_row["_upload_source"] = upload_source
                        result_row["_result"] = "ok"
                        result_row["_error"] = ""
                        result_rows.append(result_row)
                    except Exception as exc:
                        errors.append(f"Línea {idx}: {exc}")
                        result_row = dict(current_row)
                        result_row["_upload_source"] = upload_source
                        result_row["_result"] = "error"
                        result_row["_error"] = str(exc)
                        result_rows.append(result_row)
            finally:
                if archive:
                    archive.close()

            if result_rows:
                set_code = str(result_rows[0].get("set_code") or "RIFT").strip().upper()
                request.session[SESSION_KEY_RIFTBOUND_UPLOAD_RESULT] = {
                    "set_code": set_code,
                    "rows_total": len(result_rows),
                    "rows_ok": sum(1 for item in result_rows if item.get("_result") == "ok"),
                    "rows_error": sum(1 for item in result_rows if item.get("_result") == "error"),
                    "uploaded_to_imagekit": uploaded_to_imagekit,
                    "uploaded_from_zip": uploaded_from_zip,
                    "uploaded_from_url": uploaded_from_url,
                    "created_sets": sorted(created_set_codes),
                    "csv_text": _build_riftbound_upload_result_csv_text(result_rows),
                }

            summary_message = (
                f"Cartas procesadas: {processed}, subidas ImageKit: {uploaded_to_imagekit} "
                f"(ZIP: {uploaded_from_zip}, URL: {uploaded_from_url}), sets creados: {len(created_set_codes)}, "
                f"errores: {len(errors)}"
            )

            if is_async_upload:
                status_code = 200
                payload = {
                    "ok": len(errors) == 0,
                    "processed": processed,
                    "uploaded_to_imagekit": uploaded_to_imagekit,
                    "uploaded_from_zip": uploaded_from_zip,
                    "uploaded_from_url": uploaded_from_url,
                    "created_sets_count": len(created_set_codes),
                    "created_sets": sorted(created_set_codes)[:30],
                    "errors_count": len(errors),
                    "errors": errors[:20],
                    "message": summary_message,
                    "download_result_csv_url": "?download=upload_result_csv",
                }
                return JsonResponse(payload, status=status_code)

            if errors:
                messages.warning(
                    request,
                    summary_message,
                )
                messages.info(request, "Descargue el CSV resultado para ver qué filas se completaron y sus cdn_image_url.")
                for err in errors[:10]:
                    messages.error(request, err)
            else:
                messages.success(
                    request,
                    (
                        f"Carga de cartas Riftbound completada. Filas: {processed}, subidas ImageKit: {uploaded_to_imagekit} "
                        f"(ZIP: {uploaded_from_zip}, URL: {uploaded_from_url}), sets creados: {len(created_set_codes)}"
                    ),
                )
                if created_set_codes:
                    messages.info(request, f"Sets creados automáticamente: {', '.join(sorted(created_set_codes)[:20])}")
                messages.info(request, "CSV resultado disponible para descarga con cdn_image_url actualizado.")

            return redirect("riftbound-admin-bulk-cards")

    prepared_source = _prepared_source_from_session(request)
    prepared_cards = prepared_source.get("cards") or []
    upload_result = _upload_result_from_session(request)

    return render(
        request,
        "riftbound/admin_bulk_cards.html",
        {
            "form": form,
            "source_form": source_form,
            "prepared_source": prepared_source,
            "prepared_cards_total": len(prepared_cards),
            "prepared_cards_preview": prepared_cards[:25],
            "prepared_has_csv": bool(prepared_source.get("csv_text")),
            "upload_result": upload_result,
            "upload_result_has_csv": bool(upload_result.get("csv_text")),
            "imagekit_session": request.session.get(SESSION_KEY_IMAGEKIT),
        },
    )


@riftbound_admin_owner_required
@require_http_methods(["GET"])
def riftbound_admin_search(request):
    q = (request.GET.get("q") or "").strip()
    set_id_raw = (request.GET.get("set_id") or "").strip()
    card_type = (request.GET.get("card_type") or "").strip().lower()
    rarity = (request.GET.get("rarity") or "").strip().lower()
    is_active = (request.GET.get("is_active") or "all").strip().lower()
    has_description = (request.GET.get("has_description") or "all").strip().lower()
    has_cdn_image = (request.GET.get("has_cdn_image") or "all").strip().lower()

    ban_q = (request.GET.get("ban_q") or "").strip()
    ban_format_id_raw = (request.GET.get("ban_format_id") or "").strip()
    ban_status = (request.GET.get("ban_status") or "").strip().lower()

    page_size_raw = (request.GET.get("page_size") or "200").strip()
    allowed_page_sizes = {100, 200, 500, 1000}
    try:
        page_size = int(page_size_raw)
    except ValueError:
        page_size = 200
    if page_size not in allowed_page_sizes:
        page_size = 200

    ban_page_size_raw = (request.GET.get("ban_page_size") or "100").strip()
    allowed_ban_page_sizes = {50, 100, 200, 500}
    try:
        ban_page_size = int(ban_page_size_raw)
    except ValueError:
        ban_page_size = 100
    if ban_page_size not in allowed_ban_page_sizes:
        ban_page_size = 100

    def _to_int(value: str) -> int | None:
        if not value:
            return None
        try:
            return int(value)
        except ValueError:
            return None

    set_id = _to_int(set_id_raw)
    ban_format_id = _to_int(ban_format_id_raw)

    sets_filter = RiftboundSet.objects.order_by("code")
    formats_filter = RiftboundFormat.objects.order_by("code")
    card_type_choices = list(RiftboundCard._meta.get_field("card_type").choices)
    rarity_choices = list(RiftboundCard._meta.get_field("rarity").choices)
    ban_status_choices = list(RiftboundBanlistEntry._meta.get_field("status").choices)

    cards_qs = RiftboundCard.objects.select_related("set")

    if q:
        cards_qs = cards_qs.filter(
            Q(name__icontains=q)
            | Q(card_number__icontains=q)
            | Q(slug__icontains=q)
            | Q(description__icontains=q)
            | Q(variant__icontains=q)
            | Q(set__code__icontains=q)
            | Q(set__name__icontains=q)
        )

    if set_id:
        cards_qs = cards_qs.filter(set_id=set_id)
    if card_type:
        cards_qs = cards_qs.filter(card_type=card_type)
    if rarity:
        cards_qs = cards_qs.filter(rarity=rarity)

    if is_active == "active":
        cards_qs = cards_qs.filter(is_active=True)
    elif is_active == "inactive":
        cards_qs = cards_qs.filter(is_active=False)

    if has_description == "yes":
        cards_qs = cards_qs.exclude(description__exact="")
    elif has_description == "no":
        cards_qs = cards_qs.filter(description__exact="")

    if has_cdn_image == "yes":
        cards_qs = cards_qs.exclude(cdn_image_url__exact="")
    elif has_cdn_image == "no":
        cards_qs = cards_qs.filter(cdn_image_url__exact="")

    cards_qs = cards_qs.order_by("set__code", "card_number", "name")
    total_cards = cards_qs.count()
    paginator = Paginator(cards_qs, page_size)
    page_obj = paginator.get_page(request.GET.get("page") or 1)
    cards = page_obj.object_list

    cards_query_without_page = request.GET.copy()
    if "page" in cards_query_without_page:
        del cards_query_without_page["page"]

    sets = RiftboundSet.objects.none()
    banlist_qs = RiftboundBanlistEntry.objects.select_related("card", "format")

    if ban_q:
        banlist_qs = banlist_qs.filter(
            Q(card__name__icontains=ban_q)
            | Q(card__card_number__icontains=ban_q)
            | Q(format__code__icontains=ban_q)
            | Q(format__name__icontains=ban_q)
            | Q(note__icontains=ban_q)
        )
    if ban_format_id:
        banlist_qs = banlist_qs.filter(format_id=ban_format_id)
    if ban_status:
        banlist_qs = banlist_qs.filter(status=ban_status)

    banlist_qs = banlist_qs.order_by("format__code", "card__name")
    total_banlist = banlist_qs.count()
    ban_paginator = Paginator(banlist_qs, ban_page_size)
    ban_page_obj = ban_paginator.get_page(request.GET.get("ban_page") or 1)
    banlist = ban_page_obj.object_list

    banlist_query_without_page = request.GET.copy()
    if "ban_page" in banlist_query_without_page:
        del banlist_query_without_page["ban_page"]

    if q:
        sets = RiftboundSet.objects.filter(Q(code__icontains=q) | Q(name__icontains=q)).order_by("code")[:40]

    return render(
        request,
        "riftbound/admin_search.html",
        {
            "q": q,
            "set_id": set_id or "",
            "card_type": card_type,
            "rarity": rarity,
            "is_active": is_active,
            "has_description": has_description,
            "has_cdn_image": has_cdn_image,
            "page_size": page_size,
            "ban_q": ban_q,
            "ban_format_id": ban_format_id or "",
            "ban_status": ban_status,
            "ban_page_size": ban_page_size,
            "total_cards": total_cards,
            "total_banlist": total_banlist,
            "page_obj": page_obj,
            "ban_page_obj": ban_page_obj,
            "cards_query_without_page": cards_query_without_page.urlencode(),
            "banlist_query_without_page": banlist_query_without_page.urlencode(),
            "sets_filter": sets_filter,
            "formats_filter": formats_filter,
            "card_type_choices": card_type_choices,
            "rarity_choices": rarity_choices,
            "ban_status_choices": ban_status_choices,
            "sets": sets,
            "cards": cards,
            "banlist": banlist,
        },
    )
