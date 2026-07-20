from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
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
        return redirect("riftbound-admin-dashboard")
    return render(request, "cards/admin_entity_form.html", {"title": f"Editar banlist: {entry.card.name}", "form": form})


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
    sets = RiftboundSet.objects.none()
    cards = RiftboundCard.objects.none()
    banlist = RiftboundBanlistEntry.objects.none()

    if q:
        sets = RiftboundSet.objects.filter(Q(code__icontains=q) | Q(name__icontains=q)).order_by("code")[:40]
        cards = RiftboundCard.objects.filter(name__icontains=q).select_related("set")[:80]
        banlist = RiftboundBanlistEntry.objects.filter(card__name__icontains=q).select_related("card", "format")[:80]

    return render(
        request,
        "riftbound/admin_search.html",
        {
            "q": q,
            "sets": sets,
            "cards": cards,
            "banlist": banlist,
        },
    )
