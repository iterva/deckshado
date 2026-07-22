import csv
import hashlib
import html
import io
import re
from functools import wraps
from urllib.parse import urlparse

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.http import HttpResponse, HttpResponseBadRequest
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.text import slugify
from django.views.decorators.http import require_http_methods

from .admin_tools import host_from_url, upload_image_url_to_imagekit
from .forms import (
    BanlistEntryForm,
    BulkCardCsvForm,
    BulkEditionCsvForm,
    CardForm,
    EditionForm,
    SeasonForm,
    SourceCardsUrlForm,
    SessionImagekitEnvForm,
    ToggleEditionsForm,
    csv_rows,
    default_allowed_image_hosts,
    parse_session_env,
    upsert_card_row,
    upsert_edition_row,
)
from .models import BanlistEntry, Card, CardType, Edition, Format, Race, Rarity, Season


SESSION_KEY_IMAGEKIT = "cards_admin_imagekit_session"
SESSION_KEY_SOURCE_PREPARED = "cards_admin_source_prepared"

MYL_API_HOSTS = {"api.myl.cl"}
RIFTBOUND_GALLERY_HOSTS = {"playriftbound.com", "www.playriftbound.com", "riftbound.leagueoflegends.com"}
MYL_IMAGE_HOSTS = {"api.myl.cl"}
RIFTBOUND_IMAGE_HOSTS = {"cmsassets.rgpub.io"}

_IMG_TAG_RE = re.compile(r"<img\b[^>]*>", re.IGNORECASE)


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


def _resolve_source_kind(source_url: str, source_kind: str) -> str:
    if source_kind and source_kind != "auto":
        return source_kind

    host = host_from_url(source_url)
    path = (urlparse(source_url).path or "").lower()
    if host in MYL_API_HOSTS and "/cards/edition/" in path:
        return "myl_api"
    if host in RIFTBOUND_GALLERY_HOSTS and "/card-gallery" in path:
        return "riftbound_gallery"
    raise ValueError("No se pudo detectar el tipo de fuente desde la URL.")


def _build_bulk_csv_text(rows: list[dict[str, str]]) -> str:
    headers = [
        "myl_id",
        "edid",
        "name",
        "edition_slug",
        "type_slug",
        "race_slug",
        "rarity_slug",
        "cost",
        "damage",
        "ability",
        "flavour",
        "image_url",
    ]
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=headers)
    writer.writeheader()
    for row in rows:
        writer.writerow({h: row.get(h, "") for h in headers})
    return buffer.getvalue()


def _collect_cards_from_myl_api(source_url: str, max_cards: int) -> list[dict[str, str]]:
    response = requests.get(source_url, timeout=90)
    response.raise_for_status()
    payload = response.json()

    if payload.get("status") != "OK":
        raise ValueError(f"La API MYL respondió status inválido: {payload.get('status')}")

    edition_data = payload.get("edition") or {}
    edition_id = str(edition_data.get("id") or "").strip()
    if not edition_id:
        raise ValueError("No se encontró id de edición en la respuesta MYL.")

    races = {str(item.get("id")): str(item.get("slug") or "").strip() for item in (payload.get("races") or [])}
    types = {str(item.get("id")): str(item.get("slug") or "").strip() for item in (payload.get("types") or [])}
    rarities = {str(item.get("id")): str(item.get("slug") or "").strip() for item in (payload.get("rarities") or [])}

    cards: list[dict[str, str]] = []
    for raw in (payload.get("cards") or [])[:max_cards]:
        myl_id = str(raw.get("id") or "").strip()
        name = str(raw.get("name") or "").strip()
        edid = str(raw.get("edid") or "").strip()
        if edid.isdigit():
            edid = edid.zfill(3)
        if not name or not edid:
            continue

        image_url = f"https://api.myl.cl/static/cards/{edition_id}/{edid}.png"
        slug_name = slugify(name) or f"myl_{myl_id or len(cards) + 1}"
        cards.append({
            "myl_id": myl_id,
            "edid": edid,
            "name": name,
            "type_slug": types.get(str(raw.get("type") or ""), ""),
            "race_slug": races.get(str(raw.get("race") or ""), ""),
            "rarity_slug": rarities.get(str(raw.get("rarity") or ""), ""),
            "cost": str(raw.get("cost") or ""),
            "damage": str(raw.get("damage") or ""),
            "ability": str(raw.get("ability") or ""),
            "flavour": str(raw.get("flavour") or ""),
            "image_url": image_url,
            "file_name": _safe_download_name(f"{edid}_{slug_name}.png"),
        })

    if not cards:
        raise ValueError("La API MYL no devolvió cartas válidas para procesar.")
    return cards


def _riftbound_name_from_alt(alt_text: str, fallback: str) -> str:
    text = html.unescape(alt_text or "").strip()
    if ":" in text:
        text = text.split(":", 1)[1].strip()
    if "." in text:
        text = text.split(".", 1)[0].strip()
    text = re.sub(r"\s+", " ", text).strip(" -")
    return text or fallback


def _collect_cards_from_riftbound_gallery(source_url: str, max_cards: int) -> list[dict[str, str]]:
    response = requests.get(source_url, timeout=90)
    response.raise_for_status()
    html_text = response.text

    cards: list[dict[str, str]] = []
    seen_urls: set[str] = set()

    for tag in _IMG_TAG_RE.findall(html_text):
        src = html.unescape(_extract_attr(tag, "src")).strip()
        if not src:
            continue

        image_url = _normalize_image_url(src)
        if host_from_url(image_url) not in RIFTBOUND_IMAGE_HOSTS:
            continue
        if image_url in seen_urls:
            continue
        seen_urls.add(image_url)

        fallback_name = f"Riftbound {len(cards) + 1}"
        name = _riftbound_name_from_alt(_extract_attr(tag, "alt"), fallback_name)
        card_idx = len(cards) + 1
        edid = f"{card_idx:03d}"

        image_name = (urlparse(image_url).path.rsplit("/", 1)[-1] or "card.png").strip()
        ext = ".png"
        if "." in image_name:
            maybe_ext = "." + image_name.rsplit(".", 1)[-1].lower()
            if re.fullmatch(r"\.[a-z0-9]{2,5}", maybe_ext):
                ext = maybe_ext

        slug_name = slugify(name) or f"riftbound_{card_idx:03d}"
        synthetic_id = f"rb_{hashlib.sha1(image_url.encode('utf-8')).hexdigest()[:12]}"

        cards.append({
            "myl_id": synthetic_id,
            "edid": edid,
            "name": name,
            "type_slug": "",
            "race_slug": "",
            "rarity_slug": "",
            "cost": "",
            "damage": "",
            "ability": "",
            "flavour": "",
            "image_url": image_url,
            "file_name": _safe_download_name(f"{edid}_{slug_name}{ext}"),
        })

        if len(cards) >= max_cards:
            break

    if not cards:
        raise ValueError("No se encontraron imágenes de cartas en la galería de Riftbound.")
    return cards


def _build_prepared_source_payload(cleaned: dict) -> dict:
    source_url = str(cleaned.get("source_url") or "").strip()
    requested_kind = str(cleaned.get("source_kind") or "auto").strip()
    resolved_kind = _resolve_source_kind(source_url, requested_kind)
    edition_slug = str(cleaned.get("edition_slug") or "").strip()
    generate_bulk_csv = bool(cleaned.get("generate_bulk_csv"))
    max_cards = int(cleaned.get("max_cards") or 1200)

    source_host = host_from_url(source_url)
    if resolved_kind == "myl_api" and source_host not in MYL_API_HOSTS:
        raise ValueError("La URL no corresponde a un host permitido para API MYL.")
    if resolved_kind == "riftbound_gallery" and source_host not in RIFTBOUND_GALLERY_HOSTS:
        raise ValueError("La URL no corresponde a un host permitido para galería Riftbound.")

    if resolved_kind == "myl_api":
        rows = _collect_cards_from_myl_api(source_url, max_cards=max_cards)
    elif resolved_kind == "riftbound_gallery":
        rows = _collect_cards_from_riftbound_gallery(source_url, max_cards=max_cards)
    else:
        raise ValueError("Tipo de fuente no soportado.")

    csv_text = ""
    if generate_bulk_csv:
        if not edition_slug:
            raise ValueError("Debe indicar edition_slug destino para generar CSV de carga masiva.")
        csv_rows_data = []
        for row in rows:
            csv_row = dict(row)
            csv_row["edition_slug"] = edition_slug
            csv_rows_data.append(csv_row)
        csv_text = _build_bulk_csv_text(csv_rows_data)

    cards_for_download = [
        {
            "name": row.get("name", ""),
            "edid": row.get("edid", ""),
            "myl_id": row.get("myl_id", ""),
            "image_url": row.get("image_url", ""),
            "file_name": row.get("file_name", ""),
        }
        for row in rows
    ]

    return {
        "source_url": source_url,
        "source_kind": resolved_kind,
        "edition_slug": edition_slug,
        "generate_bulk_csv": generate_bulk_csv,
        "cards": cards_for_download,
        "csv_text": csv_text,
    }


def _prepared_source_from_session(request) -> dict:
    payload = request.session.get(SESSION_KEY_SOURCE_PREPARED) or {}
    cards = payload.get("cards")
    if not isinstance(cards, list):
        return {}
    return payload


def _download_prepared_csv(request):
    payload = _prepared_source_from_session(request)
    csv_text = payload.get("csv_text") or ""
    if not csv_text:
        return HttpResponseBadRequest("No hay CSV preparado para descarga.")

    source_kind = str(payload.get("source_kind") or "cards")
    response = HttpResponse(csv_text, content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="bulk_cards_{source_kind}.csv"'
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
    image_host = host_from_url(image_url)
    allowed_hosts = MYL_IMAGE_HOSTS | RIFTBOUND_IMAGE_HOSTS
    if image_host not in allowed_hosts:
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


def cards_admin_owner_required(view_func):
    @staff_member_required
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        owner_username = str(
            getattr(settings, "CARDS_ADMIN_OWNER_USERNAME", "iterva")
        ).strip().lower()
        current_username = str(getattr(request.user, "username", "")).strip().lower()
        if current_username != owner_username:
            raise PermissionDenied("No autorizado")
        return view_func(request, *args, **kwargs)

    return _wrapped


def _safe_next_url(request) -> str:
    next_url = (request.POST.get("next") or request.GET.get("next") or "").strip()
    if next_url and url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url
    return ""


def _redirect_next_or_default(request, default_view_name: str):
    next_url = _safe_next_url(request)
    if next_url:
        return redirect(next_url)
    return redirect(default_view_name)


@cards_admin_owner_required
@require_http_methods(["GET", "POST"])
def cards_admin_dashboard(request):
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
                return redirect("cards-admin-dashboard")

    if request.method == "POST" and request.POST.get("action") == "clear_imagekit_session":
        request.session.pop(SESSION_KEY_IMAGEKIT, None)
        messages.info(request, "Se eliminó la sesión de ImageKit cargada.")
        return redirect("cards-admin-dashboard")

    by_format = (
        Edition.objects.values("format__code", "format__name")
        .annotate(total=Count("id"), active_count=Count("id", filter=Q(active=True)))
        .order_by("format__name")
    )

    recent_seasons = Season.objects.order_by("-is_active", "-start_date")[:20]
    recent_editions = Edition.objects.select_related("format", "season").order_by("-date_release", "title")[:120]

    context = {
        "season_count": Season.objects.count(),
        "edition_count": Edition.objects.count(),
        "active_edition_count": Edition.objects.filter(active=True).count(),
        "card_count": Card.objects.count(),
        "banlist_count": BanlistEntry.objects.count(),
        "imagekit_session": request.session.get(SESSION_KEY_IMAGEKIT),
        "imagekit_form": imagekit_form,
        "editions_by_format": by_format,
        "recent_seasons": recent_seasons,
        "recent_editions": recent_editions,
    }
    return render(request, "cards/admin_dashboard.html", context)


def _myl_card_preview_url(card: Card) -> str:
    if card.custom_image_url:
        return card.custom_image_url
    if card.edition and card.edition.myl_id and card.edid:
        return f"https://api.myl.cl/static/cards/{card.edition.myl_id}/{card.edid}.png"
    return ""


@cards_admin_owner_required
@require_http_methods(["GET"])
def cards_admin_edition_cards(request, edition_id: int):
    edition = get_object_or_404(Edition.objects.select_related("format", "season"), pk=edition_id)
    q = (request.GET.get("q") or "").strip()

    cards_qs = Card.objects.filter(edition=edition).select_related("card_type", "rarity", "race").order_by("edid")
    if q:
        cards_qs = cards_qs.filter(name__icontains=q)

    cards_rows = []
    for card in cards_qs[:1000]:
        cards_rows.append({
            "obj": card,
            "preview_url": _myl_card_preview_url(card),
        })

    return render(
        request,
        "cards/admin_edition_cards.html",
        {
            "edition": edition,
            "cards_rows": cards_rows,
            "q": q,
            "total": cards_qs.count(),
        },
    )


@cards_admin_owner_required
@require_http_methods(["GET", "POST"])
def cards_admin_toggle_editions(request):
    if request.method == "POST":
        form = ToggleEditionsForm(request.POST)
    else:
        form = ToggleEditionsForm(preselect_active=True)

    if request.method == "POST" and form.is_valid():
        desired_active = form.cleaned_data["active"]
        selected_ids = list(form.cleaned_data["edition_ids"].values_list("id", flat=True))
        selected_format = form.cleaned_data.get("format")

        scope_qs = Edition.objects.all()
        if selected_format:
            scope_qs = scope_qs.filter(format=selected_format)

        if desired_active:
            if not selected_ids and not selected_format:
                messages.error(request, "Seleccione ediciones o un formato para aplicar el cambio.")
                return redirect("cards-admin-toggle-editions")

            selected_scope_qs = scope_qs.filter(id__in=selected_ids)
            activated = selected_scope_qs.update(active=True)
            deactivated = scope_qs.exclude(id__in=selected_ids).update(active=False)
            messages.success(
                request,
                f"Se sincronizaron ediciones: {activated} activadas y {deactivated} desactivadas.",
            )
            return redirect("cards-admin-toggle-editions")

        if selected_ids:
            updated = scope_qs.filter(id__in=selected_ids).update(active=False)
        elif selected_format:
            updated = scope_qs.update(active=False)
        else:
            messages.error(request, "Seleccione ediciones o un formato para aplicar el cambio.")
            return redirect("cards-admin-toggle-editions")

        messages.success(request, f"Se actualizaron {updated} ediciones.")
        return redirect("cards-admin-toggle-editions")

    return render(request, "cards/admin_toggle_editions.html", {"form": form})


@cards_admin_owner_required
@require_http_methods(["GET", "POST"])
def cards_admin_season_new(request):
    form = SeasonForm(request.POST or None)
    next_url = _safe_next_url(request)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Temporada creada correctamente.")
        return _redirect_next_or_default(request, "cards-admin-dashboard")
    return render(request, "cards/admin_entity_form.html", {"title": "Nueva temporada", "form": form, "next_url": next_url})


@cards_admin_owner_required
@require_http_methods(["GET", "POST"])
def cards_admin_season_edit(request, season_id: int):
    season = get_object_or_404(Season, pk=season_id)
    form = SeasonForm(request.POST or None, instance=season)
    next_url = _safe_next_url(request)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Temporada actualizada correctamente.")
        return _redirect_next_or_default(request, "cards-admin-dashboard")
    return render(request, "cards/admin_entity_form.html", {"title": f"Editar temporada: {season.name}", "form": form, "next_url": next_url})


@cards_admin_owner_required
@require_http_methods(["GET", "POST"])
def cards_admin_edition_new(request):
    form = EditionForm(request.POST or None)
    next_url = _safe_next_url(request)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Edición creada correctamente.")
        return _redirect_next_or_default(request, "cards-admin-dashboard")
    return render(request, "cards/admin_entity_form.html", {"title": "Nueva edición", "form": form, "next_url": next_url})


@cards_admin_owner_required
@require_http_methods(["GET", "POST"])
def cards_admin_edition_edit(request, edition_id: int):
    edition = get_object_or_404(Edition, pk=edition_id)
    form = EditionForm(request.POST or None, instance=edition)
    next_url = _safe_next_url(request)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Edición actualizada correctamente.")
        return _redirect_next_or_default(request, "cards-admin-dashboard")
    return render(request, "cards/admin_entity_form.html", {"title": f"Editar edición: {edition.title}", "form": form, "next_url": next_url})


@cards_admin_owner_required
@require_http_methods(["GET", "POST"])
def cards_admin_card_new(request):
    form = CardForm(request.POST or None)
    next_url = _safe_next_url(request)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Carta creada correctamente.")
        return _redirect_next_or_default(request, "cards-admin-dashboard")
    return render(request, "cards/admin_entity_form.html", {"title": "Nueva carta", "form": form, "next_url": next_url})


@cards_admin_owner_required
@require_http_methods(["GET", "POST"])
def cards_admin_card_edit(request, card_id: int):
    card = get_object_or_404(Card, pk=card_id)
    form = CardForm(request.POST or None, instance=card)
    next_url = _safe_next_url(request)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Carta actualizada correctamente.")
        return _redirect_next_or_default(request, "cards-admin-dashboard")
    return render(request, "cards/admin_entity_form.html", {"title": f"Editar carta: {card.name}", "form": form, "next_url": next_url})


@cards_admin_owner_required
@require_http_methods(["GET", "POST"])
def cards_admin_banlist_new(request):
    form = BanlistEntryForm(request.POST or None)
    next_url = _safe_next_url(request)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Entrada de banlist creada correctamente.")
        return _redirect_next_or_default(request, "cards-admin-dashboard")
    return render(request, "cards/admin_entity_form.html", {"title": "Nueva entrada banlist", "form": form, "next_url": next_url})


@cards_admin_owner_required
@require_http_methods(["GET", "POST"])
def cards_admin_banlist_edit(request, entry_id: int):
    entry = get_object_or_404(BanlistEntry, pk=entry_id)
    form = BanlistEntryForm(request.POST or None, instance=entry)
    next_url = _safe_next_url(request)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Entrada de banlist actualizada correctamente.")
        return _redirect_next_or_default(request, "cards-admin-dashboard")
    return render(request, "cards/admin_entity_form.html", {"title": f"Editar banlist: {entry.card_name}", "form": form, "next_url": next_url})


@cards_admin_owner_required
@require_http_methods(["GET", "POST"])
def cards_admin_bulk_editions(request):
    form = BulkEditionCsvForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        created_or_updated = 0
        errors: list[str] = []
        for idx, row in enumerate(csv_rows(form.cleaned_data["csv_file"]), start=2):
            try:
                upsert_edition_row(row)
                created_or_updated += 1
            except Exception as exc:
                errors.append(f"Línea {idx}: {exc}")

        if errors:
            messages.warning(request, f"Procesadas {created_or_updated} filas con {len(errors)} errores.")
            for err in errors[:10]:
                messages.error(request, err)
        else:
            messages.success(request, f"Carga de ediciones completada: {created_or_updated} filas.")

        return redirect("cards-admin-bulk-editions")

    return render(request, "cards/admin_bulk_editions.html", {"form": form})


@cards_admin_owner_required
@require_http_methods(["GET", "POST"])
def cards_admin_bulk_cards(request):
    if request.method == "GET":
        download_kind = (request.GET.get("download") or "").strip().lower()
        if download_kind == "csv":
            return _download_prepared_csv(request)
        if download_kind == "image":
            return _download_prepared_image(request)

    form = BulkCardCsvForm()
    source_form = SourceCardsUrlForm()

    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()

        if action == "prepare_source_cards":
            source_form = SourceCardsUrlForm(request.POST)
            if source_form.is_valid():
                try:
                    prepared_payload = _build_prepared_source_payload(source_form.cleaned_data)
                except Exception as exc:
                    messages.error(request, f"No se pudo preparar la fuente: {exc}")
                else:
                    request.session[SESSION_KEY_SOURCE_PREPARED] = prepared_payload
                    messages.success(
                        request,
                        f"Fuente preparada correctamente. Cartas detectadas: {len(prepared_payload.get('cards') or [])}",
                    )
                    return redirect("cards-admin-bulk-cards")

        elif action == "clear_prepared_source":
            request.session.pop(SESSION_KEY_SOURCE_PREPARED, None)
            messages.info(request, "Se eliminó la preparación actual de fuente.")
            return redirect("cards-admin-bulk-cards")

        else:
            form = BulkCardCsvForm(request.POST or None, request.FILES or None)
            if form.is_valid():
                created_or_updated = 0
                uploaded_to_imagekit = 0
                errors: list[str] = []

                do_upload = form.cleaned_data.get("upload_images_to_imagekit", False)
                imagekit_folder = form.cleaned_data.get("imagekit_folder", "").strip() or "deckshado/myl_cards/admin_bulk"
                session_env = request.session.get(SESSION_KEY_IMAGEKIT) or {}

                if do_upload and not session_env:
                    messages.error(
                        request,
                        "Debe cargar primero el archivo env de sesión de ImageKit para usar subida de imágenes.",
                    )
                    return redirect("cards-admin-bulk-cards")

                allowed_hosts = default_allowed_image_hosts()

                for idx, row in enumerate(csv_rows(form.cleaned_data["csv_file"]), start=2):
                    try:
                        source_image = (row.get("image_url") or row.get("custom_image_url") or "").strip()
                        if do_upload and source_image:
                            host = host_from_url(source_image)
                            if host not in allowed_hosts:
                                raise ValueError(f"Host no permitido para subida: {host}")

                            file_name = f"{row.get('myl_id', 'card')}_{row.get('edid', '')}"
                            uploaded_url = upload_image_url_to_imagekit(
                                source_url=source_image,
                                imagekit_private_key=session_env["private_key"],
                                imagekit_url_endpoint=session_env["url"],
                                folder=imagekit_folder,
                                file_name=file_name,
                            )
                            row["custom_image_url"] = uploaded_url
                            uploaded_to_imagekit += 1

                        upsert_card_row(row)
                        created_or_updated += 1
                    except Exception as exc:
                        errors.append(f"Línea {idx}: {exc}")

                if errors:
                    messages.warning(
                        request,
                        f"Cartas procesadas: {created_or_updated}, subidas ImageKit: {uploaded_to_imagekit}, errores: {len(errors)}",
                    )
                    for err in errors[:10]:
                        messages.error(request, err)
                else:
                    messages.success(
                        request,
                        f"Carga de cartas completada. Filas: {created_or_updated}, subidas ImageKit: {uploaded_to_imagekit}",
                    )

                return redirect("cards-admin-bulk-cards")

    prepared_source = _prepared_source_from_session(request)
    prepared_cards = prepared_source.get("cards") or []

    return render(
        request,
        "cards/admin_bulk_cards.html",
        {
            "form": form,
            "source_form": source_form,
            "imagekit_session": request.session.get(SESSION_KEY_IMAGEKIT),
            "prepared_source": prepared_source,
            "prepared_cards_total": len(prepared_cards),
            "prepared_cards_preview": prepared_cards[:25],
            "prepared_has_csv": bool(prepared_source.get("csv_text")),
        },
    )


@cards_admin_owner_required
def cards_admin_quick_search(request):
    q = (request.GET.get("q") or "").strip()
    format_code = (request.GET.get("format_code") or "").strip().lower()
    edition_id_raw = (request.GET.get("edition_id") or "").strip()
    type_id_raw = (request.GET.get("type_id") or "").strip()
    rarity_id_raw = (request.GET.get("rarity_id") or "").strip()
    race_id_raw = (request.GET.get("race_id") or "").strip()
    edition_active = (request.GET.get("edition_active") or "all").strip().lower()
    has_ability = (request.GET.get("has_ability") or "all").strip().lower()
    has_custom_image = (request.GET.get("has_custom_image") or "all").strip().lower()

    page_size_raw = (request.GET.get("page_size") or "200").strip()
    allowed_page_sizes = {100, 200, 500, 1000}
    try:
        page_size = int(page_size_raw)
    except ValueError:
        page_size = 200
    if page_size not in allowed_page_sizes:
        page_size = 200

    def _to_int(value: str) -> int | None:
        if not value:
            return None
        try:
            return int(value)
        except ValueError:
            return None

    edition_id = _to_int(edition_id_raw)
    type_id = _to_int(type_id_raw)
    rarity_id = _to_int(rarity_id_raw)
    race_id = _to_int(race_id_raw)

    formats = Format.objects.filter(code__in=["imp", "esc"]).order_by("name")
    editions_filter_qs = Edition.objects.select_related("format").order_by("title")
    if format_code:
        editions_filter_qs = editions_filter_qs.filter(format__code=format_code)

    card_types = CardType.objects.order_by("name")
    rarities = Rarity.objects.order_by("display_order", "name")
    races = Race.objects.order_by("name")

    cards_qs = Card.objects.select_related("edition", "edition__format", "rarity", "card_type", "race")

    if q:
        cards_qs = cards_qs.filter(
            Q(name__icontains=q)
            | Q(slug__icontains=q)
            | Q(myl_id__icontains=q)
            | Q(edid__icontains=q)
            | Q(edition__title__icontains=q)
            | Q(ability__icontains=q)
        )

    if format_code:
        cards_qs = cards_qs.filter(edition__format__code=format_code)
    if edition_id:
        cards_qs = cards_qs.filter(edition_id=edition_id)
    if type_id:
        cards_qs = cards_qs.filter(card_type_id=type_id)
    if rarity_id:
        cards_qs = cards_qs.filter(rarity_id=rarity_id)
    if race_id:
        cards_qs = cards_qs.filter(race_id=race_id)

    if edition_active == "active":
        cards_qs = cards_qs.filter(edition__active=True)
    elif edition_active == "inactive":
        cards_qs = cards_qs.filter(edition__active=False)

    if has_ability == "yes":
        cards_qs = cards_qs.exclude(ability__isnull=True).exclude(ability__exact="")
    elif has_ability == "no":
        cards_qs = cards_qs.filter(Q(ability__isnull=True) | Q(ability__exact=""))

    if has_custom_image == "yes":
        cards_qs = cards_qs.exclude(custom_image_url__isnull=True).exclude(custom_image_url__exact="")
    elif has_custom_image == "no":
        cards_qs = cards_qs.filter(Q(custom_image_url__isnull=True) | Q(custom_image_url__exact=""))

    cards_qs = cards_qs.order_by("edition__format__code", "edition__title", "edid", "name")
    total_cards = cards_qs.count()
    paginator = Paginator(cards_qs, page_size)
    page_obj = paginator.get_page(request.GET.get("page") or 1)
    cards = page_obj.object_list

    query_without_page = request.GET.copy()
    if "page" in query_without_page:
        del query_without_page["page"]

    seasons = Season.objects.none()
    editions = Edition.objects.none()
    banlist = BanlistEntry.objects.none()

    if q:
        seasons = Season.objects.filter(name__icontains=q).order_by("-is_active", "-start_date")[:25]
        editions = Edition.objects.filter(title__icontains=q).select_related("format", "season")[:25]
        banlist = BanlistEntry.objects.filter(card_name__icontains=q).select_related("card")[:40]

    return render(
        request,
        "cards/admin_search.html",
        {
            "q": q,
            "format_code": format_code,
            "edition_id": edition_id or "",
            "type_id": type_id or "",
            "rarity_id": rarity_id or "",
            "race_id": race_id or "",
            "edition_active": edition_active,
            "has_ability": has_ability,
            "has_custom_image": has_custom_image,
            "page_size": page_size,
            "total_cards": total_cards,
            "page_obj": page_obj,
            "query_without_page": query_without_page.urlencode(),
            "formats": formats,
            "editions_filter": editions_filter_qs,
            "card_types": card_types,
            "rarities": rarities,
            "races": races,
            "seasons": seasons,
            "editions": editions,
            "cards": cards,
            "banlist": banlist,
        },
    )
