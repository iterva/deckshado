from django.db.models import Q
from rest_framework import viewsets, permissions, status, filters, generics
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly

from .models import (
    RiftboundCard, RiftboundSet, RiftboundFormat, RiftboundBanlistEntry,
    RiftboundDeck, RiftboundCollectionEntry, RiftboundWishlistEntry, RiftboundIcon,
    RiftboundBinderProfile,
)
from .serializers import (
    RiftboundCardSerializer, RiftboundCardLiteSerializer,
    RiftboundSetSerializer, RiftboundFormatSerializer,
    RiftboundBanlistEntrySerializer, RiftboundDeckSerializer,
    RiftboundCollectionEntrySerializer, RiftboundWishlistEntrySerializer,
    RiftboundIconSerializer,
    RiftboundBinderProfileSerializer, RiftboundPublicBinderProfileSerializer,
)


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
        if color_list:
            color_set = set(color_list)
            ids = [pk for pk, cs in qs.values_list("id", "colors")
                   if cs and any(c in color_set for c in cs)]
            qs = qs.filter(id__in=ids)

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

    def get_queryset(self):
        qs = (
            RiftboundCollectionEntry.objects.filter(user=self.request.user)
            .select_related("card", "card__set")
        )
        if self.request.query_params.get("selling") == "1":
            qs = qs.filter(selling_quantity__gt=0)
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

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
            entry.is_foil = bool(data["is_foil"])
        if "notes" in data:
            entry.notes = str(data["notes"] or "")[:200]
        if entry.selling_quantity > entry.quantity:
            entry.selling_quantity = entry.quantity

    @action(detail=False, methods=["post"], url_path="upsert")
    def upsert(self, request):
        """Crea o actualiza una entrada por (user, card, is_foil)."""
        card_id = request.data.get("card")
        if not card_id:
            return Response({"detail": "card requerido"}, status=400)
        try:
            card = RiftboundCard.objects.get(pk=card_id)
        except RiftboundCard.DoesNotExist:
            return Response({"detail": "carta no existe"}, status=404)

        is_foil = bool(request.data.get("is_foil", False))
        entry, created = RiftboundCollectionEntry.objects.get_or_create(
            user=request.user, card=card, is_foil=is_foil,
            defaults={"quantity": 0},
        )
        if "quantity" not in request.data and created:
            entry.quantity = 1
        self._apply_fields(entry, request.data)

        if entry.quantity <= 0:
            entry.delete()
            return Response({"deleted": True, "card": card_id})

        entry.save()
        return Response(self.get_serializer(entry).data)

    @action(detail=False, methods=["post"], url_path="batch-upsert")
    def batch_upsert(self, request):
        items = request.data if isinstance(request.data, list) else []
        if not items:
            return Response({"detail": "Se esperaba lista"}, status=400)
        if len(items) > 200:
            return Response({"detail": "Máximo 200"}, status=400)
        updated = 0
        for item in items:
            card_id = item.get("card")
            if not card_id:
                continue
            try:
                card = RiftboundCard.objects.get(pk=card_id)
            except RiftboundCard.DoesNotExist:
                continue
            is_foil = bool(item.get("is_foil", False))
            entry, _ = RiftboundCollectionEntry.objects.get_or_create(
                user=request.user, card=card, is_foil=is_foil,
                defaults={"quantity": 0},
            )
            self._apply_fields(entry, item)
            if entry.quantity <= 0:
                entry.delete()
            else:
                entry.save()
            updated += 1
        return Response({"updated": updated})

    @action(detail=False, methods=["post"], url_path="bulk-import")
    def bulk_import(self, request):
        """Importa cartas desde texto plano. Líneas: '2 Nombre' / '2x Nombre' / 'Nombre' / 'OGN-001'."""
        import re as _re
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
                user=request.user, card_id=card_id, is_foil=False,
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
        coll = {}
        for cid, q in (RiftboundCollectionEntry.objects
                       .filter(user=request.user)
                       .values_list("card_id", "quantity")):
            coll[cid] = coll.get(cid, 0) + q
        wish = list(RiftboundWishlistEntry.objects
                    .filter(user=request.user)
                    .values_list("card_id", flat=True))
        return Response({"collection": coll, "wishlist": wish})

    @action(detail=False, methods=["get"], url_path="stats")
    def stats(self, request):
        """Estadísticas agregadas de la colección."""
        from collections import Counter
        from django.db.models import Count, Sum
        entries = list(
            RiftboundCollectionEntry.objects
            .filter(user=request.user)
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
from django.db.models import Count, Sum


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
def riftbound_upload_binder_avatar(request):
    avatar_url = (request.data.get("avatar_url") or "").strip()
    if not avatar_url:
        return Response({"detail": "No se envió URL"}, status=400)
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


def _rb_resolve_public_profile(token_or_slug):
    try:
        token = _uuid.UUID(str(token_or_slug))
        return get_object_or_404(RiftboundBinderProfile, share_token=token)
    except (ValueError, AttributeError):
        return get_object_or_404(
            RiftboundBinderProfile, store_slug=str(token_or_slug).lower(), is_store_public=True,
        )


def _rb_filter_store_qs(qs, params):
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
