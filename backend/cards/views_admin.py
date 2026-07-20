from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .admin_tools import host_from_url, upload_image_url_to_imagekit
from .forms import (
    BanlistEntryForm,
    BulkCardCsvForm,
    BulkEditionCsvForm,
    CardForm,
    EditionForm,
    SeasonForm,
    SessionImagekitEnvForm,
    ToggleEditionsForm,
    csv_rows,
    default_allowed_image_hosts,
    parse_session_env,
    upsert_card_row,
    upsert_edition_row,
)
from .models import BanlistEntry, Card, Edition, Season


SESSION_KEY_IMAGEKIT = "cards_admin_imagekit_session"


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
    form = ToggleEditionsForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        desired_active = form.cleaned_data["active"]
        selected_ids = list(form.cleaned_data["edition_ids"].values_list("id", flat=True))
        selected_format = form.cleaned_data.get("format")

        queryset = Edition.objects.all()
        if selected_ids:
            queryset = queryset.filter(id__in=selected_ids)
        elif selected_format:
            queryset = queryset.filter(format=selected_format)
        else:
            messages.error(request, "Seleccione ediciones o un formato para aplicar el cambio.")
            return redirect("cards-admin-toggle-editions")

        updated = queryset.update(active=desired_active)
        messages.success(request, f"Se actualizaron {updated} ediciones.")
        return redirect("cards-admin-toggle-editions")

    return render(request, "cards/admin_toggle_editions.html", {"form": form})


@cards_admin_owner_required
@require_http_methods(["GET", "POST"])
def cards_admin_season_new(request):
    form = SeasonForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Temporada creada correctamente.")
        return redirect("cards-admin-dashboard")
    return render(request, "cards/admin_entity_form.html", {"title": "Nueva temporada", "form": form})


@cards_admin_owner_required
@require_http_methods(["GET", "POST"])
def cards_admin_season_edit(request, season_id: int):
    season = get_object_or_404(Season, pk=season_id)
    form = SeasonForm(request.POST or None, instance=season)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Temporada actualizada correctamente.")
        return redirect("cards-admin-dashboard")
    return render(request, "cards/admin_entity_form.html", {"title": f"Editar temporada: {season.name}", "form": form})


@cards_admin_owner_required
@require_http_methods(["GET", "POST"])
def cards_admin_edition_new(request):
    form = EditionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Edición creada correctamente.")
        return redirect("cards-admin-dashboard")
    return render(request, "cards/admin_entity_form.html", {"title": "Nueva edición", "form": form})


@cards_admin_owner_required
@require_http_methods(["GET", "POST"])
def cards_admin_edition_edit(request, edition_id: int):
    edition = get_object_or_404(Edition, pk=edition_id)
    form = EditionForm(request.POST or None, instance=edition)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Edición actualizada correctamente.")
        return redirect("cards-admin-dashboard")
    return render(request, "cards/admin_entity_form.html", {"title": f"Editar edición: {edition.title}", "form": form})


@cards_admin_owner_required
@require_http_methods(["GET", "POST"])
def cards_admin_card_new(request):
    form = CardForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Carta creada correctamente.")
        return redirect("cards-admin-dashboard")
    return render(request, "cards/admin_entity_form.html", {"title": "Nueva carta", "form": form})


@cards_admin_owner_required
@require_http_methods(["GET", "POST"])
def cards_admin_card_edit(request, card_id: int):
    card = get_object_or_404(Card, pk=card_id)
    form = CardForm(request.POST or None, instance=card)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Carta actualizada correctamente.")
        return redirect("cards-admin-dashboard")
    return render(request, "cards/admin_entity_form.html", {"title": f"Editar carta: {card.name}", "form": form})


@cards_admin_owner_required
@require_http_methods(["GET", "POST"])
def cards_admin_banlist_new(request):
    form = BanlistEntryForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Entrada de banlist creada correctamente.")
        return redirect("cards-admin-dashboard")
    return render(request, "cards/admin_entity_form.html", {"title": "Nueva entrada banlist", "form": form})


@cards_admin_owner_required
@require_http_methods(["GET", "POST"])
def cards_admin_banlist_edit(request, entry_id: int):
    entry = get_object_or_404(BanlistEntry, pk=entry_id)
    form = BanlistEntryForm(request.POST or None, instance=entry)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Entrada de banlist actualizada correctamente.")
        return redirect("cards-admin-dashboard")
    return render(request, "cards/admin_entity_form.html", {"title": f"Editar banlist: {entry.card_name}", "form": form})


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
    form = BulkCardCsvForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
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

    return render(
        request,
        "cards/admin_bulk_cards.html",
        {
            "form": form,
            "imagekit_session": request.session.get(SESSION_KEY_IMAGEKIT),
        },
    )


@cards_admin_owner_required
def cards_admin_quick_search(request):
    q = (request.GET.get("q") or "").strip()
    seasons = Season.objects.none()
    editions = Edition.objects.none()
    cards = Card.objects.none()
    banlist = BanlistEntry.objects.none()

    if q:
        seasons = Season.objects.filter(name__icontains=q).order_by("-is_active", "-start_date")[:25]
        editions = Edition.objects.filter(title__icontains=q).select_related("format", "season")[:25]
        cards = Card.objects.filter(name__icontains=q).select_related("edition", "rarity", "card_type")[:40]
        banlist = BanlistEntry.objects.filter(card_name__icontains=q).select_related("card")[:40]

    return render(
        request,
        "cards/admin_search.html",
        {
            "q": q,
            "seasons": seasons,
            "editions": editions,
            "cards": cards,
            "banlist": banlist,
        },
    )
