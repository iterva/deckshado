from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.db.models import Q, Sum, Value
from django.db.models.functions import Coalesce
from .models import Deck, DeckEntry
from .serializers import DeckListSerializer, DeckDetailSerializer, DeckCreateSerializer, DeckEntrySerializer, DeckChangeLogSerializer
from teams.models import TeamMember


def _annotate_card_count(qs):
    return qs.annotate(card_count=Coalesce(Sum("entries__quantity"), Value(0))).order_by("-updated_at")


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
