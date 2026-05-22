from django.db.models import Q
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly

from .models import (
    RiftboundCard, RiftboundSet, RiftboundFormat, RiftboundBanlistEntry,
    RiftboundDeck, RiftboundCollectionEntry, RiftboundWishlistEntry, RiftboundIcon,
)
from .serializers import (
    RiftboundCardSerializer, RiftboundCardLiteSerializer,
    RiftboundSetSerializer, RiftboundFormatSerializer,
    RiftboundBanlistEntrySerializer, RiftboundDeckSerializer,
    RiftboundCollectionEntrySerializer, RiftboundWishlistEntrySerializer,
    RiftboundIconSerializer,
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


class RiftboundCollectionViewSet(viewsets.ModelViewSet):
    serializer_class = RiftboundCollectionEntrySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ["card__name", "card__card_number"]

    def get_queryset(self):
        return (
            RiftboundCollectionEntry.objects.filter(user=self.request.user)
            .select_related("card", "card__set")
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

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
        entry, _ = RiftboundCollectionEntry.objects.get_or_create(
            user=request.user, card=card, is_foil=is_foil,
            defaults={"quantity": 0},
        )
        if "quantity" in request.data:
            try:
                entry.quantity = max(0, int(request.data["quantity"]))
            except (TypeError, ValueError):
                pass
        else:
            # comportamiento "add 1" si no se pasa quantity explícita
            entry.quantity += 1

        if "notes" in request.data:
            entry.notes = str(request.data["notes"])[:200]

        if entry.quantity <= 0:
            entry.delete()
            return Response({"deleted": True, "card": card_id})

        entry.save()
        return Response(self.get_serializer(entry).data)

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
        entries = list(
            RiftboundCollectionEntry.objects
            .filter(user=request.user)
            .select_related("card", "card__set")
        )
        total_cards = sum(e.quantity for e in entries)
        unique_cards = len({e.card_id for e in entries})

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

        # Completitud por set
        from django.db.models import Count
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
