import re
import uuid

from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q, Count, Sum, F
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from backend.cdn_image_upload import upload_image_to_cdn, CdnImageUploadError
from users.models import Notification

from .models import (
    BinderProfile, CollectionEntry, WishlistEntry, StoreOrder, StoreOrderItem,
    CarpetaTourProgress, MylStorePermission,
)
from .serializers import (
    BinderProfileSerializer,
    PublicBinderProfileSerializer,
    CollectionEntrySerializer,
    CollectionEntryWriteSerializer,
    WishlistEntrySerializer,
    WishlistEntryWriteSerializer,
    StoreOrderSerializer,
    StoreOrderCreateSerializer,
    MylStorePermissionSerializer,
)


class CarpetaPagination(PageNumberPagination):
    page_size = 40
    page_size_query_param = "page_size"
    max_page_size = 200


# ── Binder Profile ──────────────────────────────────────

WRITABLE_PROFILE_FIELDS = {
    "is_store_public", "display_name", "bio", "city", "country",
    "whatsapp", "instagram", "discord", "email_public",
    "payment_methods", "shipping_info", "accepts_trades",
}


@api_view(["GET", "PATCH"])
@permission_classes([permissions.IsAuthenticated])
def binder_profile_view(request):
    profile, _ = BinderProfile.objects.get_or_create(user=request.user)
    if request.method == "PATCH":
        for k, v in (request.data or {}).items():
            if k in WRITABLE_PROFILE_FIELDS:
                setattr(profile, k, v)
        profile.save()
    return Response(BinderProfileSerializer(profile, context={"request": request}).data)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
@parser_classes([JSONParser, MultiPartParser, FormParser])
def upload_binder_avatar(request):
    avatar_url = (request.data.get("avatar_url") or "").strip()
    file_obj = request.FILES.get("file")

    if not avatar_url and file_obj is not None:
        try:
            avatar_url = upload_image_to_cdn(file_obj, folder="deckshado/binder_avatars")
        except CdnImageUploadError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    if not avatar_url:
        return Response(
            {"detail": "No se envio URL o archivo de imagen."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    profile, _ = BinderProfile.objects.get_or_create(user=request.user)
    profile.binder_avatar = avatar_url
    profile.save()
    return Response(BinderProfileSerializer(profile, context={"request": request}).data)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def regenerate_share_token(request):
    profile, _ = BinderProfile.objects.get_or_create(user=request.user)
    profile.share_token = uuid.uuid4()
    profile.save()
    return Response({"share_token": str(profile.share_token)})


# ── Colaboración / permisos de tienda ("Carpetas Compartidas") ──────────

OWNER_PERMISSIONS = {
    "view_collection": True,
    "edit_collection": True,
    "delete_collection": True,
    "edit_market": True,
    "remove_from_market": True,
    "view_orders": True,
    "view_history": True,
    "accept_orders": True,
    "reject_orders": True,
    "manage_permissions": True,
}

PERMISSION_FIELD_MAP = {
    "view_collection": "can_view_collection",
    "edit_collection": "can_edit_collection",
    "delete_collection": "can_delete_collection",
    "edit_market": "can_edit_market",
    "remove_from_market": "can_remove_from_market",
    "view_orders": "can_view_orders",
    "view_history": "can_view_history",
    "accept_orders": "can_accept_orders",
    "reject_orders": "can_reject_orders",
    "manage_permissions": "can_manage_permissions",
}

COLLECTION_FIELDS = {"quantity", "condition", "language", "is_foil", "notes"}
MARKET_FIELDS = {"price", "selling_quantity", "photo_url", "photo_url_2"}


def _get_or_create_profile_for_user(user):
    profile, _ = BinderProfile.objects.get_or_create(user=user)
    return profile


def _permissions_payload_for_user(profile, user):
    if profile.user_id == user.id:
        return dict(OWNER_PERMISSIONS)
    perm = MylStorePermission.objects.filter(store_profile=profile, user=user).first()
    if not perm:
        return None
    return perm.permissions_dict()


def _can_permissions(perm_payload, key):
    return bool((perm_payload or {}).get(key))


def _store_profile_id_from_request(request):
    raw = request.query_params.get("store_profile_id")
    if raw in (None, ""):
        body = request.data if hasattr(request, "data") else None
        raw = body.get("store_profile_id") if hasattr(body, "get") else None
    if raw in (None, ""):
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise PermissionDenied("store_profile_id invalido")
    if value <= 0:
        raise PermissionDenied("store_profile_id invalido")
    return value


def _resolve_workspace(request, required_permission=None):
    requested_profile_id = _store_profile_id_from_request(request)

    if requested_profile_id is None:
        profile = _get_or_create_profile_for_user(request.user)
    else:
        profile = BinderProfile.objects.filter(pk=requested_profile_id).select_related("user").first()
        if not profile:
            raise PermissionDenied("Tienda no encontrada")

    permissions_payload = _permissions_payload_for_user(profile, request.user)
    if permissions_payload is None:
        raise PermissionDenied("No tienes acceso a esta tienda")

    if required_permission and not _can_permissions(permissions_payload, required_permission):
        raise PermissionDenied("No tienes permiso para esta accion")

    is_owner = profile.user_id == request.user.id
    return profile, permissions_payload, is_owner


def _is_store_permission_manager(profile, user):
    if profile.user_id == user.id:
        return True
    perm = MylStorePermission.objects.filter(store_profile=profile, user=user).first()
    return bool(perm and perm.can_manage_permissions)


def _permission_values_from_payload(payload):
    source = payload.get("permissions") if isinstance(payload.get("permissions"), dict) else payload
    values = {}
    for short_key, model_field in PERMISSION_FIELD_MAP.items():
        if short_key in source:
            values[model_field] = bool(source.get(short_key))
        elif model_field in source:
            values[model_field] = bool(source.get(model_field))
    return values


def _workspace_payload(profile, request, permissions_payload, is_owner):
    profile_data = BinderProfileSerializer(profile, context={"request": request}).data
    return {
        "store_profile_id": profile.id,
        "is_owner": bool(is_owner),
        "owner_username": profile.user.username,
        "permissions": permissions_payload,
        "profile": profile_data,
    }


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def myl_workspaces(request):
    own_profile = _get_or_create_profile_for_user(request.user)
    results = [
        _workspace_payload(own_profile, request, dict(OWNER_PERMISSIONS), is_owner=True)
    ]

    collaborator_qs = (
        MylStorePermission.objects
        .filter(user=request.user)
        .select_related("store_profile", "store_profile__user")
    )
    seen = {own_profile.id}
    for perm in collaborator_qs:
        profile = perm.store_profile
        if profile.id in seen:
            continue
        permissions_payload = perm.permissions_dict()
        if not any(permissions_payload.values()):
            continue
        seen.add(profile.id)
        results.append(_workspace_payload(profile, request, permissions_payload, is_owner=False))

    results.sort(key=lambda row: (0 if row["is_owner"] else 1, row["owner_username"].lower()))
    return Response({"results": results})


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def myl_workspace_permissions(request, profile_id):
    profile = get_object_or_404(BinderProfile.objects.select_related("user"), pk=profile_id)
    if not _is_store_permission_manager(profile, request.user):
        raise PermissionDenied("No puedes administrar permisos de esta tienda")

    perms = (
        MylStorePermission.objects
        .filter(store_profile=profile)
        .exclude(user=profile.user)
        .select_related("user", "granted_by")
    )
    data = MylStorePermissionSerializer(perms, many=True, context={"request": request}).data
    return Response({"store_profile_id": profile.id, "results": data})


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def myl_workspace_permission_upsert(request, profile_id):
    profile = get_object_or_404(BinderProfile.objects.select_related("user"), pk=profile_id)
    if not _is_store_permission_manager(profile, request.user):
        raise PermissionDenied("No puedes administrar permisos de esta tienda")

    payload = request.data or {}
    user_identifier = (payload.get("username") or payload.get("email") or payload.get("user") or "").strip()
    if not user_identifier:
        return Response({"detail": "Debes indicar username o email"}, status=status.HTTP_400_BAD_REQUEST)

    user_model = get_user_model()
    target_user = user_model.objects.filter(username__iexact=user_identifier).first()
    if target_user is None and "@" in user_identifier:
        target_user = user_model.objects.filter(email__iexact=user_identifier).first()
    if target_user is None:
        return Response({"detail": "Usuario no encontrado"}, status=status.HTTP_404_NOT_FOUND)
    if target_user.id == profile.user_id:
        return Response({"detail": "No puedes asignar permisos al propietario"}, status=status.HTTP_400_BAD_REQUEST)

    values = _permission_values_from_payload(payload)
    if not values:
        return Response({"detail": "No se enviaron permisos a actualizar"}, status=status.HTTP_400_BAD_REQUEST)

    is_owner = profile.user_id == request.user.id
    if (not is_owner) and values.get("can_manage_permissions"):
        raise PermissionDenied("Solo el propietario puede delegar la gestion de permisos")

    perm, created = MylStorePermission.objects.get_or_create(
        store_profile=profile,
        user=target_user,
        defaults={"granted_by": request.user},
    )
    for field_name, field_value in values.items():
        setattr(perm, field_name, field_value)

    has_any_permission = any(bool(getattr(perm, field)) for field in PERMISSION_FIELD_MAP.values())
    if not has_any_permission:
        perm.delete()
        return Response({"deleted": True})

    perm.granted_by = request.user
    perm.save()
    data = MylStorePermissionSerializer(perm, context={"request": request}).data
    return Response(data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


@api_view(["PATCH"])
@permission_classes([permissions.IsAuthenticated])
def myl_workspace_permission_update(request, profile_id, permission_id):
    profile = get_object_or_404(BinderProfile.objects.select_related("user"), pk=profile_id)
    if not _is_store_permission_manager(profile, request.user):
        raise PermissionDenied("No puedes administrar permisos de esta tienda")

    perm = get_object_or_404(
        MylStorePermission.objects.select_related("user", "granted_by"),
        pk=permission_id,
        store_profile=profile,
    )
    if perm.user_id == profile.user_id:
        return Response({"detail": "No puedes editar permisos del propietario"}, status=status.HTTP_400_BAD_REQUEST)

    values = _permission_values_from_payload(request.data or {})
    if not values:
        return Response({"detail": "No se enviaron permisos a actualizar"}, status=status.HTTP_400_BAD_REQUEST)

    is_owner = profile.user_id == request.user.id
    if (not is_owner) and values.get("can_manage_permissions"):
        raise PermissionDenied("Solo el propietario puede delegar la gestion de permisos")

    for field_name, field_value in values.items():
        setattr(perm, field_name, field_value)

    has_any_permission = any(bool(getattr(perm, field)) for field in PERMISSION_FIELD_MAP.values())
    if not has_any_permission:
        perm.delete()
        return Response({"deleted": True})

    perm.granted_by = request.user
    perm.save()
    return Response(MylStorePermissionSerializer(perm, context={"request": request}).data)


@api_view(["DELETE"])
@permission_classes([permissions.IsAuthenticated])
def myl_workspace_permission_delete(request, profile_id, permission_id):
    profile = get_object_or_404(BinderProfile.objects.select_related("user"), pk=profile_id)
    if not _is_store_permission_manager(profile, request.user):
        raise PermissionDenied("No puedes administrar permisos de esta tienda")

    perm = get_object_or_404(MylStorePermission, pk=permission_id, store_profile=profile)
    if perm.user_id == profile.user_id:
        return Response({"detail": "No puedes eliminar permisos del propietario"}, status=status.HTTP_400_BAD_REQUEST)
    perm.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


# ── Collection ───────────────────────────────────────────

class MyCollectionListView(generics.ListAPIView):
    serializer_class = CollectionEntrySerializer
    pagination_class = CarpetaPagination
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        profile, _, _ = _resolve_workspace(self.request, required_permission="view_collection")
        qs = CollectionEntry.objects.filter(user=profile.user).select_related(
            "card__edition", "card__rarity", "card__race", "card__card_type"
        )
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(card__name__icontains=search)
        selling = self.request.query_params.get("selling")
        if selling == "1":
            qs = qs.filter(selling_quantity__gt=0)
        return qs


def _apply_collection_fields(entry, data):
    """Aplica los campos editables a una entrada (sin guardar)."""
    if "quantity" in data:
        entry.quantity = max(1, int(data["quantity"]))
    if "price" in data:
        entry.price = data["price"] if data["price"] not in ("", None) else None
    if "selling_quantity" in data:
        entry.selling_quantity = max(0, int(data["selling_quantity"]))
    if "condition" in data:
        entry.condition = data["condition"]
    if "language" in data:
        entry.language = data["language"]
    if "is_foil" in data:
        entry.is_foil = bool(data["is_foil"])
    if "notes" in data:
        entry.notes = (data["notes"] or "")[:200]
    if "photo_url" in data:
        entry.photo_url = (data["photo_url"] or "")[:500]
    if "photo_url_2" in data:
        entry.photo_url_2 = (data["photo_url_2"] or "")[:500]
    if entry.selling_quantity > entry.quantity:
        entry.selling_quantity = entry.quantity


def _ensure_market_permission_for_selling_change(permissions_payload, old_selling, new_selling):
    old_value = int(old_selling or 0)
    new_value = int(new_selling or 0)
    if old_value > 0 and new_value == 0:
        if not (_can_permissions(permissions_payload, "remove_from_market") or _can_permissions(permissions_payload, "edit_market")):
            raise PermissionDenied("No tienes permiso para quitar cartas de la venta")
        return
    if old_value != new_value and not _can_permissions(permissions_payload, "edit_market"):
        raise PermissionDenied("No tienes permiso para editar ventas/precios")


def _enforce_entry_permissions(data, permissions_payload, entry=None, created=False):
    requested_fields = set(data.keys())
    requested_fields.discard("card")
    requested_fields.discard("store_profile_id")
    requested_fields.discard("file")
    requested_fields.discard("slot")

    if requested_fields & COLLECTION_FIELDS:
        if not _can_permissions(permissions_payload, "edit_collection"):
            raise PermissionDenied("No tienes permiso para editar la carpeta")

    if requested_fields & MARKET_FIELDS:
        if "selling_quantity" in requested_fields:
            old_selling = entry.selling_quantity if entry is not None else 0
            try:
                new_selling = int(data.get("selling_quantity") or 0)
            except (TypeError, ValueError):
                new_selling = old_selling
            _ensure_market_permission_for_selling_change(permissions_payload, old_selling, new_selling)

            if (requested_fields & MARKET_FIELDS) - {"selling_quantity"} and not _can_permissions(permissions_payload, "edit_market"):
                raise PermissionDenied("No tienes permiso para editar ventas/precios")
        else:
            if not _can_permissions(permissions_payload, "edit_market"):
                raise PermissionDenied("No tienes permiso para editar ventas/precios")

    if created and not _can_permissions(permissions_payload, "edit_collection"):
        raise PermissionDenied("No tienes permiso para agregar cartas a la carpeta")


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
@parser_classes([JSONParser, MultiPartParser, FormParser])
def collection_upsert(request):
    data = request.data.dict() if hasattr(request.data, "dict") else dict(request.data)
    card_id = data.get("card")
    if not card_id:
        return Response({"detail": "card es requerido."}, status=status.HTTP_400_BAD_REQUEST)

    profile, permissions_payload, _ = _resolve_workspace(request, required_permission="view_collection")

    file_obj = request.FILES.get("file")
    if file_obj is not None:
        slot = str(data.get("slot", "1")).strip()
        target_field = "photo_url_2" if slot == "2" else "photo_url"
        try:
            uploaded_url = upload_image_to_cdn(file_obj, folder="deckshado/store_card_photos")
        except CdnImageUploadError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        data[target_field] = uploaded_url

    entry = CollectionEntry.objects.filter(user=profile.user, card_id=card_id).first()
    created = entry is None
    if created:
        _enforce_entry_permissions(data, permissions_payload, entry=None, created=True)
        entry = CollectionEntry.objects.create(
            user=profile.user, card_id=card_id,
            quantity=int(data.get("quantity", 1) or 1),
        )
    else:
        _enforce_entry_permissions(data, permissions_payload, entry=entry, created=False)

    _apply_collection_fields(entry, data)
    entry.save()

    entry = CollectionEntry.objects.select_related(
        "card__edition", "card__rarity", "card__race", "card__card_type"
    ).get(pk=entry.pk)
    return Response(CollectionEntrySerializer(entry).data, status=status.HTTP_200_OK)


@api_view(["DELETE"])
@permission_classes([permissions.IsAuthenticated])
def collection_delete(request, card_id):
    profile, permissions_payload, _ = _resolve_workspace(request, required_permission="delete_collection")
    deleted, _ = CollectionEntry.objects.filter(user=profile.user, card_id=card_id).delete()
    if deleted:
        return Response(status=status.HTTP_204_NO_CONTENT)
    return Response({"detail": "Entrada no encontrada."}, status=status.HTTP_404_NOT_FOUND)


# ── Wishlist ─────────────────────────────────────────────

class MyWishlistListView(generics.ListAPIView):
    serializer_class = WishlistEntrySerializer
    pagination_class = CarpetaPagination
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = WishlistEntry.objects.filter(user=self.request.user).select_related(
            "card__edition", "card__rarity", "card__race", "card__card_type"
        )
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(card__name__icontains=search)
        return qs


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def wishlist_toggle(request):
    card_id = request.data.get("card")
    if not card_id:
        return Response({"detail": "card es requerido."}, status=status.HTTP_400_BAD_REQUEST)

    existing = WishlistEntry.objects.filter(user=request.user, card_id=card_id).first()
    if existing:
        existing.delete()
        return Response({"wishlisted": False}, status=status.HTTP_200_OK)

    entry = WishlistEntry.objects.create(
        user=request.user, card_id=card_id,
        desired_quantity=int(request.data.get("desired_quantity", 1) or 1),
    )
    entry = WishlistEntry.objects.select_related(
        "card__edition", "card__rarity", "card__race", "card__card_type"
    ).get(pk=entry.pk)
    return Response(
        {"wishlisted": True, "entry": WishlistEntrySerializer(entry).data},
        status=status.HTTP_200_OK,
    )


@api_view(["PATCH"])
@permission_classes([permissions.IsAuthenticated])
def wishlist_update(request, card_id):
    try:
        entry = WishlistEntry.objects.get(user=request.user, card_id=card_id)
    except WishlistEntry.DoesNotExist:
        return Response({"detail": "Entrada no encontrada."}, status=status.HTTP_404_NOT_FOUND)

    desired = request.data.get("desired_quantity")
    if desired is not None:
        entry.desired_quantity = max(1, int(desired))
        entry.save()

    entry = WishlistEntry.objects.select_related(
        "card__edition", "card__rarity", "card__race", "card__card_type"
    ).get(pk=entry.pk)
    return Response(WishlistEntrySerializer(entry).data)


# ── Bulk IDs ────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def my_ids(request):
    collection = dict(
        CollectionEntry.objects.filter(user=request.user).values_list("card_id", "quantity")
    )
    wishlist = list(
        WishlistEntry.objects.filter(user=request.user).values_list("card_id", flat=True)
    )
    return Response({"collection": collection, "wishlist": wishlist})


# ── Batch upsert ─────────────────────────────────────────

@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def collection_batch_upsert(request):
    items = request.data if isinstance(request.data, list) else []
    if not items:
        return Response({"detail": "Se esperaba una lista de cambios."}, status=status.HTTP_400_BAD_REQUEST)

    profile, permissions_payload, _ = _resolve_workspace(request, required_permission="view_collection")

    updated = 0
    for item in items:
        card_id = item.get("card")
        if not card_id:
            continue
        entry = CollectionEntry.objects.filter(user=profile.user, card_id=card_id).first()
        created = entry is None
        if created:
            _enforce_entry_permissions(item, permissions_payload, entry=None, created=True)
            entry = CollectionEntry.objects.create(
                user=profile.user, card_id=card_id,
                quantity=int(item.get("quantity", 1) or 1),
            )
        else:
            _enforce_entry_permissions(item, permissions_payload, entry=entry, created=False)
        _apply_collection_fields(entry, item)
        entry.save()
        updated += 1
    return Response({"updated": updated})


# ── Bulk import (texto) ──────────────────────────────────

LINE_RE = re.compile(r"^\s*(?:(\d+)\s*[xX]?\s+)?(.+?)\s*$")


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def collection_bulk_import(request):
    """
    Importa cartas desde texto plano. Cada línea: "2 Nombre" o "2x Nombre" o "Nombre".
    Body: {"text": "...", "mode": "add"|"set"}
    """
    from cards.models import Card

    text = (request.data.get("text") or "").strip()
    mode = request.data.get("mode") or "add"
    if not text:
        return Response({"detail": "Sin texto."}, status=status.HTTP_400_BAD_REQUEST)

    added = updated = ambiguous = not_found = 0
    not_found_lines = []
    ambiguous_lines = []

    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("//"):
            continue
        m = LINE_RE.match(line)
        if not m:
            continue
        qty = int(m.group(1) or 1)
        name = m.group(2).strip()
        if not name:
            continue
        matches = list(
            Card.objects.filter(name__iexact=name).values_list("id", "name")
        )
        if len(matches) == 0:
            matches = list(
                Card.objects.filter(name__icontains=name).values_list("id", "name")[:5]
            )
            if len(matches) == 0:
                not_found += 1
                not_found_lines.append(line)
                continue
            if len(matches) > 1:
                ambiguous += 1
                ambiguous_lines.append({"line": line, "matches": [n for _, n in matches]})
                continue
        card_id = matches[0][0]
        entry, created = CollectionEntry.objects.get_or_create(
            user=request.user, card_id=card_id, defaults={"quantity": qty}
        )
        if created:
            added += 1
        else:
            entry.quantity = qty if mode == "set" else entry.quantity + qty
            entry.save()
            updated += 1

    return Response({
        "added": added, "updated": updated,
        "not_found": not_found, "ambiguous": ambiguous,
        "not_found_lines": not_found_lines[:20],
        "ambiguous_lines": ambiguous_lines[:20],
    })


# ── Public Store (Tienda) ────────────────────────────────

def _resolve_public_profile(token_or_slug):
    """Resuelve por slug si no es UUID, sino por share_token."""
    try:
        token = uuid.UUID(str(token_or_slug))
        return get_object_or_404(BinderProfile, share_token=token)
    except (ValueError, AttributeError):
        return get_object_or_404(
            BinderProfile, store_slug=str(token_or_slug).lower(), is_store_public=True
        )


def _filter_store_qs(qs, params):
    entry_ids_raw = (params.get("entry_ids") or "").strip()
    if entry_ids_raw:
        entry_ids = []
        for chunk in entry_ids_raw.split(","):
            chunk = chunk.strip()
            if not chunk:
                continue
            try:
                value = int(chunk)
            except ValueError:
                continue
            if value > 0:
                entry_ids.append(value)
        entry_ids = list(dict.fromkeys(entry_ids))
        if entry_ids:
            qs = qs.filter(id__in=entry_ids)
        else:
            return qs.none()

    search = params.get("search")
    if search:
        qs = qs.filter(card__name__icontains=search)
    fmt = params.get("fmt")
    if fmt:
        codes = [c for c in fmt.split(",") if c]
        if codes:
            # Soporte para "esc" virtual (lista fija de slugs).
            ESC_EDITION_SLUGS = [
                "bushido", "sol-naciente",
                "dominio", "contraataque", "aguila-imperial", "axis-mundi",
                "hijos-del-sol", "legado-gotico", "escuelas_elementales",
                "steampunk", "heroes_de_dharma",
            ]
            q = Q()
            for code in codes:
                if code == "esc":
                    q |= Q(card__edition__slug__in=ESC_EDITION_SLUGS)
                else:
                    q |= Q(card__edition__format__code=code)
            qs = qs.filter(q)
    edition = params.get("edition")
    if edition:
        qs = qs.filter(card__edition__slug=edition)
    race = params.get("race")
    if race:
        qs = qs.filter(card__race__slug=race)
    rarity = params.get("rarity")
    if rarity:
        qs = qs.filter(card__rarity__slug=rarity)
    ctype = params.get("type")
    if ctype:
        qs = qs.filter(card__card_type__slug=ctype)
    cond = params.get("condition")
    if cond:
        qs = qs.filter(condition=cond)
    foil = params.get("foil")
    if foil == "1":
        qs = qs.filter(is_foil=True)
    elif foil == "0":
        qs = qs.filter(is_foil=False)
    pmin = params.get("price_min")
    if pmin:
        try:
            qs = qs.filter(price__gte=int(pmin))
        except ValueError:
            pass
    pmax = params.get("price_max")
    if pmax:
        try:
            qs = qs.filter(price__lte=int(pmax))
        except ValueError:
            pass
    if params.get("only_priced") == "1":
        qs = qs.filter(price__isnull=False)
    ordering = params.get("ordering") or "-id"
    allowed = {"price", "-price", "card__name", "-card__name", "id", "-id"}
    if ordering in allowed:
        qs = qs.order_by(ordering)
    return qs


def _public_profile_payload(profile, request):
    """Devuelve dict con perfil + flags has_store y has_wishlist (para tabs)."""
    sel_count = CollectionEntry.objects.filter(
        user=profile.user, selling_quantity__gt=0,
    ).count()
    wish_count = WishlistEntry.objects.filter(user=profile.user).count()
    profile.selling_count = sel_count
    data = PublicBinderProfileSerializer(profile, context={"request": request}).data
    data["has_store"] = bool(profile.is_store_public and sel_count > 0)
    data["has_wishlist"] = wish_count > 0
    data["wishlist_count"] = wish_count
    return data


class PublicWishlistListView(generics.ListAPIView):
    """Wishlist pública resolvida por share_token (UUID) o slug si la tienda es pública."""
    serializer_class = WishlistEntrySerializer
    pagination_class = CarpetaPagination
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        profile = _resolve_public_profile(self.kwargs["token"])
        self._profile = profile
        qs = WishlistEntry.objects.filter(user=profile.user).select_related(
            "card__edition", "card__rarity", "card__race", "card__card_type",
        )
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(card__name__icontains=search)
        edition = self.request.query_params.get("edition")
        if edition:
            qs = qs.filter(card__edition__slug=edition)
        ordering = self.request.query_params.get("ordering") or "-id"
        allowed = {"card__name", "-card__name", "id", "-id"}
        if ordering in allowed:
            qs = qs.order_by(ordering)
        return qs

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        response.data["store"] = _public_profile_payload(self._profile, request)
        return response


class PublicStoreListView(generics.ListAPIView):
    serializer_class = CollectionEntrySerializer
    pagination_class = CarpetaPagination
    permission_classes = [permissions.AllowAny]

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        if self.request.user.is_authenticated:
            ctx["viewer_wishlist_ids"] = set(
                WishlistEntry.objects.filter(user=self.request.user).values_list("card_id", flat=True)
            )
        return ctx

    def get_queryset(self):
        profile = _resolve_public_profile(self.kwargs["token"])
        self._profile = profile
        qs = CollectionEntry.objects.filter(
            user=profile.user, selling_quantity__gt=0
        ).select_related(
            "card__edition", "card__rarity", "card__race", "card__card_type"
        )
        return _filter_store_qs(qs, self.request.query_params)

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        profile = self._profile
        # Inyectar info de la tienda
        sel_count = CollectionEntry.objects.filter(
            user=profile.user, selling_quantity__gt=0
        ).count()
        profile.selling_count = sel_count
        response.data["store"] = _public_profile_payload(profile, request)
        # Compatibilidad legacy
        response.data["store_owner"] = profile.user.username
        response.data["store_avatar"] = response.data["store"]["user_avatar_url"]
        response.data["store_binder_avatar"] = response.data["store"]["binder_avatar_url"]
        return response


class PublicStoreIndexView(generics.ListAPIView):
    """Listado público de tiendas (is_store_public=True con al menos 1 carta en venta)."""
    serializer_class = PublicBinderProfileSerializer
    pagination_class = CarpetaPagination
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = (
            BinderProfile.objects.filter(is_store_public=True)
            .annotate(
                selling_count=Count(
                    "user__collection_entries",
                    filter=Q(user__collection_entries__selling_quantity__gt=0),
                )
            )
            .filter(selling_count__gt=0)
            .select_related("user")
        )
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(
                Q(user__username__icontains=search)
                | Q(display_name__icontains=search)
                | Q(city__icontains=search)
            )
        country = self.request.query_params.get("country")
        if country:
            qs = qs.filter(country=country)
        ordering = self.request.query_params.get("ordering") or "-last_active"
        allowed = {"-last_active", "last_active", "-selling_count", "selling_count", "user__username"}
        if ordering in allowed:
            qs = qs.order_by(ordering)
        return qs


def _create_store_order(profile, buyer_user, payload):
    items = payload.get("items") or []
    if not items:
        raise ValueError("Debes enviar al menos una carta en el pedido.")

    requested_by_entry = {}
    for row in items:
        entry_id = int(row["entry_id"])
        qty = int(row["quantity"])
        requested_by_entry[entry_id] = requested_by_entry.get(entry_id, 0) + qty

    entry_ids = list(requested_by_entry.keys())
    with transaction.atomic():
        entries_qs = (
            CollectionEntry.objects.select_for_update()
            .filter(user=profile.user, id__in=entry_ids)
            .select_related("card")
        )
        entry_map = {e.id: e for e in entries_qs}

        missing_ids = [eid for eid in entry_ids if eid not in entry_map]
        if missing_ids:
            raise ValueError("Algunas cartas ya no estan disponibles en la tienda.")

        for entry_id, qty in requested_by_entry.items():
            entry = entry_map[entry_id]
            if entry.selling_quantity <= 0:
                raise ValueError(f"{entry.card.name} ya no esta disponible.")
            if qty > entry.selling_quantity:
                raise ValueError(
                    f"Stock insuficiente para {entry.card.name}: pediste {qty}, disponible {entry.selling_quantity}."
                )

        buyer_name = (str(payload.get("buyer_name") or "").strip())[:100]
        buyer_whatsapp = (str(payload.get("buyer_whatsapp") or "").strip())[:30]
        buyer_note = (str(payload.get("buyer_note") or "").strip())[:800]

        if not buyer_name and buyer_user is not None:
            buyer_name = buyer_user.username

        order = StoreOrder.objects.create(
            store_profile=profile,
            buyer_user=buyer_user,
            buyer_name=buyer_name,
            buyer_whatsapp=buyer_whatsapp,
            buyer_note=buyer_note,
            status=StoreOrder.STATUS_PENDING,
        )

        total_estimated = 0
        has_priced_items = False

        for entry_id, qty in requested_by_entry.items():
            entry = entry_map[entry_id]
            unit_price = entry.price
            line_total = unit_price * qty if unit_price is not None else None

            StoreOrderItem.objects.create(
                order=order,
                collection_entry=entry,
                card=entry.card,
                quantity=qty,
                unit_price=unit_price,
                line_total=line_total,
                card_name=entry.card.name,
                card_edid=entry.card.edid,
                language=entry.language,
                is_foil=entry.is_foil,
            )

            # Reserva de stock: sale de "en venta" y queda asignado al pedido.
            entry.selling_quantity = max(0, entry.selling_quantity - qty)
            entry.save(update_fields=["selling_quantity"])

            if line_total is not None:
                total_estimated += line_total
                has_priced_items = True

        if has_priced_items:
            order.total_estimated = total_estimated
            order.save(update_fields=["total_estimated"])

    total_items = sum(requested_by_entry.values())
    buyer_label = order.buyer_name or (buyer_user.username if buyer_user is not None else "Comprador")
    try:
        Notification.objects.create(
            user=profile.user,
            notif_type="general",
            message=f"Nuevo pedido MYL de {buyer_label} ({total_items} cartas)",
            link="/carpeta?tab=pedidos",
        )
    except Exception:
        pass

    return (
        StoreOrder.objects.select_related("store_profile", "store_profile__user", "buyer_user")
        .prefetch_related("items", "items__card")
        .get(pk=order.pk)
    )


class PublicStoreOrderCreateView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = StoreOrderCreateSerializer

    def post(self, request, *args, **kwargs):
        profile = _resolve_public_profile(self.kwargs["token"])
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        buyer_user = request.user if request.user.is_authenticated else None
        try:
            order = _create_store_order(profile, buyer_user, serializer.validated_data)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            StoreOrderSerializer(order, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class MyStoreOrderListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = StoreOrderSerializer

    def get_queryset(self):
        profile, permissions_payload, _ = _resolve_workspace(self.request)
        qs = (
            StoreOrder.objects.filter(store_profile=profile)
            .select_related("store_profile", "store_profile__user", "buyer_user")
            .prefetch_related("items", "items__card")
        )
        status_filter = (self.request.query_params.get("status") or "").strip().lower()
        allowed = {
            StoreOrder.STATUS_PENDING,
            StoreOrder.STATUS_ACCEPTED,
            StoreOrder.STATUS_CANCELLED,
        }

        def _can_view_status(status_value):
            if status_value == StoreOrder.STATUS_PENDING:
                return _can_permissions(permissions_payload, "view_orders")
            return _can_permissions(permissions_payload, "view_history")

        if status_filter == "history":
            if not _can_permissions(permissions_payload, "view_history"):
                raise PermissionDenied("No tienes permiso para ver el historial de pedidos")
            return qs.filter(status__in=[StoreOrder.STATUS_ACCEPTED, StoreOrder.STATUS_CANCELLED])
        if status_filter in allowed:
            if not _can_view_status(status_filter):
                raise PermissionDenied("No tienes permiso para ver ese estado de pedidos")
            qs = qs.filter(status=status_filter)
        else:
            status_q = Q()
            if _can_permissions(permissions_payload, "view_orders"):
                status_q |= Q(status=StoreOrder.STATUS_PENDING)
            if _can_permissions(permissions_payload, "view_history"):
                status_q |= Q(status__in=[StoreOrder.STATUS_ACCEPTED, StoreOrder.STATUS_CANCELLED])
            if not status_q:
                raise PermissionDenied("No tienes permiso para ver pedidos de esta tienda")
            qs = qs.filter(status_q)
        return qs


class MyPurchaseOrderListView(generics.ListAPIView):
    """Pedidos que el usuario autenticado hizo como COMPRADOR, en cualquier tienda."""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = StoreOrderSerializer

    def get_queryset(self):
        qs = (
            StoreOrder.objects.filter(buyer_user=self.request.user)
            .select_related("store_profile", "store_profile__user", "buyer_user")
            .prefetch_related("items", "items__card")
            .order_by("-created_at")
        )
        store_token = (self.request.query_params.get("store") or "").strip()
        if store_token:
            try:
                profile = _resolve_public_profile(store_token)
            except Http404:
                return qs.none()
            qs = qs.filter(store_profile=profile)
        status_filter = (self.request.query_params.get("status") or "").strip().lower()
        allowed = {
            StoreOrder.STATUS_PENDING,
            StoreOrder.STATUS_ACCEPTED,
            StoreOrder.STATUS_CANCELLED,
        }
        if status_filter in allowed:
            qs = qs.filter(status=status_filter)
        return qs


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def my_order_assignments(request):
    profile, permissions_payload, _ = _resolve_workspace(request)
    if not _can_permissions(permissions_payload, "view_orders"):
        raise PermissionDenied("No tienes permiso para ver pedidos pendientes")

    rows = (
        StoreOrderItem.objects.filter(
            order__store_profile=profile,
            order__status=StoreOrder.STATUS_PENDING,
            collection_entry__isnull=False,
        )
        .values("collection_entry_id")
        .annotate(assigned=Sum("quantity"))
    )
    return Response({
        "assigned_by_entry": {
            int(row["collection_entry_id"]): int(row["assigned"] or 0)
            for row in rows
            if row["collection_entry_id"] is not None
        }
    })


def _update_order_status(request, order_id, new_status):
    if new_status not in {StoreOrder.STATUS_ACCEPTED, StoreOrder.STATUS_CANCELLED}:
        return Response({"detail": "Estado invalido."}, status=status.HTTP_400_BAD_REQUEST)

    required_permission = "accept_orders" if new_status == StoreOrder.STATUS_ACCEPTED else "reject_orders"

    with transaction.atomic():
        try:
            order = (
                StoreOrder.objects.select_for_update()
                .select_related("store_profile", "store_profile__user", "buyer_user")
                .prefetch_related("items")
                .get(pk=order_id)
            )
        except StoreOrder.DoesNotExist:
            return Response({"detail": "Pedido no encontrado."}, status=status.HTTP_404_NOT_FOUND)

        permissions_payload = _permissions_payload_for_user(order.store_profile, request.user)
        if permissions_payload is None:
            return Response({"detail": "Pedido no encontrado."}, status=status.HTTP_404_NOT_FOUND)
        if not _can_permissions(permissions_payload, required_permission):
            return Response({"detail": "No tienes permiso para gestionar este pedido."}, status=status.HTTP_403_FORBIDDEN)

        if order.status != StoreOrder.STATUS_PENDING:
            return Response({"detail": "Solo puedes gestionar pedidos pendientes."}, status=status.HTTP_400_BAD_REQUEST)

        items = list(order.items.all())
        entry_ids = [it.collection_entry_id for it in items if it.collection_entry_id]
        entry_map = {}
        if entry_ids:
            entry_map = {
                e.id: e
                for e in CollectionEntry.objects.select_for_update().filter(
                    id__in=entry_ids,
                    user_id=order.store_profile.user_id,
                )
            }

        for item in items:
            if not item.collection_entry_id:
                continue
            entry = entry_map.get(item.collection_entry_id)
            if not entry:
                continue

            qty = max(0, int(item.quantity or 0))
            if new_status == StoreOrder.STATUS_CANCELLED:
                # Devuelve la reserva al stock visible en tienda.
                entry.selling_quantity = min(entry.quantity, entry.selling_quantity + qty)
                entry.save(update_fields=["selling_quantity"])
            else:
                # Consolida venta: baja stock real y limpia exceso en venta.
                entry.quantity = max(0, entry.quantity - qty)
                if entry.selling_quantity > entry.quantity:
                    entry.selling_quantity = entry.quantity
                entry.save(update_fields=["quantity", "selling_quantity"])

        order.status = new_status
        order.responded_at = timezone.now()
        order.seller_note = str((request.data or {}).get("seller_note") or "").strip()[:800]
        order.save(update_fields=["status", "responded_at", "seller_note", "updated_at"])

    try:
        if order.buyer_user_id:
            msg = "Tu pedido MYL fue aceptado." if new_status == StoreOrder.STATUS_ACCEPTED else "Tu pedido MYL fue cancelado."
            Notification.objects.create(
                user=order.buyer_user,
                notif_type="general",
                message=msg,
                link=f"/mis-compras?game=myl&store={order.store_profile.share_token}",
            )
    except Exception:
        pass

    payload = (
        StoreOrder.objects.select_related("store_profile", "store_profile__user", "buyer_user")
        .prefetch_related("items", "items__card")
        .get(pk=order.pk)
    )
    return Response(StoreOrderSerializer(payload, context={"request": request}).data)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def accept_store_order(request, order_id):
    return _update_order_status(request, order_id, StoreOrder.STATUS_ACCEPTED)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def cancel_store_order(request, order_id):
    return _update_order_status(request, order_id, StoreOrder.STATUS_CANCELLED)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def my_share_token(request):
    profile, _ = BinderProfile.objects.get_or_create(user=request.user)
    return Response({
        "share_token": str(profile.share_token),
        "store_slug": profile.store_slug,
        "is_store_public": profile.is_store_public,
    })


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def collection_stats(request):
    from cards.models import Edition, Race, Rarity, Card

    entries = CollectionEntry.objects.filter(user=request.user)

    total_cards = entries.aggregate(t=Sum("quantity"))["t"] or 0
    unique_cards = entries.count()
    total_value = entries.aggregate(v=Sum("price"))["v"] or 0

    by_edition = list(
        entries.annotate(_ed_name=F("card__edition__title"))
        .values("_ed_name")
        .annotate(count=Sum("quantity"))
        .order_by("-count")[:15]
    )
    by_edition = [{"card__edition__name": x["_ed_name"], "count": x["count"]} for x in by_edition]
    by_rarity = list(
        entries.values("card__rarity__name")
        .annotate(count=Sum("quantity"))
        .order_by("-count")
    )
    by_race = list(
        entries.values("card__race__name")
        .annotate(count=Sum("quantity"))
        .order_by("-count")[:15]
    )
    by_type = list(
        entries.values("card__card_type__name")
        .annotate(count=Sum("quantity"))
        .order_by("-count")
    )
    edition_completeness = []
    top_editions = entries.annotate(_ed_name=F("card__edition__title")).values("card__edition_id", "_ed_name").annotate(
        owned=Count("card_id", distinct=True)
    ).order_by("-owned")[:5]
    for ed in top_editions:
        total_in_ed = Card.objects.filter(edition_id=ed["card__edition_id"]).count()
        edition_completeness.append({
            "edition": ed["_ed_name"],
            "owned": ed["owned"],
            "total": total_in_ed,
            "pct": round(ed["owned"] / total_in_ed * 100, 1) if total_in_ed else 0,
        })

    return Response({
        "total_cards": total_cards,
        "unique_cards": unique_cards,
        "total_value": total_value,
        "by_edition": by_edition,
        "by_rarity": by_rarity,
        "by_race": by_race,
        "by_type": by_type,
        "edition_completeness": edition_completeness,
    })


# ── Guía interactiva (tours) ─────────────────────────────

@api_view(["GET", "POST"])
@permission_classes([permissions.IsAuthenticated])
def carpeta_tours(request):
    """GET: tours completados por el usuario. POST {tour_id}: marca uno como completado."""
    if request.method == "POST":
        tour_id = str((request.data or {}).get("tour_id") or "").strip()[:64]
        if not tour_id:
            return Response({"detail": "tour_id requerido"}, status=status.HTTP_400_BAD_REQUEST)
        CarpetaTourProgress.objects.get_or_create(user=request.user, tour_id=tour_id)

    completed = list(
        CarpetaTourProgress.objects
        .filter(user=request.user)
        .values_list("tour_id", flat=True)
    )
    return Response({"completed": completed})
