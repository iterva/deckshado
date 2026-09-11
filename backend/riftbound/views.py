import os

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q, Count, Sum
from django.http import Http404
from django.utils import timezone
from rest_framework import viewsets, permissions, status, filters, generics
from rest_framework.decorators import action, api_view, permission_classes, parser_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly
from backend.cdn_image_upload import upload_image_to_cdn, CdnImageUploadError

from .tcgplayer import get_tcg_price, get_tcg_prices_batch
from .tcgmatch import get_tcgmatch_price

from .models import (
    RiftboundCard, RiftboundSet, RiftboundFormat, RiftboundBanlistEntry,
    RiftboundDeck, RiftboundCollectionEntry, RiftboundWishlistEntry, RiftboundIcon,
    RiftboundBinderProfile, RiftboundStoreOrder, RiftboundStoreOrderItem, RiftboundStorePermission,
)
from .serializers import (
    RiftboundCardSerializer, RiftboundCardLiteSerializer,
    RiftboundSetSerializer, RiftboundFormatSerializer,
    RiftboundBanlistEntrySerializer, RiftboundDeckSerializer,
    RiftboundCollectionEntrySerializer, RiftboundWishlistEntrySerializer,
    RiftboundIconSerializer,
    RiftboundBinderProfileSerializer, RiftboundPublicBinderProfileSerializer,
    RiftboundStoreOrderSerializer, RiftboundStoreOrderCreateSerializer, RiftboundStorePermissionSerializer,
)
from .integrations.riftcodex import RiftcodexClient, map_card_type, map_card_rarity, normalize_riftbound_card_number
from users.models import Notification


class RiftboundCardViewSet(viewsets.ReadOnlyModelViewSet):
    """Catálogo público de cartas Riftbound, con filtros y búsqueda."""
    queryset = (
        RiftboundCard.objects.filter(is_active=True).select_related("set").order_by("card_number")
    )
    permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "card_number", "description"]
    ordering_fields = ["card_number", "name", "energy", "power", "might"]
    serializer_class = RiftboundCardSerializer
    lookup_field = "card_number"

    def _remote_cards_enabled(self) -> bool:
        source = (self.request.query_params.get("source") or os.environ.get("RIFTBOUND_CARDS_SOURCE") or "local").strip().lower()
        return source in {"riftcodex", "remote", "api"}

    def _page_size(self) -> int:
        raw = self.request.query_params.get("page_size") or "20"
        try:
            size = int(raw)
        except ValueError:
            size = 20
        return max(1, min(250, size))

    def _page_number(self) -> int:
        raw = self.request.query_params.get("page") or "1"
        try:
            page = int(raw)
        except ValueError:
            page = 1
        return max(1, page)

    def _build_page_url(self, page: int | None) -> str | None:
        if page is None:
            return None
        query = self.request.query_params.copy()
        query["page"] = str(page)
        return f"{self.request.build_absolute_uri(self.request.path)}?{query.urlencode()}"

    def _apply_remote_filters(self, rows: list[dict]) -> list[dict]:
        params = self.request.query_params
        out = list(rows)

        ctype = (params.get("type") or "").strip().lower()
        if ctype:
            if ctype == "champion":
                out = [
                    r for r in out
                    if (r.get("card_type") == "unit")
                    and ("," in (r.get("name") or ""))
                    and (r.get("name") or "").split(",")[0].strip() in (r.get("subtypes") or [])
                ]
            else:
                out = [r for r in out if (r.get("card_type") or "") == ctype]

        rarity = (params.get("rarity") or "").strip().lower()
        if rarity:
            out = [r for r in out if (r.get("rarity") or "") == rarity]

        energy_raw = params.get("energy")
        if energy_raw not in (None, ""):
            try:
                energy = int(energy_raw)
                out = [r for r in out if r.get("energy") == energy]
            except ValueError:
                pass

        sub = (params.get("subtype") or "").strip().lower()
        if sub:
            out = [
                r for r in out
                if any((s or "").lower() == sub for s in (r.get("subtypes") or []))
            ]

        exclude_bg = params.get("exclude_battlefields") in ("1", "true", "True")
        colors = (params.get("colors") or "").strip()
        if colors:
            color_set = {c.strip().lower() for c in colors.split(",") if c.strip()}
            out = [
                r for r in out
                if ((r.get("card_type") == "battlefield") and not exclude_bg)
                or any((c or "").lower() in color_set for c in (r.get("colors") or []))
            ]
        elif exclude_bg:
            out = [r for r in out if r.get("card_type") != "battlefield"]

        return out

    def _card_number_to_riftbound_query(self, card_number: str) -> str:
        value = (card_number or "").strip().upper()
        if not value:
            return ""
        if "-" not in value:
            return value.lower()
        set_code, number = value.split("-", 1)
        number = number.rstrip("*")
        return f"{set_code.lower()}-{number.lower()}"

    def _map_remote_item(self, item: dict, local_map: dict, lite: bool = False):
        meta = item.get("metadata") or {}
        attrs = item.get("attributes") or {}
        text = item.get("text") or {}
        media = item.get("media") or {}
        classification = item.get("classification") or {}
        set_data = item.get("set") or {}

        card_number = normalize_riftbound_card_number(
            item.get("riftbound_id") or "",
            signature=bool(meta.get("signature")),
        )
        if not card_number:
            return None

        local_card = local_map.get(card_number)
        if not local_card:
            # Keep DB-backed flows (builder/collection/decks) safe by avoiding orphan IDs.
            return None

        color_values = [str(c).lower() for c in (classification.get("domain") or []) if c]
        card_type = map_card_type(classification.get("type"))
        rarity = map_card_rarity(classification.get("rarity"))
        image_url = media.get("image_url") or local_card.image_url or local_card.image_url_small or ""
        cdn_image_url = local_card.cdn_image_url or ""
        image = cdn_image_url or image_url or local_card.image_url_small or ""

        if lite:
            return {
                "id": local_card.id,
                "card_number": card_number,
                "name": item.get("name") or local_card.name,
                "card_type": card_type,
                "rarity": rarity,
                "colors": color_values,
                "energy": attrs.get("energy"),
                "power": attrs.get("power"),
                "might": attrs.get("might"),
                "image": image,
                "image_url": image_url,
                "image_url_small": local_card.image_url_small or "",
                "cdn_image_url": cdn_image_url,
                "description": text.get("plain") or local_card.description or "",
                "subtypes": local_card.subtypes or [],
            }

        set_payload = None
        if local_card.set:
            set_payload = {
                "id": local_card.set.id,
                "code": local_card.set.code,
                "name": local_card.set.name,
                "release_date": local_card.set.release_date.isoformat() if local_card.set.release_date else None,
            }
        elif set_data:
            set_payload = {
                "id": None,
                "code": (set_data.get("set_id") or "").upper() or None,
                "name": set_data.get("label") or "",
                "release_date": None,
            }

        return {
            "id": local_card.id,
            "card_number": card_number,
            "external_id": str(item.get("id") or local_card.external_id),
            "name": item.get("name") or local_card.name,
            "slug": local_card.slug,
            "set": set_payload,
            "card_type": card_type,
            "supertype": classification.get("supertype") or "",
            "subtypes": local_card.subtypes or [],
            "rarity": rarity,
            "variant": "Alt Art" if meta.get("alternate_art") else (local_card.variant or ""),
            "colors": color_values,
            "energy": attrs.get("energy"),
            "power": attrs.get("power"),
            "might": attrs.get("might"),
            "description": text.get("plain") or local_card.description or "",
            "flavor": text.get("flavour") or local_card.flavor or "",
            "image_url": image_url,
            "image_url_small": local_card.image_url_small or "",
            "cdn_image_url": cdn_image_url,
            "image": image,
            "is_active": bool(local_card.is_active),
        }

    def list(self, request, *args, **kwargs):
        if not self._remote_cards_enabled():
            return super().list(request, *args, **kwargs)

        client = RiftcodexClient()
        page = self._page_number()
        size = self._page_size()

        try:
            name_search = (request.query_params.get("name_search") or "").strip()
            ability_search = (request.query_params.get("ability_search") or "").strip()
            generic_search = (request.query_params.get("search") or "").strip()
            set_code = (request.query_params.get("set") or "").strip().upper() or None

            remote_items: list[dict]
            total = 0
            pages = 1
            if name_search:
                remote_items = client.search_cards_by_name(fuzzy=name_search, set_id=set_code, size=size, page=page)
                total = len(remote_items)
            elif ability_search:
                remote_items = client.search_cards(query=ability_search, set_id=set_code, size=size, page=page)
                total = len(remote_items)
            elif generic_search:
                remote_items = client.search_cards_by_name(fuzzy=generic_search, set_id=set_code, size=size, page=page)
                if not remote_items:
                    remote_items = client.search_cards(query=generic_search, set_id=set_code, size=size, page=page)
                total = len(remote_items)
            else:
                remote_page = client.fetch_cards_page(page=page, size=size)
                remote_items = remote_page.items
                total = remote_page.total
                pages = remote_page.pages

            card_numbers = []
            for item in remote_items:
                meta = item.get("metadata") or {}
                cn = normalize_riftbound_card_number(item.get("riftbound_id") or "", signature=bool(meta.get("signature")))
                if cn:
                    card_numbers.append(cn)

            local_cards = RiftboundCard.objects.filter(card_number__in=card_numbers).select_related("set")
            local_map = {c.card_number: c for c in local_cards}

            lite = request.query_params.get("lite") == "1"
            mapped = []
            for item in remote_items:
                payload = self._map_remote_item(item, local_map, lite=lite)
                if payload:
                    mapped.append(payload)

            mapped = self._apply_remote_filters(mapped)

            if total and pages > 1:
                next_page = page + 1 if page < pages else None
                prev_page = page - 1 if page > 1 else None
                return Response(
                    {
                        "count": total,
                        "next": self._build_page_url(next_page),
                        "previous": self._build_page_url(prev_page),
                        "results": mapped,
                    }
                )

            return Response(
                {
                    "count": len(mapped),
                    "next": None,
                    "previous": None,
                    "results": mapped,
                }
            )
        except Exception:
            # Safe fallback: keep app usable if external API is unavailable.
            return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        if not self._remote_cards_enabled():
            return super().retrieve(request, *args, **kwargs)

        card_number = (kwargs.get(self.lookup_field) or "").strip().upper()
        if not card_number:
            return super().retrieve(request, *args, **kwargs)

        local_card = RiftboundCard.objects.filter(card_number=card_number).select_related("set").first()
        if not local_card:
            return super().retrieve(request, *args, **kwargs)

        client = RiftcodexClient()
        try:
            items = client.fetch_cards_by_riftbound_id(self._card_number_to_riftbound_query(card_number))
            local_map = {local_card.card_number: local_card}
            for item in items:
                meta = item.get("metadata") or {}
                cn = normalize_riftbound_card_number(item.get("riftbound_id") or "", signature=bool(meta.get("signature")))
                if cn == card_number:
                    payload = self._map_remote_item(item, local_map, lite=False)
                    if payload:
                        return Response(payload)
        except Exception:
            pass

        return super().retrieve(request, *args, **kwargs)

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params

        # Búsquedas dirigidas (no usan SearchFilter):
        # ?name_search=foo  → solo nombre / número
        # ?ability_search=foo  → solo descripción / texto de habilidad
        if (ns := (params.get("name_search") or "").strip()):
            qs = qs.filter(Q(name__icontains=ns) | Q(card_number__icontains=ns))
        if (asx := (params.get("ability_search") or "").strip()):
            qs = qs.filter(description__icontains=asx)

        if (set_code := params.get("set")):
            qs = qs.filter(set__code__iexact=set_code)

        if (ctype := params.get("type")):
            if ctype == "champion":
                # Champion-units: card_type=unit cuyo nombre "X, Titulo" tiene X en subtypes.
                qs = qs.filter(card_type="unit", name__contains=", ")
            else:
                qs = qs.filter(card_type=ctype)

        if (rarity := params.get("rarity")):
            qs = qs.filter(rarity=rarity)

        # ?colors=fury,calm  (cualquiera). En SQLite el lookup `__contains` sobre
        # JSONField no esta soportado; filtramos en Python.
        color_list: list[str] = []
        if (colors := params.get("colors")):
            color_list = [c.strip() for c in colors.split(",") if c.strip()]

        for field in ("energy", "power", "might"):
            v = params.get(field)
            if v not in (None, ""):
                try:
                    qs = qs.filter(**{field: int(v)})
                except ValueError:
                    pass

        # Filtro champion: requiere comprobar nombre vs subtypes en Python (JSONField)
        if params.get("type") == "champion":
            ids = [pk for pk, name, subs in qs.values_list("id", "name", "subtypes")
                   if name and "," in name
                   and name.split(",")[0].strip() in (subs or [])]
            qs = qs.filter(id__in=ids)

        # Filtro de colores en Python (compatible con SQLite). OR entre colores.
        # Los battlefields se incluyen siempre (son cartas neutrales necesarias
        # en cualquier mazo, independientemente de los colores elegidos).
        # Excepcion: ?exclude_battlefields=1 fuerza a excluirlos del listado.
        exclude_bg = params.get("exclude_battlefields") in ("1", "true", "True")
        if color_list:
            color_set = set(color_list)
            ids = [pk for pk, cs, ct in qs.values_list("id", "colors", "card_type")
                   if (ct == "battlefield" and not exclude_bg)
                   or (cs and any(c in color_set for c in cs))]
            qs = qs.filter(id__in=ids)
        elif exclude_bg:
            qs = qs.exclude(card_type="battlefield")

        # ?subtype=Annie  → cartas cuyo JSONField `subtypes` contiene el valor
        # (filtro en Python por compatibilidad con SQLite).
        if (sub := (params.get("subtype") or "").strip()):
            sub_l = sub.lower()
            ids = [pk for pk, subs in qs.values_list("id", "subtypes")
                   if subs and any((s or "").lower() == sub_l for s in subs)]
            qs = qs.filter(id__in=ids)

        return qs

    def get_serializer_class(self):
        if self.action == "list" and self.request.query_params.get("lite") == "1":
            return RiftboundCardLiteSerializer
        return super().get_serializer_class()


class RiftboundSetViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = RiftboundSet.objects.all().order_by("code")
    serializer_class = RiftboundSetSerializer
    permission_classes = [AllowAny]


class RiftboundFormatViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = RiftboundFormat.objects.filter(is_active=True)
    serializer_class = RiftboundFormatSerializer
    permission_classes = [AllowAny]


class RiftboundBanlistViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = (
        RiftboundBanlistEntry.objects.select_related("card", "format").order_by("status", "card__name")
    )
    serializer_class = RiftboundBanlistEntrySerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = super().get_queryset()
        # NOTA: usamos `fmt` y NO `format` porque DRF reserva ?format= para
        # negociacion de renderer (json/api).
        fmt = self.request.query_params.get("fmt") or self.request.query_params.get("format_code") or "standard"
        return qs.filter(format__code=fmt)


class RiftboundIconViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = RiftboundIcon.objects.all()
    serializer_class = RiftboundIconSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = super().get_queryset()
        if (kind := self.request.query_params.get("kind")):
            qs = qs.filter(kind=kind)
        return qs


class RiftboundDeckViewSet(viewsets.ModelViewSet):
    """CRUD de mazos Riftbound. Lectura pública para `is_public=True`."""
    serializer_class = RiftboundDeckSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "owner__username", "description"]
    ordering_fields = ["updated_at", "created_at", "name"]

    def get_queryset(self):
        user = self.request.user
        qs = RiftboundDeck.objects.select_related("owner", "format", "cover_card").prefetch_related(
            "entries__card"
        )
        if self.action == "list":
            mine = self.request.query_params.get("mine") == "1"
            if mine and user.is_authenticated:
                return qs.filter(owner=user)
            # Listado publico: solo mazos publicos (los privados solo aparecen en mine=1)
            return qs.filter(is_public=True)
        if user.is_authenticated:
            return qs.filter(Q(is_public=True) | Q(owner=user))
        return qs.filter(is_public=True)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def perform_update(self, serializer):
        if serializer.instance.owner_id != self.request.user.id:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("No puedes editar mazos ajenos.")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.owner_id != self.request.user.id:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("No puedes borrar mazos ajenos.")
        instance.delete()

    @action(detail=True, methods=["get"], permission_classes=[AllowAny])
    def validate(self, request, pk=None):
        from .validation import validate_riftbound_deck
        deck = self.get_object()
        return Response(validate_riftbound_deck(deck))


RB_OWNER_PERMISSIONS = {
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


def _rb_get_or_create_profile_for_user(user):
    profile, _ = RiftboundBinderProfile.objects.get_or_create(user=user)
    return profile


def _rb_permissions_payload_for_user(profile, user):
    if profile.user_id == user.id:
        return dict(RB_OWNER_PERMISSIONS)
    perm = RiftboundStorePermission.objects.filter(store_profile=profile, user=user).first()
    if not perm:
        return None
    return perm.permissions_dict()


def _rb_can_permissions(perm_payload, key):
    return bool((perm_payload or {}).get(key))


def _rb_store_profile_id_from_request(request):
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


def _rb_resolve_workspace(request, required_permission=None):
    requested_profile_id = _rb_store_profile_id_from_request(request)

    if requested_profile_id is None:
        profile = _rb_get_or_create_profile_for_user(request.user)
    else:
        profile = RiftboundBinderProfile.objects.filter(pk=requested_profile_id).select_related("user").first()
        if not profile:
            raise PermissionDenied("Tienda no encontrada")

    permissions_payload = _rb_permissions_payload_for_user(profile, request.user)
    if permissions_payload is None:
        raise PermissionDenied("No tienes acceso a esta tienda")

    if required_permission and not _rb_can_permissions(permissions_payload, required_permission):
        raise PermissionDenied("No tienes permiso para esta accion")

    is_owner = profile.user_id == request.user.id
    return profile, permissions_payload, is_owner


class RiftboundCollectionPagination(PageNumberPagination):
    """Permite al cliente pedir un page_size mayor (hasta 200) en la carpeta."""
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200


class RiftboundCollectionViewSet(viewsets.ModelViewSet):
    serializer_class = RiftboundCollectionEntrySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ["card__name", "card__card_number"]
    pagination_class = RiftboundCollectionPagination

    _RB_COLLECTION_FIELDS = {"quantity", "condition", "language", "is_foil", "notes"}
    _RB_MARKET_FIELDS = {"price", "selling_quantity", "photo_url", "photo_url_2"}

    def _resolve_workspace(self, required_permission="view_collection"):
        profile, permissions_payload, is_owner = _rb_resolve_workspace(self.request, required_permission=required_permission)
        return profile, permissions_payload, is_owner

    def _entry_store_profile_id(self, entry):
        return _rb_get_or_create_profile_for_user(entry.user).id

    def _ensure_entry_belongs_to_workspace(self, entry, profile):
        if self._entry_store_profile_id(entry) != profile.id:
            raise PermissionDenied("La entrada no pertenece a la tienda seleccionada")

    def _ensure_market_permission_for_selling_change(self, permissions_payload, old_selling, new_selling):
        old_value = int(old_selling or 0)
        new_value = int(new_selling or 0)
        if old_value > 0 and new_value == 0:
            if not (_rb_can_permissions(permissions_payload, "remove_from_market") or _rb_can_permissions(permissions_payload, "edit_market")):
                raise PermissionDenied("No tienes permiso para quitar cartas de la venta")
            return
        if old_value != new_value and not _rb_can_permissions(permissions_payload, "edit_market"):
            raise PermissionDenied("No tienes permiso para editar ventas/precios")

    def _enforce_entry_permissions(self, data, permissions_payload, entry=None, created=False):
        requested_fields = set(data.keys())
        requested_fields.discard("card")
        requested_fields.discard("id")
        requested_fields.discard("entry_id")
        requested_fields.discard("slot")
        requested_fields.discard("store_profile_id")

        if requested_fields & self._RB_COLLECTION_FIELDS:
            if not _rb_can_permissions(permissions_payload, "edit_collection"):
                raise PermissionDenied("No tienes permiso para editar la carpeta")

        if requested_fields & self._RB_MARKET_FIELDS:
            if "selling_quantity" in requested_fields:
                old_selling = entry.selling_quantity if entry is not None else 0
                try:
                    new_selling = int(data.get("selling_quantity") or 0)
                except (TypeError, ValueError):
                    new_selling = old_selling
                self._ensure_market_permission_for_selling_change(permissions_payload, old_selling, new_selling)

                if "price" in requested_fields and not _rb_can_permissions(permissions_payload, "edit_market"):
                    raise PermissionDenied("No tienes permiso para editar ventas/precios")
            else:
                if not _rb_can_permissions(permissions_payload, "edit_market"):
                    raise PermissionDenied("No tienes permiso para editar ventas/precios")

        if created and not _rb_can_permissions(permissions_payload, "edit_collection"):
            raise PermissionDenied("No tienes permiso para agregar cartas a la carpeta")

    def get_queryset(self):
        profile, _, _ = self._resolve_workspace(required_permission="view_collection")
        qs = (
            RiftboundCollectionEntry.objects.filter(user=profile.user)
            .select_related("card", "card__set")
        )
        if self.request.query_params.get("selling") == "1":
            qs = qs.filter(selling_quantity__gt=0)
        return qs

    def perform_create(self, serializer):
        profile, permissions_payload, _ = self._resolve_workspace(required_permission="view_collection")
        if not _rb_can_permissions(permissions_payload, "edit_collection"):
            raise PermissionDenied("No tienes permiso para agregar cartas a la carpeta")
        serializer.save(user=profile.user)

    def perform_destroy(self, instance):
        profile, permissions_payload, _ = self._resolve_workspace(required_permission="view_collection")
        self._ensure_entry_belongs_to_workspace(instance, profile)
        if not _rb_can_permissions(permissions_payload, "delete_collection"):
            raise PermissionDenied("No tienes permiso para eliminar cartas de la carpeta")
        instance.delete()

    @staticmethod
    def _coerce_bool(value):
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return False

    def _apply_fields(self, entry, data):
        if "quantity" in data:
            try:
                entry.quantity = max(0, int(data["quantity"]))
            except (TypeError, ValueError):
                pass
        if "price" in data:
            v = data["price"]
            if v in ("", None):
                entry.price = None
            else:
                try:
                    entry.price = max(0, int(v))
                except (TypeError, ValueError):
                    pass
        if "selling_quantity" in data:
            try:
                entry.selling_quantity = max(0, int(data["selling_quantity"]))
            except (TypeError, ValueError):
                pass
        if "condition" in data and data["condition"] in dict(RiftboundCollectionEntry.CONDITION_CHOICES):
            entry.condition = data["condition"]
        if "language" in data and data["language"] in dict(RiftboundCollectionEntry.LANGUAGE_CHOICES):
            entry.language = data["language"]
        if "is_foil" in data:
            entry.is_foil = self._coerce_bool(data["is_foil"])
        if "notes" in data:
            entry.notes = str(data["notes"] or "")[:200]
        if "photo_url" in data:
            entry.photo_url = str(data["photo_url"] or "")[:500]
        if "photo_url_2" in data:
            entry.photo_url_2 = str(data["photo_url_2"] or "")[:500]
        if entry.selling_quantity > entry.quantity:
            entry.selling_quantity = entry.quantity

    @staticmethod
    def _coerce_int(value):
        if value in (None, ""):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _merge_duplicate_entry(self, entry, duplicate):
        """Consolida una posible entrada duplicada dentro de `entry` y elimina la otra."""
        entry.quantity = (entry.quantity or 0) + (duplicate.quantity or 0)
        entry.selling_quantity = (entry.selling_quantity or 0) + (duplicate.selling_quantity or 0)
        if not entry.notes and duplicate.notes:
            entry.notes = duplicate.notes
        if not entry.photo_url and duplicate.photo_url:
            entry.photo_url = duplicate.photo_url
        if not entry.photo_url_2 and duplicate.photo_url_2:
            entry.photo_url_2 = duplicate.photo_url_2
        duplicate.delete()

    @action(detail=False, methods=["post"], url_path="upsert")
    @parser_classes([JSONParser, MultiPartParser, FormParser])
    def upsert(self, request):
        """Crea o actualiza una entrada; si llega `id`, actualiza esa fila exacta."""
        data = request.data.dict() if hasattr(request.data, "dict") else dict(request.data)
        profile, permissions_payload, _ = self._resolve_workspace(required_permission="view_collection")

        entry_id = self._coerce_int(data.get("id") or data.get("entry_id"))
        card_id = data.get("card")
        card = None

        file_obj = request.FILES.get("file")
        if file_obj is not None:
            slot = str(data.get("slot", "1")).strip()
            target_field = "photo_url_2" if slot == "2" else "photo_url"
            try:
                uploaded_url = upload_image_to_cdn(file_obj, folder="deckshado/riftbound/store_card_photos")
            except CdnImageUploadError as exc:
                return Response({"detail": str(exc)}, status=400)
            data[target_field] = uploaded_url

        with transaction.atomic():
            if entry_id is not None:
                entry = RiftboundCollectionEntry.objects.filter(user=profile.user, pk=entry_id).first()
                if not entry:
                    return Response({"detail": "entrada no existe"}, status=404)
                self._ensure_entry_belongs_to_workspace(entry, profile)

                if card_id:
                    try:
                        card = RiftboundCard.objects.get(pk=card_id)
                    except RiftboundCard.DoesNotExist:
                        return Response({"detail": "carta no existe"}, status=404)
                else:
                    card = entry.card

                target_is_foil = self._coerce_bool(data["is_foil"]) if "is_foil" in data else entry.is_foil
                duplicate = (
                    RiftboundCollectionEntry.objects
                    .filter(user=profile.user, card=card, is_foil=target_is_foil)
                    .exclude(pk=entry.pk)
                    .first()
                )
                if duplicate:
                    self._merge_duplicate_entry(entry, duplicate)

                entry.card = card
                entry.is_foil = target_is_foil
                created = False
            else:
                if not card_id:
                    return Response({"detail": "card requerido"}, status=400)
                try:
                    card = RiftboundCard.objects.get(pk=card_id)
                except RiftboundCard.DoesNotExist:
                    return Response({"detail": "carta no existe"}, status=404)

                is_foil = self._coerce_bool(data.get("is_foil", False))
                entry, created = RiftboundCollectionEntry.objects.get_or_create(
                    user=profile.user, card=card, is_foil=is_foil,
                    defaults={"quantity": 0},
                )

        self._enforce_entry_permissions(data, permissions_payload, entry=entry, created=created)

        if "quantity" not in data and created:
            entry.quantity = 1
        self._apply_fields(entry, data)

        if entry.quantity <= 0:
            if not _rb_can_permissions(permissions_payload, "delete_collection"):
                return Response({"detail": "No tienes permiso para eliminar cartas de la carpeta"}, status=403)
            entry.delete()
            return Response({"deleted": True, "card": card_id})

        entry.save()
        return Response(self.get_serializer(entry).data)

    @action(detail=False, methods=["post"], url_path="batch-upsert")
    def batch_upsert(self, request):
        profile, permissions_payload, _ = self._resolve_workspace(required_permission="view_collection")
        items = request.data if isinstance(request.data, list) else []
        if not items:
            return Response({"detail": "Se esperaba lista"}, status=400)
        updated = 0
        for item in items:
            entry_id = self._coerce_int(item.get("id") or item.get("entry_id"))
            card_id = item.get("card")
            card = None
            entry_created = False

            with transaction.atomic():
                if entry_id is not None:
                    entry = RiftboundCollectionEntry.objects.filter(user=profile.user, pk=entry_id).first()
                    if not entry:
                        continue
                    self._ensure_entry_belongs_to_workspace(entry, profile)

                    if card_id:
                        try:
                            card = RiftboundCard.objects.get(pk=card_id)
                        except RiftboundCard.DoesNotExist:
                            continue
                    else:
                        card = entry.card

                    target_is_foil = self._coerce_bool(item["is_foil"]) if "is_foil" in item else entry.is_foil
                    duplicate = (
                        RiftboundCollectionEntry.objects
                        .filter(user=profile.user, card=card, is_foil=target_is_foil)
                        .exclude(pk=entry.pk)
                        .first()
                    )
                    if duplicate:
                        self._merge_duplicate_entry(entry, duplicate)

                    entry.card = card
                    entry.is_foil = target_is_foil
                else:
                    if not card_id:
                        continue
                    try:
                        card = RiftboundCard.objects.get(pk=card_id)
                    except RiftboundCard.DoesNotExist:
                        continue
                    is_foil = self._coerce_bool(item.get("is_foil", False))
                    entry, entry_created = RiftboundCollectionEntry.objects.get_or_create(
                        user=profile.user, card=card, is_foil=is_foil,
                        defaults={"quantity": 0},
                    )

            try:
                self._enforce_entry_permissions(item, permissions_payload, entry=entry, created=entry_created)
            except PermissionDenied:
                continue

            self._apply_fields(entry, item)
            if entry.quantity <= 0:
                if not _rb_can_permissions(permissions_payload, "delete_collection"):
                    continue
                entry.delete()
            else:
                entry.save()
            updated += 1
        return Response({"updated": updated})

    @action(detail=False, methods=["post"], url_path="bulk-import")
    def bulk_import(self, request):
        """Importa cartas desde texto plano. Líneas: '2 Nombre' / '2x Nombre' / 'Nombre' / 'OGN-001'."""
        import re as _re
        profile, permissions_payload, _ = self._resolve_workspace(required_permission="view_collection")
        if not _rb_can_permissions(permissions_payload, "edit_collection"):
            return Response({"detail": "No tienes permiso para agregar cartas a la carpeta"}, status=403)

        text = (request.data.get("text") or "").strip()
        mode = request.data.get("mode") or "add"
        if not text:
            return Response({"detail": "Sin texto"}, status=400)
        line_re = _re.compile(r"^\s*(?:(\d+)\s*[xX]?\s+)?(.+?)\s*$")
        added = updated_count = ambiguous = not_found = 0
        not_found_lines = []
        ambiguous_lines = []
        for raw in text.splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or line.startswith("//"):
                continue
            m = line_re.match(line)
            if not m:
                continue
            try:
                qty = max(1, int(m.group(1) or 1))
            except ValueError:
                qty = 1
            name = m.group(2).strip()
            if not name:
                continue
            # Match exacto por número primero
            matches = list(
                RiftboundCard.objects.filter(card_number__iexact=name).values_list("id", "name")
            )
            if not matches:
                matches = list(
                    RiftboundCard.objects.filter(name__iexact=name).values_list("id", "name")
                )
            if not matches:
                matches = list(
                    RiftboundCard.objects.filter(name__icontains=name).values_list("id", "name")[:5]
                )
                if not matches:
                    not_found += 1
                    not_found_lines.append(line)
                    continue
                if len(matches) > 1:
                    ambiguous += 1
                    ambiguous_lines.append({"line": line, "matches": [n for _, n in matches]})
                    continue
            card_id = matches[0][0]
            entry, created = RiftboundCollectionEntry.objects.get_or_create(
                user=profile.user, card_id=card_id, is_foil=False,
                defaults={"quantity": qty},
            )
            if created:
                added += 1
            else:
                entry.quantity = qty if mode == "set" else entry.quantity + qty
                entry.save()
                updated_count += 1
        return Response({
            "added": added, "updated": updated_count,
            "not_found": not_found, "ambiguous": ambiguous,
            "not_found_lines": not_found_lines[:20],
            "ambiguous_lines": ambiguous_lines[:20],
        })

    @action(detail=False, methods=["get"], url_path="ids")
    def ids(self, request):
        """Devuelve {collection: {card_id: qty}, wishlist: [card_id, ...]}."""
        profile, _, _ = self._resolve_workspace(required_permission="view_collection")
        coll = {}
        for cid, q in (RiftboundCollectionEntry.objects
                       .filter(user=profile.user)
                       .values_list("card_id", "quantity")):
            coll[cid] = coll.get(cid, 0) + q
        wish = list(RiftboundWishlistEntry.objects.filter(user=profile.user).values_list("card_id", flat=True))
        return Response({"collection": coll, "wishlist": wish})

    @action(detail=False, methods=["get"], url_path="stats")
    def stats(self, request):
        """Estadísticas agregadas de la colección."""
        from collections import Counter
        from django.db.models import Count, Sum
        profile, _, _ = self._resolve_workspace(required_permission="view_collection")
        entries = list(
            RiftboundCollectionEntry.objects
            .filter(user=profile.user)
            .select_related("card", "card__set")
        )
        total_cards = sum(e.quantity for e in entries)
        unique_cards = len({e.card_id for e in entries})
        total_value = sum((e.price or 0) * e.quantity for e in entries)

        by_type = Counter()
        by_rarity = Counter()
        by_color = Counter()
        by_set = Counter()
        set_names = {}
        for e in entries:
            by_type[e.card.card_type] += e.quantity
            by_rarity[e.card.rarity] += e.quantity
            for c in (e.card.colors or []):
                by_color[c] += e.quantity
            if e.card.set:
                by_set[e.card.set.code] += e.quantity
                set_names[e.card.set.code] = e.card.set.name

        set_qs = (RiftboundCard.objects.filter(is_active=True, set__isnull=False)
                  .values("set__code", "set__name")
                  .annotate(total=Count("id")))
        owned_unique_by_set = {}
        for e in entries:
            if e.card.set:
                owned_unique_by_set.setdefault(e.card.set.code, set()).add(e.card_id)

        set_completeness = []
        for row in set_qs:
            code = row["set__code"]
            total = row["total"] or 0
            owned = len(owned_unique_by_set.get(code, set()))
            pct = round((owned / total) * 100) if total else 0
            set_completeness.append({
                "set": code,
                "name": row["set__name"],
                "owned": owned,
                "total": total,
                "pct": pct,
            })
        set_completeness.sort(key=lambda r: -r["pct"])

        return Response({
            "total_cards": total_cards,
            "unique_cards": unique_cards,
            "total_value": total_value,
            "by_type": [{"key": k, "count": v} for k, v in by_type.most_common()],
            "by_rarity": [{"key": k, "count": v} for k, v in by_rarity.most_common()],
            "by_color": [{"key": k, "count": v} for k, v in by_color.most_common()],
            "by_set": [
                {"key": k, "name": set_names.get(k, k), "count": v}
                for k, v in by_set.most_common()
            ],
            "set_completeness": set_completeness,
        })


class RiftboundWishlistViewSet(viewsets.ModelViewSet):
    serializer_class = RiftboundWishlistEntrySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ["card__name", "card__card_number"]

    def get_queryset(self):
        return (
            RiftboundWishlistEntry.objects.filter(user=self.request.user)
            .select_related("card", "card__set")
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=["post"], url_path="toggle")
    def toggle(self, request):
        """Agrega o quita una carta del wishlist. Returns {wishlisted: bool}."""
        card_id = request.data.get("card")
        if not card_id:
            return Response({"detail": "card requerido"}, status=400)
        try:
            card = RiftboundCard.objects.get(pk=card_id)
        except RiftboundCard.DoesNotExist:
            return Response({"detail": "carta no existe"}, status=404)

        existing = RiftboundWishlistEntry.objects.filter(user=request.user, card=card).first()
        if existing:
            existing.delete()
            return Response({"wishlisted": False, "card": card_id})
        RiftboundWishlistEntry.objects.create(user=request.user, card=card, desired_quantity=1)
        return Response({"wishlisted": True, "card": card_id})

    @action(detail=False, methods=["post"], url_path="set-quantity")
    def set_quantity(self, request):
        card_id = request.data.get("card")
        try:
            qty = max(1, int(request.data.get("desired_quantity", 1)))
        except (TypeError, ValueError):
            qty = 1
        try:
            entry = RiftboundWishlistEntry.objects.get(user=request.user, card_id=card_id)
        except RiftboundWishlistEntry.DoesNotExist:
            return Response({"detail": "no existe"}, status=404)
        entry.desired_quantity = qty
        entry.save()
        return Response(self.get_serializer(entry).data)


# ─────────────────────── Binder Profile & Tienda ───────────────────────

import uuid as _uuid
from django.shortcuts import get_object_or_404


RB_WRITABLE_PROFILE_FIELDS = {
    "is_store_public", "display_name", "bio", "city", "country",
    "whatsapp", "instagram", "discord", "email_public",
    "payment_methods", "shipping_info", "accepts_trades",
}


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def riftbound_binder_profile_view(request):
    profile, _ = RiftboundBinderProfile.objects.get_or_create(user=request.user)
    if request.method == "PATCH":
        for k, v in (request.data or {}).items():
            if k in RB_WRITABLE_PROFILE_FIELDS:
                setattr(profile, k, v)
        profile.save()
    return Response(RiftboundBinderProfileSerializer(profile, context={"request": request}).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser, MultiPartParser, FormParser])
def riftbound_upload_binder_avatar(request):
    avatar_url = (request.data.get("avatar_url") or "").strip()
    file_obj = request.FILES.get("file")

    if not avatar_url and file_obj is not None:
        try:
            avatar_url = upload_image_to_cdn(file_obj, folder="deckshado/binder_avatars")
        except CdnImageUploadError as exc:
            return Response({"detail": str(exc)}, status=400)

    if not avatar_url:
        return Response({"detail": "No se envio URL o archivo"}, status=400)
    profile, _ = RiftboundBinderProfile.objects.get_or_create(user=request.user)
    profile.binder_avatar = avatar_url[:500]
    profile.save()
    return Response(RiftboundBinderProfileSerializer(profile, context={"request": request}).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def riftbound_regenerate_share_token(request):
    profile, _ = RiftboundBinderProfile.objects.get_or_create(user=request.user)
    profile.share_token = _uuid.uuid4()
    profile.save()
    return Response({"share_token": str(profile.share_token)})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def riftbound_my_share_token(request):
    profile, _ = RiftboundBinderProfile.objects.get_or_create(user=request.user)
    return Response({
        "share_token": str(profile.share_token),
        "store_slug": profile.store_slug,
        "is_store_public": profile.is_store_public,
    })


RB_PERMISSION_FIELD_MAP = {
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


def _rb_is_store_permission_manager(profile, user):
    if profile.user_id == user.id:
        return True
    perm = RiftboundStorePermission.objects.filter(store_profile=profile, user=user).first()
    return bool(perm and perm.can_manage_permissions)


def _rb_permission_values_from_payload(payload):
    source = payload.get("permissions") if isinstance(payload.get("permissions"), dict) else payload
    values = {}
    for short_key, model_field in RB_PERMISSION_FIELD_MAP.items():
        if short_key in source:
            values[model_field] = bool(source.get(short_key))
        elif model_field in source:
            values[model_field] = bool(source.get(model_field))
    return values


def _rb_workspace_payload(profile, request, permissions_payload, is_owner):
    profile_data = RiftboundBinderProfileSerializer(profile, context={"request": request}).data
    return {
        "store_profile_id": profile.id,
        "is_owner": bool(is_owner),
        "owner_username": profile.user.username,
        "permissions": permissions_payload,
        "profile": profile_data,
    }


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def riftbound_workspaces(request):
    own_profile = _rb_get_or_create_profile_for_user(request.user)
    results = [
        _rb_workspace_payload(
            own_profile,
            request,
            dict(RB_OWNER_PERMISSIONS),
            is_owner=True,
        )
    ]

    collaborator_qs = (
        RiftboundStorePermission.objects
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
        results.append(_rb_workspace_payload(profile, request, permissions_payload, is_owner=False))

    results.sort(key=lambda row: (0 if row["is_owner"] else 1, row["owner_username"].lower()))
    return Response({"results": results})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def riftbound_workspace_permissions(request, profile_id):
    profile = get_object_or_404(RiftboundBinderProfile.objects.select_related("user"), pk=profile_id)
    if not _rb_is_store_permission_manager(profile, request.user):
        raise PermissionDenied("No puedes administrar permisos de esta tienda")

    perms = (
        RiftboundStorePermission.objects
        .filter(store_profile=profile)
        .exclude(user=profile.user)
        .select_related("user", "granted_by")
    )
    data = RiftboundStorePermissionSerializer(perms, many=True, context={"request": request}).data
    return Response({"store_profile_id": profile.id, "results": data})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def riftbound_workspace_permission_upsert(request, profile_id):
    profile = get_object_or_404(RiftboundBinderProfile.objects.select_related("user"), pk=profile_id)
    if not _rb_is_store_permission_manager(profile, request.user):
        raise PermissionDenied("No puedes administrar permisos de esta tienda")

    payload = request.data or {}
    user_identifier = (payload.get("username") or payload.get("email") or payload.get("user") or "").strip()
    if not user_identifier:
        return Response({"detail": "Debes indicar username o email"}, status=400)

    user_model = get_user_model()
    target_user = user_model.objects.filter(username__iexact=user_identifier).first()
    if target_user is None and "@" in user_identifier:
        target_user = user_model.objects.filter(email__iexact=user_identifier).first()
    if target_user is None:
        return Response({"detail": "Usuario no encontrado"}, status=404)
    if target_user.id == profile.user_id:
        return Response({"detail": "No puedes asignar permisos al propietario"}, status=400)

    values = _rb_permission_values_from_payload(payload)
    if not values:
        return Response({"detail": "No se enviaron permisos a actualizar"}, status=400)

    is_owner = profile.user_id == request.user.id
    if (not is_owner) and values.get("can_manage_permissions"):
        raise PermissionDenied("Solo el propietario puede delegar la gestion de permisos")

    perm, created = RiftboundStorePermission.objects.get_or_create(
        store_profile=profile,
        user=target_user,
        defaults={"granted_by": request.user},
    )
    for field_name, field_value in values.items():
        setattr(perm, field_name, field_value)

    has_any_permission = any(bool(getattr(perm, field)) for field in RB_PERMISSION_FIELD_MAP.values())
    if not has_any_permission:
        perm.delete()
        return Response({"deleted": True})

    perm.granted_by = request.user
    perm.save()
    data = RiftboundStorePermissionSerializer(perm, context={"request": request}).data
    return Response(data, status=201 if created else 200)


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def riftbound_workspace_permission_update(request, profile_id, permission_id):
    profile = get_object_or_404(RiftboundBinderProfile.objects.select_related("user"), pk=profile_id)
    if not _rb_is_store_permission_manager(profile, request.user):
        raise PermissionDenied("No puedes administrar permisos de esta tienda")

    perm = get_object_or_404(
        RiftboundStorePermission.objects.select_related("user", "granted_by"),
        pk=permission_id,
        store_profile=profile,
    )
    if perm.user_id == profile.user_id:
        return Response({"detail": "No puedes editar permisos del propietario"}, status=400)

    values = _rb_permission_values_from_payload(request.data or {})
    if not values:
        return Response({"detail": "No se enviaron permisos a actualizar"}, status=400)

    is_owner = profile.user_id == request.user.id
    if (not is_owner) and values.get("can_manage_permissions"):
        raise PermissionDenied("Solo el propietario puede delegar la gestion de permisos")

    for field_name, field_value in values.items():
        setattr(perm, field_name, field_value)

    has_any_permission = any(bool(getattr(perm, field)) for field in RB_PERMISSION_FIELD_MAP.values())
    if not has_any_permission:
        perm.delete()
        return Response({"deleted": True})

    perm.granted_by = request.user
    perm.save()
    return Response(RiftboundStorePermissionSerializer(perm, context={"request": request}).data)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def riftbound_workspace_permission_delete(request, profile_id, permission_id):
    profile = get_object_or_404(RiftboundBinderProfile.objects.select_related("user"), pk=profile_id)
    if not _rb_is_store_permission_manager(profile, request.user):
        raise PermissionDenied("No puedes administrar permisos de esta tienda")

    perm = get_object_or_404(RiftboundStorePermission, pk=permission_id, store_profile=profile)
    if perm.user_id == profile.user_id:
        return Response({"detail": "No puedes eliminar permisos del propietario"}, status=400)
    perm.delete()
    return Response(status=204)


def _rb_resolve_public_profile(token_or_slug):
    try:
        token = _uuid.UUID(str(token_or_slug))
        return get_object_or_404(RiftboundBinderProfile, share_token=token)
    except (ValueError, AttributeError):
        return get_object_or_404(
            RiftboundBinderProfile, store_slug=str(token_or_slug).lower(), is_store_public=True,
        )


def _rb_filter_store_qs(qs, params):
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
    set_code = params.get("set")
    if set_code:
        qs = qs.filter(card__set__code__iexact=set_code)
    ctype = params.get("type")
    if ctype:
        qs = qs.filter(card__card_type=ctype)
    rarity = params.get("rarity")
    if rarity:
        qs = qs.filter(card__rarity=rarity)
    for field in ("energy", "power", "might"):
        v = params.get(field)
        if v not in (None, ""):
            try:
                qs = qs.filter(**{f"card__{field}": int(v)})
            except ValueError:
                pass
    colors = (params.get("colors") or "").strip()
    if colors:
        color_set = {c.strip().lower() for c in colors.split(",") if c.strip()}
        ids = [
            pk for pk, cs in qs.values_list("id", "card__colors")
            if cs and any((c or "").lower() in color_set for c in cs)
        ]
        qs = qs.filter(id__in=ids)
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


class RiftboundPublicStoreListView(generics.ListAPIView):
    serializer_class = RiftboundCollectionEntrySerializer
    permission_classes = [AllowAny]
    pagination_class = RiftboundCollectionPagination

    def get_queryset(self):
        profile = _rb_resolve_public_profile(self.kwargs["token"])
        self._profile = profile
        qs = RiftboundCollectionEntry.objects.filter(
            user=profile.user, selling_quantity__gt=0,
        ).select_related("card", "card__set")
        return _rb_filter_store_qs(qs, self.request.query_params)

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        response.data["store"] = _rb_public_profile_payload(self._profile, request)
        response.data["store_owner"] = self._profile.user.username
        response.data["store_avatar"] = response.data["store"]["user_avatar_url"]
        response.data["store_binder_avatar"] = response.data["store"]["binder_avatar_url"]
        return response


def _rb_public_profile_payload(profile, request):
    sel_count = RiftboundCollectionEntry.objects.filter(
        user=profile.user, selling_quantity__gt=0,
    ).count()
    wish_count = RiftboundWishlistEntry.objects.filter(user=profile.user).count()
    profile.selling_count = sel_count
    data = RiftboundPublicBinderProfileSerializer(profile, context={"request": request}).data
    data["has_store"] = bool(profile.is_store_public and sel_count > 0)
    data["has_wishlist"] = wish_count > 0
    data["wishlist_count"] = wish_count
    return data


class RiftboundPublicWishlistListView(generics.ListAPIView):
    """Wishlist pública de Riftbound por share_token (UUID) o slug si la tienda es pública."""
    serializer_class = RiftboundWishlistEntrySerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        profile = _rb_resolve_public_profile(self.kwargs["token"])
        self._profile = profile
        qs = RiftboundWishlistEntry.objects.filter(user=profile.user).select_related(
            "card", "card__set",
        )
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(card__name__icontains=search)
        ordering = self.request.query_params.get("ordering") or "-id"
        allowed = {"card__name", "-card__name", "id", "-id"}
        if ordering in allowed:
            qs = qs.order_by(ordering)
        return qs

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        response.data["store"] = _rb_public_profile_payload(self._profile, request)
        return response


class RiftboundPublicStoreIndexView(generics.ListAPIView):
    """Listado público de tiendas Riftbound."""
    serializer_class = RiftboundPublicBinderProfileSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = (
            RiftboundBinderProfile.objects.filter(is_store_public=True)
            .annotate(
                selling_count=Count(
                    "user__riftbound_collection",
                    filter=Q(user__riftbound_collection__selling_quantity__gt=0),
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


def _rb_create_store_order(profile, buyer_user, payload):
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
            RiftboundCollectionEntry.objects.select_for_update()
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

        order = RiftboundStoreOrder.objects.create(
            store_profile=profile,
            buyer_user=buyer_user,
            buyer_name=buyer_name,
            buyer_whatsapp=buyer_whatsapp,
            buyer_note=buyer_note,
            status=RiftboundStoreOrder.STATUS_PENDING,
        )

        total_estimated = 0
        has_priced_items = False

        for entry_id, qty in requested_by_entry.items():
            entry = entry_map[entry_id]
            unit_price = entry.price
            line_total = unit_price * qty if unit_price is not None else None

            RiftboundStoreOrderItem.objects.create(
                order=order,
                collection_entry=entry,
                card=entry.card,
                quantity=qty,
                unit_price=unit_price,
                line_total=line_total,
                card_name=entry.card.name,
                card_number=entry.card.card_number,
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
            message=f"Nuevo pedido Riftbound de {buyer_label} ({total_items} cartas)",
            link="/riftbound/carpeta?tab=pedidos",
        )
    except Exception:
        pass

    return (
        RiftboundStoreOrder.objects.select_related("store_profile", "store_profile__user", "buyer_user")
        .prefetch_related("items", "items__card")
        .get(pk=order.pk)
    )


class RiftboundPublicStoreOrderCreateView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = RiftboundStoreOrderCreateSerializer

    def post(self, request, *args, **kwargs):
        profile = _rb_resolve_public_profile(self.kwargs["token"])
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        buyer_user = request.user if request.user.is_authenticated else None
        try:
            order = _rb_create_store_order(profile, buyer_user, serializer.validated_data)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)

        return Response(
            RiftboundStoreOrderSerializer(order, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class RiftboundMyPurchaseOrderListView(generics.ListAPIView):
    """Pedidos que el usuario autenticado hizo como COMPRADOR, en cualquier tienda."""
    permission_classes = [IsAuthenticated]
    serializer_class = RiftboundStoreOrderSerializer

    def get_queryset(self):
        qs = (
            RiftboundStoreOrder.objects.filter(buyer_user=self.request.user)
            .select_related("store_profile", "store_profile__user", "buyer_user")
            .prefetch_related("items", "items__card")
            .order_by("-created_at")
        )
        store_token = (self.request.query_params.get("store") or "").strip()
        if store_token:
            try:
                profile = _rb_resolve_public_profile(store_token)
            except Http404:
                return qs.none()
            qs = qs.filter(store_profile=profile)
        status_filter = (self.request.query_params.get("status") or "").strip().lower()
        allowed = {
            RiftboundStoreOrder.STATUS_PENDING,
            RiftboundStoreOrder.STATUS_ACCEPTED,
            RiftboundStoreOrder.STATUS_CANCELLED,
        }
        if status_filter in allowed:
            qs = qs.filter(status=status_filter)
        return qs


class RiftboundMyStoreOrderListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = RiftboundStoreOrderSerializer

    def get_queryset(self):
        profile, permissions_payload, _ = _rb_resolve_workspace(self.request)
        qs = (
            RiftboundStoreOrder.objects.filter(store_profile=profile)
            .select_related("store_profile", "store_profile__user", "buyer_user")
            .prefetch_related("items", "items__card")
        )
        status_filter = (self.request.query_params.get("status") or "").strip().lower()
        allowed = {
            RiftboundStoreOrder.STATUS_PENDING,
            RiftboundStoreOrder.STATUS_ACCEPTED,
            RiftboundStoreOrder.STATUS_CANCELLED,
        }

        def _can_view_status(status_value):
            if status_value == RiftboundStoreOrder.STATUS_PENDING:
                return _rb_can_permissions(permissions_payload, "view_orders")
            return _rb_can_permissions(permissions_payload, "view_history")

        if status_filter in allowed:
            if not _can_view_status(status_filter):
                raise PermissionDenied("No tienes permiso para ver ese estado de pedidos")
            qs = qs.filter(status=status_filter)
        else:
            status_q = Q()
            if _rb_can_permissions(permissions_payload, "view_orders"):
                status_q |= Q(status=RiftboundStoreOrder.STATUS_PENDING)
            if _rb_can_permissions(permissions_payload, "view_history"):
                status_q |= Q(status__in=[RiftboundStoreOrder.STATUS_ACCEPTED, RiftboundStoreOrder.STATUS_CANCELLED])
            if not status_q:
                raise PermissionDenied("No tienes permiso para ver pedidos de esta tienda")
            qs = qs.filter(status_q)
        return qs


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def riftbound_my_order_assignments(request):
    profile, permissions_payload, _ = _rb_resolve_workspace(request)
    if not _rb_can_permissions(permissions_payload, "view_orders"):
        raise PermissionDenied("No tienes permiso para ver pedidos pendientes")

    rows = (
        RiftboundStoreOrderItem.objects.filter(
            order__store_profile=profile,
            order__status=RiftboundStoreOrder.STATUS_PENDING,
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


def _rb_update_order_status(request, order_id, new_status):
    if new_status not in {RiftboundStoreOrder.STATUS_ACCEPTED, RiftboundStoreOrder.STATUS_CANCELLED}:
        return Response({"detail": "Estado invalido."}, status=400)

    required_permission = "accept_orders" if new_status == RiftboundStoreOrder.STATUS_ACCEPTED else "reject_orders"

    with transaction.atomic():
        try:
            order = (
                RiftboundStoreOrder.objects.select_for_update()
                .select_related("store_profile", "store_profile__user", "buyer_user")
                .prefetch_related("items")
                .get(pk=order_id)
            )
        except RiftboundStoreOrder.DoesNotExist:
            return Response({"detail": "Pedido no encontrado."}, status=404)

        permissions_payload = _rb_permissions_payload_for_user(order.store_profile, request.user)
        if permissions_payload is None:
            return Response({"detail": "Pedido no encontrado."}, status=404)
        if not _rb_can_permissions(permissions_payload, required_permission):
            return Response({"detail": "No tienes permiso para gestionar este pedido."}, status=403)

        if order.status != RiftboundStoreOrder.STATUS_PENDING:
            return Response({"detail": "Solo puedes gestionar pedidos pendientes."}, status=400)

        items = list(order.items.all())
        entry_ids = [it.collection_entry_id for it in items if it.collection_entry_id]
        entry_map = {}
        if entry_ids:
            entry_map = {
                e.id: e
                for e in RiftboundCollectionEntry.objects.select_for_update().filter(
                    id__in=entry_ids,
                    user=order.store_profile.user,
                )
            }

        for item in items:
            if not item.collection_entry_id:
                continue
            entry = entry_map.get(item.collection_entry_id)
            if not entry:
                continue

            qty = max(0, int(item.quantity or 0))
            if new_status == RiftboundStoreOrder.STATUS_CANCELLED:
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
        order.responded_by = request.user
        order.seller_note = str((request.data or {}).get("seller_note") or "").strip()[:800]
        order.save(update_fields=["status", "responded_at", "responded_by", "seller_note", "updated_at"])

    try:
        if order.buyer_user_id:
            msg = "Tu pedido Riftbound fue aceptado." if new_status == RiftboundStoreOrder.STATUS_ACCEPTED else "Tu pedido Riftbound fue cancelado."
            Notification.objects.create(
                user=order.buyer_user,
                notif_type="general",
                message=msg,
                link=f"/riftbound/tienda/{order.store_profile.share_token}",
            )
    except Exception:
        pass

    payload = (
        RiftboundStoreOrder.objects.select_related("store_profile", "store_profile__user", "buyer_user")
        .prefetch_related("items", "items__card")
        .get(pk=order.pk)
    )
    return Response(RiftboundStoreOrderSerializer(payload, context={"request": request}).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def riftbound_accept_store_order(request, order_id):
    return _rb_update_order_status(request, order_id, RiftboundStoreOrder.STATUS_ACCEPTED)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def riftbound_cancel_store_order(request, order_id):
    return _rb_update_order_status(request, order_id, RiftboundStoreOrder.STATUS_CANCELLED)


# ─── TCGPlayer Price Proxy ───────────────────────────────────────────────────


@api_view(["GET"])
@permission_classes([AllowAny])
def tcgplayer_price_view(request):
    """Obtiene precio de TCGPlayer para una carta por nombre."""
    card_name = request.query_params.get("card_name", "").strip()
    if not card_name or len(card_name) < 2:
        return Response({"error": "card_name is required (min 2 chars)"}, status=400)

    data = get_tcg_price(card_name)
    if data is None or data.get("market_price") is None:
        return Response({"card_name": card_name, "market_price": None})

    return Response(data)


@api_view(["POST"])
@permission_classes([AllowAny])
def tcgplayer_prices_batch_view(request):
    """Obtiene precios de TCGPlayer para múltiples cartas (máx 20)."""
    card_names = request.data.get("card_names", [])
    if not isinstance(card_names, list):
        return Response({"error": "card_names must be a list"}, status=400)
    if len(card_names) == 0:
        return Response({"prices": []})

    prices = get_tcg_prices_batch(card_names)
    return Response({"prices": prices})


@api_view(["GET"])
@permission_classes([AllowAny])
def tcgmatch_price_view(request):
    """Obtiene precio de TCGMatch para una carta por nombre."""
    card_name = request.query_params.get("card_name", "").strip()
    if not card_name or len(card_name) < 2:
        return Response({"error": "card_name is required (min 2 chars)"}, status=400)

    data = get_tcgmatch_price(card_name)
    if data is None or (
        data.get("market_price") is None and data.get("low_price") is None
    ):
        return Response({
            "card_name": card_name,
            "market_price": None,
            "low_price": None,
            "currency": "CLP",
        })

    return Response(data)
