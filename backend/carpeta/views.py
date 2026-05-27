import re
import uuid

from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from django.db.models import Q, Count, Sum, F
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import BinderProfile, CollectionEntry, WishlistEntry
from .serializers import (
    BinderProfileSerializer,
    PublicBinderProfileSerializer,
    CollectionEntrySerializer,
    CollectionEntryWriteSerializer,
    WishlistEntrySerializer,
    WishlistEntryWriteSerializer,
)


class CarpetaPagination(PageNumberPagination):
    page_size = 40


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
def upload_binder_avatar(request):
    avatar_url = (request.data.get("avatar_url") or "").strip()
    if not avatar_url:
        return Response({"detail": "No se envió URL de imagen."}, status=status.HTTP_400_BAD_REQUEST)
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


# ── Collection ───────────────────────────────────────────

class MyCollectionListView(generics.ListAPIView):
    serializer_class = CollectionEntrySerializer
    pagination_class = CarpetaPagination
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = CollectionEntry.objects.filter(user=self.request.user).select_related(
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
    if entry.selling_quantity > entry.quantity:
        entry.selling_quantity = entry.quantity


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def collection_upsert(request):
    card_id = request.data.get("card")
    if not card_id:
        return Response({"detail": "card es requerido."}, status=status.HTTP_400_BAD_REQUEST)

    entry, created = CollectionEntry.objects.get_or_create(
        user=request.user, card_id=card_id,
        defaults={"quantity": int(request.data.get("quantity", 1) or 1)},
    )
    if created:
        _apply_collection_fields(entry, request.data)
    else:
        _apply_collection_fields(entry, request.data)
    entry.save()

    entry = CollectionEntry.objects.select_related(
        "card__edition", "card__rarity", "card__race", "card__card_type"
    ).get(pk=entry.pk)
    return Response(CollectionEntrySerializer(entry).data, status=status.HTTP_200_OK)


@api_view(["DELETE"])
@permission_classes([permissions.IsAuthenticated])
def collection_delete(request, card_id):
    deleted, _ = CollectionEntry.objects.filter(user=request.user, card_id=card_id).delete()
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
    if len(items) > 200:
        return Response({"detail": "Máximo 200 cambios por lote."}, status=status.HTTP_400_BAD_REQUEST)

    updated = 0
    for item in items:
        card_id = item.get("card")
        if not card_id:
            continue
        entry, created = CollectionEntry.objects.get_or_create(
            user=request.user, card_id=card_id,
            defaults={"quantity": int(item.get("quantity", 1) or 1)},
        )
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
