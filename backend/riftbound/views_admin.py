from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods

from cards.admin_tools import host_from_url, upload_image_url_to_imagekit
from cards.forms import SessionImagekitEnvForm, default_allowed_image_hosts, parse_session_env

from .forms_admin import (
    BulkRiftboundCardCsvForm,
    BulkRiftboundSetCsvForm,
    RiftboundBanlistEntryForm,
    RiftboundCardForm,
    RiftboundSetForm,
    ToggleRiftboundSetsForm,
    csv_rows,
    upsert_card_row,
    upsert_set_row,
)
from .models import RiftboundBanlistEntry, RiftboundCard, RiftboundFormat, RiftboundSet


SESSION_KEY_IMAGEKIT = "cards_admin_imagekit_session"


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
    form = ToggleRiftboundSetsForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        selected = list(form.cleaned_data["set_ids"].values_list("id", flat=True))
        active = form.cleaned_data["active"]
        if not selected:
            messages.error(request, "Seleccione al menos un set.")
            return redirect("riftbound-admin-toggle-sets")
        updated = RiftboundCard.objects.filter(set_id__in=selected).update(is_active=active)
        messages.success(request, f"Se actualizaron {updated} cartas de Riftbound.")
        return redirect("riftbound-admin-toggle-sets")

    return render(request, "riftbound/admin_toggle_sets.html", {"form": form})


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
    form = BulkRiftboundCardCsvForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        processed = 0
        uploaded_to_imagekit = 0
        errors: list[str] = []

        do_upload = form.cleaned_data.get("upload_images_to_imagekit", False)
        imagekit_folder = form.cleaned_data.get("imagekit_folder", "").strip() or "deckshado/riftbound/cards_admin_bulk"
        session_env = request.session.get(SESSION_KEY_IMAGEKIT) or {}

        if do_upload and not session_env:
            messages.error(request, "Debe cargar primero el archivo env de sesión de ImageKit para subir imágenes.")
            return redirect("riftbound-admin-bulk-cards")

        allowed_hosts = default_allowed_image_hosts()

        for idx, row in enumerate(csv_rows(form.cleaned_data["csv_file"]), start=2):
            try:
                source_image = (row.get("image_url") or row.get("cdn_image_url") or "").strip()
                if do_upload and source_image:
                    host = host_from_url(source_image)
                    if host not in allowed_hosts:
                        raise ValueError(f"Host no permitido para subida: {host}")

                    file_name = row.get("card_number", "rb-card")
                    uploaded_url = upload_image_url_to_imagekit(
                        source_url=source_image,
                        imagekit_private_key=session_env["private_key"],
                        imagekit_url_endpoint=session_env["url"],
                        folder=imagekit_folder,
                        file_name=file_name,
                    )
                    row["cdn_image_url"] = uploaded_url
                    uploaded_to_imagekit += 1

                upsert_card_row(row)
                processed += 1
            except Exception as exc:
                errors.append(f"Línea {idx}: {exc}")

        if errors:
            messages.warning(
                request,
                f"Cartas procesadas: {processed}, subidas ImageKit: {uploaded_to_imagekit}, errores: {len(errors)}",
            )
            for err in errors[:10]:
                messages.error(request, err)
        else:
            messages.success(
                request,
                f"Carga de cartas Riftbound completada. Filas: {processed}, subidas ImageKit: {uploaded_to_imagekit}",
            )

        return redirect("riftbound-admin-bulk-cards")

    return render(
        request,
        "riftbound/admin_bulk_cards.html",
        {
            "form": form,
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
