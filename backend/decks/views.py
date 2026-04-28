from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.db.models import Q, Sum, Value, Count
from django.db.models.functions import Coalesce
from .models import Deck, DeckEntry, DeckLike, DeckSnapshot, DeckComment
from .serializers import (
    DeckListSerializer, DeckDetailSerializer, DeckCreateSerializer,
    DeckEntrySerializer, DeckChangeLogSerializer, DeckCommentSerializer,
    DeckSnapshotSerializer,
)
from teams.models import TeamMember
from users.models import Notification


def _get_visible_deck(deck_id, user=None):
    """Return a deck if it's public, owned by user, or shared with user's team."""
    try:
        deck = Deck.objects.get(id=deck_id)
    except Deck.DoesNotExist:
        return None
    if deck.is_public:
        return deck
    if user and user.is_authenticated:
        if deck.owner == user:
            return deck
        if deck.shared_with_team:
            owner_team_ids = TeamMember.objects.filter(user=deck.owner).values_list("team_id", flat=True)
            if TeamMember.objects.filter(user=user, team_id__in=owner_team_ids).exists():
                return deck
    return None


def _annotate_card_count(qs):
    return qs.annotate(
        card_count=Coalesce(Sum("entries__quantity"), Value(0)),
        like_count=Count("likes", distinct=True),
    ).order_by("-updated_at")


class PublicDeckListView(generics.ListAPIView):
    """Lista de mazos públicos (no requiere autenticación)."""
    serializer_class = DeckListSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = _annotate_card_count(Deck.objects.filter(is_public=True).select_related("owner"))
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(owner__username__icontains=search))
        fmt = self.request.query_params.get("format")
        if fmt:
            qs = qs.filter(format=fmt)
        race = self.request.query_params.get("race")
        if race:
            qs = qs.filter(race=race)
        return qs


class MyDeckListView(generics.ListCreateAPIView):
    """Lista y creación de mazos del usuario autenticado."""
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return DeckCreateSerializer
        return DeckListSerializer

    def get_queryset(self):
        return _annotate_card_count(Deck.objects.filter(owner=self.request.user).select_related("owner"))

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class DeckDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Detalle, edición y eliminación de un mazo."""
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return DeckCreateSerializer
        return DeckDetailSerializer

    def get_queryset(self):
        return _annotate_card_count(Deck.objects.filter(owner=self.request.user).prefetch_related("entries__card__edition", "entries__card__rarity", "entries__card__race", "entries__card__card_type"))


class PublicDeckDetailView(generics.RetrieveAPIView):
    """Ver un mazo público (sin autenticación)."""
    serializer_class = DeckDetailSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return _annotate_card_count(Deck.objects.filter(is_public=True).prefetch_related("entries__card__edition", "entries__card__rarity", "entries__card__race", "entries__card__card_type"))


class TeamDeckListView(generics.ListAPIView):
    """Mazos compartidos con el equipo del usuario."""
    serializer_class = DeckListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        try:
            membership = TeamMember.objects.get(user=self.request.user)
        except TeamMember.DoesNotExist:
            return Deck.objects.none()
        teammate_ids = TeamMember.objects.filter(team=membership.team).values_list("user_id", flat=True)
        return _annotate_card_count(
            Deck.objects.filter(owner_id__in=teammate_ids, shared_with_team=True).select_related("owner")
        )


class TeamDeckDetailView(generics.RetrieveAPIView):
    """Ver un mazo compartido con el equipo (solo lectura)."""
    serializer_class = DeckDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        try:
            membership = TeamMember.objects.get(user=self.request.user)
        except TeamMember.DoesNotExist:
            return Deck.objects.none()
        teammate_ids = TeamMember.objects.filter(team=membership.team).values_list("user_id", flat=True)
        return _annotate_card_count(
            Deck.objects.filter(owner_id__in=teammate_ids, shared_with_team=True).prefetch_related("entries__card__edition", "entries__card__rarity", "entries__card__race", "entries__card__card_type")
        )


@api_view(["POST", "DELETE"])
@permission_classes([permissions.IsAuthenticated])
def deck_entry_view(request, deck_id):
    """Agregar o quitar una carta de un mazo."""
    try:
        deck = Deck.objects.get(id=deck_id, owner=request.user)
    except Deck.DoesNotExist:
        return Response({"error": "Mazo no encontrado"}, status=status.HTTP_404_NOT_FOUND)

    card_id = request.data.get("card_id")
    quantity = request.data.get("quantity", 1)

    if not card_id:
        return Response({"error": "card_id es requerido"}, status=status.HTTP_400_BAD_REQUEST)

    if request.method == "POST":
        entry, created = DeckEntry.objects.get_or_create(
            deck=deck, card_id=card_id,
            defaults={"quantity": quantity},
        )
        if not created:
            entry.quantity = quantity
            entry.save()
        return Response(DeckEntrySerializer(entry).data, status=status.HTTP_200_OK)

    elif request.method == "DELETE":
        deleted, _ = DeckEntry.objects.filter(deck=deck, card_id=card_id).delete()
        if deleted:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response({"error": "Entrada no encontrada"}, status=status.HTTP_404_NOT_FOUND)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def deck_changelog_view(request, deck_id):
    """Historial de cambios de un mazo."""
    from .models import DeckChangeLog
    try:
        deck = Deck.objects.get(id=deck_id, owner=request.user)
    except Deck.DoesNotExist:
        return Response({"error": "Mazo no encontrado"}, status=status.HTTP_404_NOT_FOUND)
    entries = DeckChangeLog.objects.filter(deck=deck)[:20]
    return Response(DeckChangeLogSerializer(entries, many=True).data)


# ── Likes ────────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def toggle_like(request, deck_id):
    """Toggle like on a visible deck."""
    deck = _get_visible_deck(deck_id, request.user)
    if not deck:
        return Response({"error": "Mazo no encontrado"}, status=status.HTTP_404_NOT_FOUND)
    existing = DeckLike.objects.filter(user=request.user, deck=deck).first()
    if existing:
        existing.delete()
        return Response({"liked": False, "like_count": deck.likes.count()})
    DeckLike.objects.create(user=request.user, deck=deck)
    # Notify deck owner (if not self)
    if deck.owner != request.user:
        Notification.objects.create(
            user=deck.owner,
            notif_type="deck_like",
            message=f"{request.user.username} le dio ♥ a tu mazo «{deck.name}»",
            link=f"/decks/{deck.id}",
        )
    return Response({"liked": True, "like_count": deck.likes.count()})


# ── Comments ─────────────────────────────────────────────

@api_view(["GET", "POST"])
def deck_comments_view(request, deck_id):
    """List or add comments on a visible deck."""
    deck = _get_visible_deck(deck_id, request.user if request.user.is_authenticated else None)
    if not deck:
        return Response({"error": "Mazo no encontrado"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        comments = DeckComment.objects.filter(deck=deck).select_related("user__profile")[:50]
        return Response(DeckCommentSerializer(comments, many=True, context={"request": request}).data)

    # POST — auth required
    if not request.user.is_authenticated:
        return Response({"error": "Debes iniciar sesión"}, status=status.HTTP_401_UNAUTHORIZED)
    text = (request.data.get("text") or "").strip()
    if not text:
        return Response({"error": "El comentario no puede estar vacío"}, status=status.HTTP_400_BAD_REQUEST)
    if len(text) > 1000:
        return Response({"error": "Máximo 1000 caracteres"}, status=status.HTTP_400_BAD_REQUEST)
    comment = DeckComment.objects.create(user=request.user, deck=deck, text=text)
    # Notify deck owner
    if deck.owner != request.user:
        Notification.objects.create(
            user=deck.owner,
            notif_type="deck_comment",
            message=f"{request.user.username} comentó en tu mazo «{deck.name}»",
            link=f"/decks/{deck.id}",
        )
    return Response(
        DeckCommentSerializer(comment, context={"request": request}).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(["DELETE"])
@permission_classes([permissions.IsAuthenticated])
def delete_comment(request, comment_id):
    """Delete own comment or deck owner deletes any."""
    try:
        comment = DeckComment.objects.select_related("deck").get(id=comment_id)
    except DeckComment.DoesNotExist:
        return Response({"error": "Comentario no encontrado"}, status=status.HTTP_404_NOT_FOUND)
    if comment.user != request.user and comment.deck.owner != request.user:
        return Response({"error": "No autorizado"}, status=status.HTTP_403_FORBIDDEN)
    comment.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


# ── Snapshots ────────────────────────────────────────────

@api_view(["GET", "POST"])
@permission_classes([permissions.IsAuthenticated])
def deck_snapshots_view(request, deck_id):
    """List or create snapshots of a deck."""
    try:
        deck = Deck.objects.get(id=deck_id, owner=request.user)
    except Deck.DoesNotExist:
        return Response({"error": "Mazo no encontrado"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        snaps = DeckSnapshot.objects.filter(deck=deck)[:20]
        return Response(DeckSnapshotSerializer(snaps, many=True).data)

    # POST — create snapshot
    label = (request.data.get("label") or "").strip()
    if not label:
        label = f"Versión {DeckSnapshot.objects.filter(deck=deck).count() + 1}"
    entries = list(deck.entries.values("card_id", "quantity", "is_sideboard"))
    snapshot_data = {
        "name": deck.name,
        "description": deck.description,
        "format": deck.format,
        "sub_format": deck.sub_format,
        "race": deck.race,
        "starting_gold": deck.starting_gold_id,
        "entries": entries,
    }
    snap = DeckSnapshot.objects.create(deck=deck, label=label, snapshot_data=snapshot_data)
    return Response(DeckSnapshotSerializer(snap).data, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def restore_snapshot(request, snapshot_id):
    """Restore a deck to a saved snapshot."""
    try:
        snap = DeckSnapshot.objects.select_related("deck").get(id=snapshot_id)
    except DeckSnapshot.DoesNotExist:
        return Response({"error": "Snapshot no encontrado"}, status=status.HTTP_404_NOT_FOUND)
    deck = snap.deck
    if deck.owner != request.user:
        return Response({"error": "No autorizado"}, status=status.HTTP_403_FORBIDDEN)
    data = snap.snapshot_data
    deck.name = data.get("name", deck.name)
    deck.description = data.get("description", deck.description)
    deck.format = data.get("format", deck.format)
    deck.sub_format = data.get("sub_format", deck.sub_format)
    deck.race = data.get("race", deck.race)
    deck.starting_gold_id = data.get("starting_gold")
    deck.save()
    deck.entries.all().delete()
    for e in data.get("entries", []):
        DeckEntry.objects.create(deck=deck, card_id=e["card_id"], quantity=e["quantity"], is_sideboard=e.get("is_sideboard", False))
    from .models import DeckChangeLog
    DeckChangeLog.objects.create(deck=deck, summary=f"Restaurado desde snapshot: {snap.label}")
    return Response({"detail": "Mazo restaurado"})


# ── Suggestions ──────────────────────────────────────────

@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def card_suggestions(request, deck_id):
    """Suggest popular cards from other public decks with same format+race."""
    try:
        deck = Deck.objects.get(id=deck_id, owner=request.user)
    except Deck.DoesNotExist:
        return Response({"error": "Mazo no encontrado"}, status=status.HTTP_404_NOT_FOUND)
    # Current card IDs in this deck
    current_ids = set(deck.entries.values_list("card_id", flat=True))
    # Find cards from similar public decks
    similar = Deck.objects.filter(
        is_public=True, format=deck.format, race=deck.race,
    ).exclude(id=deck.id)
    from django.db.models import Count as DjCount
    popular = (
        DeckEntry.objects.filter(deck__in=similar)
        .exclude(card_id__in=current_ids)
        .values("card_id")
        .annotate(freq=DjCount("id"))
        .order_by("-freq")[:15]
    )
    from cards.models import Card
    from cards.serializers import CardListSerializer as CLS
    card_ids = [p["card_id"] for p in popular]
    cards = Card.objects.filter(id__in=card_ids).select_related("edition", "rarity", "race", "card_type")
    freq_map = {p["card_id"]: p["freq"] for p in popular}
    result = []
    for c in cards:
        data = CLS(c).data
        data["popularity"] = freq_map.get(c.id, 0)
        result.append(data)
    result.sort(key=lambda x: -x["popularity"])
    return Response(result)
