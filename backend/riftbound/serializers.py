import os

from rest_framework import serializers

from .models import (
    RiftboundCard,
    RiftboundSet,
    RiftboundFormat,
    RiftboundBanlistEntry,
    RiftboundDeck,
    RiftboundDeckEntry,
    RiftboundCollectionEntry,
    RiftboundWishlistEntry,
    RiftboundBinderProfile,
    RiftboundStoreOrder,
    RiftboundStoreOrderItem,
    RiftboundIcon,
    ZONE_CHAMPION,
    RiftboundStorePermission,
    ZONE_BATTLEFIELD,
    ZONE_MAIN,
    ZONE_SIDE,
    ZONE_RUNE,
)


def _imagekit_endpoints() -> list[str]:
    endpoints: list[str] = []

    primary = (os.environ.get("IMAGEKIT_URL_ENDPOINT") or "").strip().rstrip("/")
    if primary:
        endpoints.append(primary)

    csv_endpoints = (os.environ.get("IMAGEKIT_URL_ENDPOINTS") or "").strip()
    if csv_endpoints:
        for endpoint in csv_endpoints.split(","):
            clean = endpoint.strip().rstrip("/")
            if clean:
                endpoints.append(clean)

    # Remove duplicates while preserving order.
    return list(dict.fromkeys(endpoints))


def _is_imagekit_url(url: str) -> bool:
    value = (url or "").strip()
    if not value:
        return False

    if "ik.imagekit.io/" in value:
        return True

    for endpoint in _imagekit_endpoints():
        if value.startswith(endpoint + "/") or value == endpoint:
            return True

    return False


def _preferred_riftbound_image(cdn_url: str, image_url: str, image_url_small: str = "") -> str:
    # Riftbound should serve ImageKit when available.
    if _is_imagekit_url(cdn_url):
        return cdn_url
    if _is_imagekit_url(image_url):
        return image_url
    if _is_imagekit_url(image_url_small):
        return image_url_small

    # Fallback to upstream API URLs while migration finishes.
    return image_url or image_url_small or ""


class RiftboundSetSerializer(serializers.ModelSerializer):
    class Meta:
        model = RiftboundSet
        fields = ["id", "code", "name", "release_date"]


class RiftboundCardSerializer(serializers.ModelSerializer):
    set = RiftboundSetSerializer(read_only=True)
    image = serializers.SerializerMethodField()

    class Meta:
        model = RiftboundCard
        fields = [
            "id", "card_number", "external_id", "name", "slug",
            "set", "card_type", "supertype", "subtypes", "rarity", "variant",
            "colors", "energy", "power", "might",
            "description", "flavor",
            "image_url", "image_url_small", "cdn_image_url", "image",
            "is_active",
        ]

    def get_image(self, obj):
        return _preferred_riftbound_image(obj.cdn_image_url, obj.image_url, obj.image_url_small)


class RiftboundCardLiteSerializer(serializers.ModelSerializer):
    """Versión compacta para listados grandes."""
    image = serializers.SerializerMethodField()

    class Meta:
        model = RiftboundCard
        fields = [
            "id", "card_number", "name", "card_type", "rarity",
            "colors", "energy", "power", "might",
            "image", "image_url", "image_url_small", "cdn_image_url",
            "description", "subtypes",
        ]

    def get_image(self, obj):
        return _preferred_riftbound_image(obj.cdn_image_url, obj.image_url, obj.image_url_small)


class RiftboundFormatSerializer(serializers.ModelSerializer):
    class Meta:
        model = RiftboundFormat
        fields = ["id", "code", "name", "is_active"]


class RiftboundBanlistEntrySerializer(serializers.ModelSerializer):
    card_name = serializers.CharField(source="card.name", read_only=True)
    card_number = serializers.CharField(source="card.card_number", read_only=True)
    card_type = serializers.CharField(source="card.card_type", read_only=True)
    card_image = serializers.SerializerMethodField()
    format_code = serializers.CharField(source="format.code", read_only=True)

    class Meta:
        model = RiftboundBanlistEntry
        fields = [
            "id", "card", "card_name", "card_number", "card_type", "card_image",
            "format", "format_code",
            "status", "max_copies", "note", "effective_from",
        ]

    def get_card_image(self, obj):
        c = obj.card
        return _preferred_riftbound_image(c.cdn_image_url, c.image_url, c.image_url_small)


# ───────────── Decks ─────────────


class RiftboundDeckEntrySerializer(serializers.ModelSerializer):
    card_data = RiftboundCardLiteSerializer(source="card", read_only=True)

    class Meta:
        model = RiftboundDeckEntry
        fields = ["id", "card", "card_data", "quantity", "zone"]


class RiftboundDeckSerializer(serializers.ModelSerializer):
    entries = RiftboundDeckEntrySerializer(many=True, required=False)
    owner_username = serializers.CharField(source="owner.username", read_only=True)
    cover_card_data = RiftboundCardLiteSerializer(source="cover_card", read_only=True)
    champion_unit_data = RiftboundCardLiteSerializer(source="champion_unit", read_only=True)
    validation = serializers.SerializerMethodField()

    class Meta:
        model = RiftboundDeck
        fields = [
            "id", "name", "description", "format", "is_public",
            "primary_colors", "cover_card", "cover_card_data",
            "champion_unit", "champion_unit_data",
            "owner", "owner_username",
            "entries", "validation",
            "created_at", "updated_at",
        ]
        read_only_fields = ["owner", "created_at", "updated_at"]

    def get_validation(self, obj):
        from .validation import validate_riftbound_deck
        return validate_riftbound_deck(obj)

    def create(self, validated_data):
        entries = validated_data.pop("entries", [])
        deck = RiftboundDeck.objects.create(**validated_data)
        for e in entries:
            RiftboundDeckEntry.objects.create(deck=deck, **e)
        return deck

    def update(self, instance, validated_data):
        entries = validated_data.pop("entries", None)
        for k, v in validated_data.items():
            setattr(instance, k, v)
        instance.save()
        if entries is not None:
            instance.entries.all().delete()
            for e in entries:
                RiftboundDeckEntry.objects.create(deck=instance, **e)
        return instance


# ───────────── Carpeta ─────────────


class RiftboundCollectionEntrySerializer(serializers.ModelSerializer):
    card_data = RiftboundCardLiteSerializer(source="card", read_only=True)

    class Meta:
        model = RiftboundCollectionEntry
        fields = [
            "id", "card", "card_data", "quantity",
            "price", "selling_quantity", "condition", "language",
            "is_foil", "notes", "photo_url", "photo_url_2",
        ]


class RiftboundBinderProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    share_token = serializers.UUIDField(read_only=True)
    binder_avatar_url = serializers.CharField(source="binder_avatar", read_only=True)
    user_avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = RiftboundBinderProfile
        fields = [
            "id", "username", "share_token", "binder_avatar", "binder_avatar_url",
            "user_avatar_url",
            "store_slug", "is_store_public", "display_name", "bio",
            "city", "country", "whatsapp", "instagram", "discord",
            "email_public", "payment_methods", "shipping_info",
            "accepts_trades", "last_active",
        ]
        read_only_fields = ["id", "store_slug", "last_active"]

    def get_user_avatar_url(self, obj):
        # Si el usuario tiene un avatar global, lo devolvemos; si no, vacío.
        avatar = getattr(obj.user, "avatar", None) or getattr(obj.user, "avatar_url", None)
        if hasattr(avatar, "url"):
            try:
                return avatar.url
            except Exception:
                return ""
        return avatar or ""


class RiftboundPublicBinderProfileSerializer(RiftboundBinderProfileSerializer):
    selling_count = serializers.IntegerField(read_only=True, required=False)

    class Meta(RiftboundBinderProfileSerializer.Meta):
        fields = RiftboundBinderProfileSerializer.Meta.fields + ["selling_count"]


class RiftboundWishlistEntrySerializer(serializers.ModelSerializer):
    card_data = RiftboundCardLiteSerializer(source="card", read_only=True)

    class Meta:
        model = RiftboundWishlistEntry
        fields = ["id", "card", "card_data", "desired_quantity"]


class RiftboundIconSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = RiftboundIcon
        fields = ["id", "kind", "code", "label", "image_url", "cdn_image_url", "image"]

    def get_image(self, obj):
        return _preferred_riftbound_image(obj.cdn_image_url, obj.image_url)


class RiftboundStoreOrderItemSerializer(serializers.ModelSerializer):
    card_data = RiftboundCardLiteSerializer(source="card", read_only=True)

    class Meta:
        model = RiftboundStoreOrderItem
        fields = [
            "id",
            "collection_entry",
            "card",
            "card_data",
            "quantity",
            "unit_price",
            "line_total",
            "card_name",
            "card_number",
            "language",
            "is_foil",
        ]


class RiftboundStoreOrderSerializer(serializers.ModelSerializer):
    items = RiftboundStoreOrderItemSerializer(many=True, read_only=True)
    buyer_username = serializers.CharField(source="buyer_user.username", read_only=True)
    responded_by_username = serializers.CharField(source="responded_by.username", read_only=True)
    store_owner = serializers.CharField(source="store_profile.user.username", read_only=True)
    total_items = serializers.SerializerMethodField()

    class Meta:
        model = RiftboundStoreOrder
        fields = [
            "id",
            "store_profile",
            "store_owner",
            "buyer_user",
            "buyer_username",
            "responded_by",
            "responded_by_username",
            "buyer_name",
            "buyer_whatsapp",
            "buyer_note",
            "seller_note",
            "status",
            "total_estimated",
            "total_items",
            "responded_at",
            "created_at",
            "updated_at",
            "items",
        ]
        read_only_fields = [
            "id",
            "store_profile",
            "store_owner",
            "buyer_user",
            "buyer_username",
            "responded_by",
            "responded_by_username",
            "status",
            "total_estimated",
            "total_items",
            "responded_at",
            "created_at",
            "updated_at",
            "items",
        ]

    def get_total_items(self, obj):
        return sum((it.quantity or 0) for it in obj.items.all())


class RiftboundStoreOrderCreateItemSerializer(serializers.Serializer):
    entry_id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1, max_value=999)


class RiftboundStoreOrderCreateSerializer(serializers.Serializer):
    buyer_name = serializers.CharField(required=False, allow_blank=True, max_length=100)
    buyer_whatsapp = serializers.CharField(required=False, allow_blank=True, max_length=30)
    buyer_note = serializers.CharField(required=False, allow_blank=True, max_length=800)
    items = RiftboundStoreOrderCreateItemSerializer(many=True, allow_empty=False)

class RiftboundStorePermissionSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    granted_by_username = serializers.CharField(source="granted_by.username", read_only=True)
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = RiftboundStorePermission
        fields = [
            "id",
            "store_profile",
            "user_id",
            "username",
            "granted_by",
            "granted_by_username",
            "permissions",
            "can_view_collection",
            "can_edit_collection",
            "can_delete_collection",
            "can_edit_market",
            "can_remove_from_market",
            "can_view_orders",
            "can_view_history",
            "can_accept_orders",
            "can_reject_orders",
            "can_manage_permissions",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "store_profile",
            "user_id",
            "username",
            "granted_by",
            "granted_by_username",
            "permissions",
            "created_at",
            "updated_at",
        ]

    def get_permissions(self, obj):
        return obj.permissions_dict()
