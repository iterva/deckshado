import csv
import io

from django.core.management import call_command
from django.db.models import Q, Case, When, Value, IntegerField
from django.core.cache import cache
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import viewsets, permissions, status, filters, generics
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly

from .tcgplayer import get_tcg_price, get_tcg_prices_batch
from .integrations.riftcodex import ALLOWED_INDEX_TYPES, RiftcodexClient, normalize_riftbound_card_number

from .models import (
    RiftboundCard, RiftboundSet, RiftboundFormat, RiftboundBanlistEntry,
    RiftboundDeck, RiftboundCollectionEntry, RiftboundWishlistEntry, RiftboundIcon,
    RiftboundBinderProfile, RiftboundSyncState, RiftboundOpsRun,
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
    hybrid_min_results = 12

    def _is_hybrid_enabled(self, params):
        return (params.get("hybrid") or "") in ("1", "true", "True")

    def filter_queryset(self, queryset):
        # En modo hybrid aplicamos busqueda textual manual en get_queryset,
        # por lo que omitimos SearchFilter para no descartar resultados remotos.
        if self._is_hybrid_enabled(self.request.query_params):
            q = queryset
            for backend in self.filter_backends:
                if backend is filters.SearchFilter:
                    continue
                q = backend().filter_queryset(self.request, q, self)
            return q
        return super().filter_queryset(queryset)

    def _expand_with_remote_candidates(self, base_qs, text_qs, query: str, set_code: str | None):
        local_rows = list(text_qs.values("id", "name", "card_number")[:300])
        local_ids = {r["id"] for r in local_rows}
        if len(local_ids) >= self.hybrid_min_results:
            return text_qs

        try:
            client = RiftcodexClient(timeout=10, max_retries=2, backoff_seconds=0.2)
            remote_items = []
            remote_items.extend(client.search_cards_by_name(fuzzy=query, set_id=set_code, size=30))
            remote_items.extend(client.search_cards(query=query, set_id=set_code, size=30))
        except Exception:
            return text_qs

        if not remote_items:
            return text_qs

        number_to_id = {
            str(card_number).upper(): cid
            for cid, card_number in base_qs.values_list("id", "card_number")
        }

        merged_ids = set(local_ids)
        for item in remote_items:
            meta = item.get("metadata") or {}
            number = normalize_riftbound_card_number(
                item.get("riftbound_id") or "",
                signature=bool(meta.get("signature")),
            ).upper()
            if not number:
                continue
            cid = number_to_id.get(number)
            if cid:
                merged_ids.add(cid)

        if not merged_ids:
            return text_qs

        # Ranking: exacto > prefijo > contiene > solo remoto.
        ql = query.lower()
        scores: dict[int, int] = {}
        for row in local_rows:
            cid = row["id"]
            name = str(row.get("name") or "").lower()
            num = str(row.get("card_number") or "").lower()
            if name == ql or num == ql:
                scores[cid] = 0
            elif name.startswith(ql) or num.startswith(ql):
                scores[cid] = 1
            else:
                scores[cid] = 2

        for cid in merged_ids:
            if cid not in scores:
                scores[cid] = 3

        whens = [When(id=cid, then=Value(rank)) for cid, rank in scores.items()]
        return (
            base_qs.filter(id__in=merged_ids)
            .annotate(_hybrid_rank=Case(*whens, default=Value(9), output_field=IntegerField()))
            .order_by("_hybrid_rank", "card_number")
        )

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

        search_q = (params.get("search") or "").strip()
        if search_q:
            base_qs = qs
            text_qs = qs.filter(
                Q(name__icontains=search_q)
                | Q(card_number__icontains=search_q)
                | Q(description__icontains=search_q)
            )
            if self._is_hybrid_enabled(params):
                return self._expand_with_remote_candidates(
                    base_qs=base_qs,
                    text_qs=text_qs,
                    query=search_q,
                    set_code=(params.get("set") or "").strip() or None,
                )
            qs = text_qs

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
        if "photo_url" in data:
            entry.photo_url = str(data["photo_url"] or "")[:500]
        if "photo_url_2" in data:
            entry.photo_url_2 = str(data["photo_url_2"] or "")[:500]
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


def _rb_sort_mixed(values):
    return sorted(values, key=lambda v: (0, v) if isinstance(v, (int, float)) else (1, str(v).lower()))


def _rb_local_index_payload(index_type: str) -> dict:
    qs = RiftboundCard.objects.filter(is_active=True)

    if index_type == "card-types":
        values = [v for v in qs.values_list("card_type", flat=True).distinct() if v]
    elif index_type == "card-supertypes":
        values = [v for v in qs.values_list("supertype", flat=True).distinct() if v]
    elif index_type == "rarities":
        values = [v for v in qs.values_list("rarity", flat=True).distinct() if v]
    elif index_type == "card-names":
        values = [v for v in qs.values_list("name", flat=True).distinct() if v]
    elif index_type == "domains":
        vals = set()
        for colors in qs.values_list("colors", flat=True):
            for c in (colors or []):
                vals.add(c)
        values = list(vals)
    elif index_type in ("tags", "keywords"):
        vals = set()
        for tags in qs.values_list("subtypes", flat=True):
            for t in (tags or []):
                vals.add(t)
        values = list(vals)
    elif index_type in ("energy", "might", "power"):
        values = [v for v in qs.values_list(index_type, flat=True).distinct() if v is not None]
    elif index_type == "artists":
        # El modelo local no persiste artista separado de la API externa.
        values = []
    else:
        values = []

    values = _rb_sort_mixed(values)
    return {
        "type": index_type,
        "total": len(values),
        "values": values,
        "generated_at": timezone.now(),
    }


@api_view(["GET"])
@permission_classes([AllowAny])
def riftcodex_index_proxy_view(request, index_type: str):
    """Proxy cacheado de indices Riftcodex con fallback local."""
    index_type = (index_type or "").strip().lower()
    if index_type not in ALLOWED_INDEX_TYPES:
        return Response(
            {
                "detail": "index_type no soportado",
                "allowed": list(ALLOWED_INDEX_TYPES),
            },
            status=400,
        )

    cache_key = f"riftcodex:index:{index_type}:v1"
    cached = cache.get(cache_key)
    if cached:
        return Response({**cached, "source": "cache"})

    ttl = 60 * 60 * 6
    try:
        payload = RiftcodexClient().fetch_index(index_type)
        payload["generated_at"] = timezone.now()
        cache.set(cache_key, payload, ttl)
        return Response({**payload, "source": "remote"})
    except Exception as exc:
        local_payload = _rb_local_index_payload(index_type)
        local_payload["source"] = "local-fallback"
        local_payload["upstream_error"] = str(exc)[:300]
        return Response(local_payload)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def riftcodex_sync_status_view(request):
    """Estado operativo de la ultima sincronizacion con Riftcodex."""
    state = RiftboundSyncState.objects.filter(provider="riftcodex", key="cards").first()
    if not state:
        return Response(
            {
                "provider": "riftcodex",
                "key": "cards",
                "configured": False,
                "status": "never_run",
                "message": "Aun no existe estado de sincronizacion.",
            }
        )

    age_hours = None
    if state.last_success_at:
        age_hours = round((timezone.now() - state.last_success_at).total_seconds() / 3600, 2)

    status_key = "ok" if not state.last_error else "error"
    return Response(
        {
            "provider": state.provider,
            "key": state.key,
            "configured": True,
            "status": status_key,
            "last_cursor": state.last_cursor,
            "last_started_at": state.last_started_at,
            "last_success_at": state.last_success_at,
            "last_success_age_hours": age_hours,
            "last_stats": state.last_stats,
            "last_error": state.last_error,
            "updated_at": state.updated_at,
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def riftcodex_audit_status_view(request):
    """Devuelve el ultimo reporte de auditoria local vs Riftcodex."""
    state = RiftboundSyncState.objects.filter(provider="riftcodex", key="audit_cards").first()
    if not state:
        return Response(
            {
                "provider": "riftcodex",
                "key": "audit_cards",
                "configured": False,
                "status": "never_run",
                "message": "No existe auditoria. Ejecuta manage.py audit_riftcodex_diff.",
            }
        )

    return Response(
        {
            "provider": state.provider,
            "key": state.key,
            "configured": True,
            "status": "ok" if not state.last_error else "error",
            "last_started_at": state.last_started_at,
            "last_success_at": state.last_success_at,
            "last_stats": state.last_stats,
            "last_error": state.last_error,
            "updated_at": state.updated_at,
        }
    )


def _rb_is_admin(user) -> bool:
    return bool(
        user
        and user.is_authenticated
        and (getattr(user, "is_admin", False) or user.is_staff or user.is_superuser)
    )


def _rb_start_ops_run(kind: str, command: str, request, args: dict) -> RiftboundOpsRun:
    return RiftboundOpsRun.objects.create(
        provider="riftcodex",
        kind=kind,
        command=command,
        status=RiftboundOpsRun.STATUS_RUNNING,
        requested_by=request.user if request.user.is_authenticated else None,
        args=args or {},
    )


def _rb_finish_ops_run(run: RiftboundOpsRun, ok: bool, output: str, error: str = ""):
    finished = timezone.now()
    duration_ms = None
    if run.started_at:
        duration_ms = int((finished - run.started_at).total_seconds() * 1000)
    run.finished_at = finished
    run.duration_ms = duration_ms
    run.status = RiftboundOpsRun.STATUS_SUCCESS if ok else RiftboundOpsRun.STATUS_ERROR
    run.output = (output or "")[-10000:]
    run.error = (error or "")[:1500]
    run.save(update_fields=["finished_at", "duration_ms", "status", "output", "error"])


def _rb_serialize_ops_run(run: RiftboundOpsRun, include_output: bool = False) -> dict:
    payload = {
        "id": run.id,
        "kind": run.kind,
        "command": run.command,
        "status": run.status,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
        "duration_ms": run.duration_ms,
        "requested_by": run.requested_by.username if run.requested_by else None,
        "args": run.args if isinstance(run.args, dict) else {},
        "error": run.error,
        "output_excerpt": (run.output or "")[-500:],
    }
    if include_output:
        payload["output"] = run.output or ""
    return payload


def _rb_execute_ops_command(
    request,
    *,
    kind: str,
    command: str,
    kwargs: dict,
    rerun_of: int | None = None,
):
    out = io.StringIO()
    run_args = dict(kwargs or {})
    if rerun_of:
        run_args["rerun_of"] = rerun_of

    run = _rb_start_ops_run(
        kind=kind,
        command=command,
        request=request,
        args=run_args,
    )
    try:
        call_command(command, stdout=out, stderr=out, **kwargs)
        _rb_finish_ops_run(run, ok=True, output=out.getvalue())
    except Exception as exc:
        _rb_finish_ops_run(run, ok=False, output=out.getvalue(), error=str(exc))
        return Response(
            {
                "ok": False,
                "command": command,
                "run_id": run.id,
                "rerun_of": rerun_of,
                "error": str(exc),
                "output": out.getvalue()[-5000:],
            },
            status=500,
        )

    return Response(
        {
            "ok": True,
            "command": command,
            "run_id": run.id,
            "rerun_of": rerun_of,
            "output": out.getvalue()[-5000:],
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def riftcodex_run_sync_view(request):
    """Ejecuta sync_riftcodex_cards desde API (solo admin)."""
    if not _rb_is_admin(request.user):
        return Response({"detail": "No autorizado"}, status=403)

    payload = request.data or {}

    kwargs = {
        "full": bool(payload.get("full", False)),
        "dry_run": bool(payload.get("dry_run", False)),
        "skip_fixes": bool(payload.get("skip_fixes", False)),
        "size": int(payload.get("size", 100) or 100),
    }
    since = (payload.get("since") or "").strip()
    if since:
        kwargs["since"] = since
    return _rb_execute_ops_command(
        request,
        kind=RiftboundOpsRun.KIND_SYNC,
        command="sync_riftcodex_cards",
        kwargs=kwargs,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def riftcodex_run_audit_view(request):
    """Ejecuta audit_riftcodex_diff desde API (solo admin)."""
    if not _rb_is_admin(request.user):
        return Response({"detail": "No autorizado"}, status=403)

    payload = request.data or {}
    limit = int(payload.get("limit", 50) or 50)
    return _rb_execute_ops_command(
        request,
        kind=RiftboundOpsRun.KIND_AUDIT,
        command="audit_riftcodex_diff",
        kwargs={"limit": limit},
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def riftcodex_audit_export_csv_view(request):
    """Exporta ejemplos de auditoría a CSV (solo admin)."""
    if not _rb_is_admin(request.user):
        return Response({"detail": "No autorizado"}, status=403)

    state = RiftboundSyncState.objects.filter(provider="riftcodex", key="audit_cards").first()
    if not state or not isinstance(state.last_stats, dict):
        return Response({"detail": "No hay auditoría disponible."}, status=404)

    examples = (state.last_stats or {}).get("examples") or {}
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["category", "card_number", "name", "local", "remote", "type", "rarity", "set"])

    for category, rows in examples.items():
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            writer.writerow([
                category,
                row.get("card_number", ""),
                row.get("name", ""),
                row.get("local", ""),
                row.get("remote", ""),
                row.get("type", ""),
                row.get("rarity", ""),
                row.get("set", ""),
            ])

    resp = HttpResponse(output.getvalue(), content_type="text/csv; charset=utf-8")
    ts = timezone.now().strftime("%Y%m%d_%H%M%S")
    resp["Content-Disposition"] = f'attachment; filename="riftcodex_audit_{ts}.csv"'
    return resp


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def riftcodex_ops_overview_view(request):
    """Resumen operativo unificado (sync + audit + últimas ejecuciones)."""
    if not _rb_is_admin(request.user):
        return Response({"detail": "No autorizado"}, status=403)

    sync_state = RiftboundSyncState.objects.filter(provider="riftcodex", key="cards").first()
    audit_state = RiftboundSyncState.objects.filter(provider="riftcodex", key="audit_cards").first()
    sync_age_hours = None
    if sync_state and sync_state.last_success_at:
        sync_age_hours = round((timezone.now() - sync_state.last_success_at).total_seconds() / 3600, 2)
    kind_filter = (request.query_params.get("kind") or "").strip().lower()
    status_filter = (request.query_params.get("status") or "").strip().lower()
    search_q = (request.query_params.get("q") or "").strip()
    try:
        page = max(1, int(request.query_params.get("page", 1)))
    except ValueError:
        page = 1
    try:
        page_size = min(50, max(1, int(request.query_params.get("page_size", 10))))
    except ValueError:
        page_size = 10

    runs_qs = RiftboundOpsRun.objects.filter(provider="riftcodex").select_related("requested_by")
    if kind_filter in {RiftboundOpsRun.KIND_SYNC, RiftboundOpsRun.KIND_AUDIT}:
        runs_qs = runs_qs.filter(kind=kind_filter)
    if status_filter in {RiftboundOpsRun.STATUS_RUNNING, RiftboundOpsRun.STATUS_SUCCESS, RiftboundOpsRun.STATUS_ERROR}:
        runs_qs = runs_qs.filter(status=status_filter)
    if search_q:
        runs_qs = runs_qs.filter(
            Q(command__icontains=search_q)
            | Q(error__icontains=search_q)
            | Q(output__icontains=search_q)
            | Q(requested_by__username__icontains=search_q)
        )

    total_runs = runs_qs.count()
    start = (page - 1) * page_size
    end = start + page_size
    latest_runs = runs_qs[start:end]
    total_pages = max(1, (total_runs + page_size - 1) // page_size)

    return Response(
        {
            "sync": {
                "provider": "riftcodex",
                "key": "cards",
                "configured": bool(sync_state),
                "status": "never_run" if not sync_state else ("error" if sync_state.last_error else "ok"),
                "last_cursor": sync_state.last_cursor if sync_state else None,
                "last_success_at": sync_state.last_success_at if sync_state else None,
                "last_started_at": sync_state.last_started_at if sync_state else None,
                "last_success_age_hours": sync_age_hours,
                "last_stats": sync_state.last_stats if sync_state else {},
                "last_error": sync_state.last_error if sync_state else "",
            },
            "audit": {
                "provider": "riftcodex",
                "key": "audit_cards",
                "configured": bool(audit_state),
                "status": "never_run" if not audit_state else ("error" if audit_state.last_error else "ok"),
                "last_success_at": audit_state.last_success_at if audit_state else None,
                "last_started_at": audit_state.last_started_at if audit_state else None,
                "last_stats": audit_state.last_stats if audit_state else {},
                "last_error": audit_state.last_error if audit_state else "",
            },
            "runs": [
                _rb_serialize_ops_run(run, include_output=False)
                for run in latest_runs
            ],
            "runs_pagination": {
                "page": page,
                "page_size": page_size,
                "total": total_runs,
                "total_pages": total_pages,
                "has_prev": page > 1,
                "has_next": end < total_runs,
                "kind": kind_filter or None,
                "status": status_filter or None,
                "q": search_q or None,
            },
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def riftcodex_ops_run_detail_view(request, run_id: int):
    if not _rb_is_admin(request.user):
        return Response({"detail": "No autorizado"}, status=403)

    run = RiftboundOpsRun.objects.filter(provider="riftcodex", id=run_id).select_related("requested_by").first()
    if not run:
        return Response({"detail": "Run no encontrado"}, status=404)
    return Response(_rb_serialize_ops_run(run, include_output=True))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def riftcodex_ops_rerun_view(request, run_id: int):
    if not _rb_is_admin(request.user):
        return Response({"detail": "No autorizado"}, status=403)

    prev = RiftboundOpsRun.objects.filter(provider="riftcodex", id=run_id).first()
    if not prev:
        return Response({"detail": "Run no encontrado"}, status=404)

    args = prev.args if isinstance(prev.args, dict) else {}
    overrides = request.data if isinstance(request.data, dict) else {}

    def _to_int(value, default):
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _to_bool(value, default=False):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            v = value.strip().lower()
            if v in {"1", "true", "yes", "on"}:
                return True
            if v in {"0", "false", "no", "off"}:
                return False
        return default

    merged = {**args, **overrides}
    if prev.kind == RiftboundOpsRun.KIND_SYNC:
        size = max(1, min(100, _to_int(merged.get("size"), 100)))
        kwargs = {
            "full": _to_bool(merged.get("full", False), False),
            "dry_run": _to_bool(merged.get("dry_run", False), False),
            "skip_fixes": _to_bool(merged.get("skip_fixes", False), False),
            "size": size,
        }
        since = str(merged.get("since") or "").strip()
        if since:
            kwargs["since"] = since
        return _rb_execute_ops_command(
            request,
            kind=RiftboundOpsRun.KIND_SYNC,
            command="sync_riftcodex_cards",
            kwargs=kwargs,
            rerun_of=prev.id,
        )

    if prev.kind == RiftboundOpsRun.KIND_AUDIT:
        limit = max(1, min(500, _to_int(merged.get("limit"), 50)))
        kwargs = {"limit": limit}
        return _rb_execute_ops_command(
            request,
            kind=RiftboundOpsRun.KIND_AUDIT,
            command="audit_riftcodex_diff",
            kwargs=kwargs,
            rerun_of=prev.id,
        )

    return Response({"detail": "Tipo de operación no soportado para re-run"}, status=400)
