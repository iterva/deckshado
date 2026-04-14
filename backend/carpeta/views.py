from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from django.db.models import Q
from django.shortcuts import get_object_or_404
from .models import BinderProfile, CollectionEntry, WishlistEntry
from .serializers import (
    BinderProfileSerializer,
    CollectionEntrySerializer,
    CollectionEntryWriteSerializer,
    WishlistEntrySerializer,
    WishlistEntryWriteSerializer,
)


class CarpetaPagination(PageNumberPagination):
    page_size = 40


# ── Binder Profile ──────────────────────────────────────

@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def binder_profile_view(request):
    profile, _ = BinderProfile.objects.get_or_create(user=request.user)
    return Response(BinderProfileSerializer(profile, context={"request": request}).data)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def upload_binder_avatar(request):
    avatar = request.FILES.get("binder_avatar")
    if not avatar:
        return Response({"detail": "No se envió ninguna imagen."}, status=status.HTTP_400_BAD_REQUEST)
    if avatar.size > 2 * 1024 * 1024:
        return Response({"detail": "La imagen no puede pesar más de 2MB."}, status=status.HTTP_400_BAD_REQUEST)
    if not avatar.content_type.startswith("image/"):
        return Response({"detail": "El archivo debe ser una imagen."}, status=status.HTTP_400_BAD_REQUEST)
    profile, _ = BinderProfile.objects.get_or_create(user=request.user)
    if profile.binder_avatar:
        profile.binder_avatar.delete(save=False)
    profile.binder_avatar = avatar
    profile.save()
    return Response(BinderProfileSerializer(profile, context={"request": request}).data)


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


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def collection_upsert(request):
    """Añadir o actualizar una carta en la colección."""
    card_id = request.data.get("card")
    if not card_id:
        return Response({"detail": "card es requerido."}, status=status.HTTP_400_BAD_REQUEST)

    entry, created = CollectionEntry.objects.get_or_create(
        user=request.user, card_id=card_id,
        defaults={
            "quantity": request.data.get("quantity", 1),
            "price": request.data.get("price"),
            "selling_quantity": request.data.get("selling_quantity", 0),
        },
    )
    if not created:
        if "quantity" in request.data:
            entry.quantity = int(request.data["quantity"])
        if "price" in request.data:
            entry.price = request.data["price"]
        if "selling_quantity" in request.data:
            entry.selling_quantity = int(request.data["selling_quantity"])
        entry.save()

    entry = CollectionEntry.objects.select_related(
        "card__edition", "card__rarity", "card__race", "card__card_type"
    ).get(pk=entry.pk)
    return Response(CollectionEntrySerializer(entry).data, status=status.HTTP_200_OK)


@api_view(["DELETE"])
@permission_classes([permissions.IsAuthenticated])
def collection_delete(request, card_id):
    """Eliminar una carta de la colección."""
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
    """Añadir o quitar una carta de la wishlist (toggle)."""
    card_id = request.data.get("card")
    if not card_id:
        return Response({"detail": "card es requerido."}, status=status.HTTP_400_BAD_REQUEST)

    existing = WishlistEntry.objects.filter(user=request.user, card_id=card_id).first()
    if existing:
        existing.delete()
        return Response({"wishlisted": False}, status=status.HTTP_200_OK)

    entry = WishlistEntry.objects.create(
        user=request.user,
        card_id=card_id,
        desired_quantity=request.data.get("desired_quantity", 1),
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
    """Actualizar la cantidad deseada de una carta en la wishlist."""
    try:
        entry = WishlistEntry.objects.get(user=request.user, card_id=card_id)
    except WishlistEntry.DoesNotExist:
        return Response({"detail": "Entrada no encontrada."}, status=status.HTTP_404_NOT_FOUND)

    desired = request.data.get("desired_quantity")
    if desired is not None:
        entry.desired_quantity = int(desired)
        entry.save()

    entry = WishlistEntry.objects.select_related(
        "card__edition", "card__rarity", "card__race", "card__card_type"
    ).get(pk=entry.pk)
    return Response(WishlistEntrySerializer(entry).data)


# ── Bulk IDs (for Codex heart/collection status) ────────

@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def my_ids(request):
    """Retorna los IDs de cartas en colección y wishlist del usuario."""
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
    """Actualizar múltiples entradas de la colección de una sola vez."""
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
            defaults={
                "quantity": item.get("quantity", 1),
                "price": item.get("price"),
                "selling_quantity": item.get("selling_quantity", 0),
            },
        )
        if not created:
            changed = False
            if "quantity" in item:
                entry.quantity = int(item["quantity"])
                changed = True
            if "price" in item:
                entry.price = item["price"]
                changed = True
            if "selling_quantity" in item:
                entry.selling_quantity = int(item["selling_quantity"])
                changed = True
            if changed:
                entry.save()
        updated += 1
    return Response({"updated": updated})


# ── Public Store (Tienda) ────────────────────────────────

class PublicStoreListView(generics.ListAPIView):
    """Cartas en venta de un usuario, accesible públicamente mediante share_token."""
    serializer_class = CollectionEntrySerializer
    pagination_class = CarpetaPagination
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        token = self.kwargs["token"]
        profile = get_object_or_404(BinderProfile, share_token=token)
        qs = CollectionEntry.objects.filter(
            user=profile.user, selling_quantity__gt=0
        ).select_related(
            "card__edition", "card__rarity", "card__race", "card__card_type"
        )
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(card__name__icontains=search)
        return qs

    def list(self, request, *args, **kwargs):
        token = self.kwargs["token"]
        profile = get_object_or_404(BinderProfile, share_token=token)
        response = super().list(request, *args, **kwargs)
        response.data["store_owner"] = profile.user.username
        if hasattr(profile.user, "profile") and profile.user.profile.avatar:
            response.data["store_avatar"] = request.build_absolute_uri(profile.user.profile.avatar.url)
        else:
            response.data["store_avatar"] = None
        if profile.binder_avatar:
            response.data["store_binder_avatar"] = request.build_absolute_uri(profile.binder_avatar.url)
        else:
            response.data["store_binder_avatar"] = None
        return response


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def my_share_token(request):
    """Retorna el share_token del usuario autenticado."""
    profile, _ = BinderProfile.objects.get_or_create(user=request.user)
    return Response({"share_token": str(profile.share_token)})
