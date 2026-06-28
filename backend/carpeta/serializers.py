from rest_framework import serializers
from .models import BinderProfile, CollectionEntry, WishlistEntry, StoreOrder, StoreOrderItem
from cards.serializers import CardListSerializer


def _clean_avatar_url(url):
    if not isinstance(url, str) or not url:
        return None
    lower = url.lower()
    if "res.cloudinary.com/dmvu6tuee/" in lower:
        return None
    return url


class BinderProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    binder_avatar_url = serializers.SerializerMethodField()
    share_token = serializers.UUIDField(read_only=True)
    country_display = serializers.CharField(source="get_country_display", read_only=True)

    class Meta:
        model = BinderProfile
        fields = [
            "id", "username", "binder_avatar_url", "share_token",
            "store_slug", "is_store_public",
            "display_name", "bio", "city", "country", "country_display",
            "whatsapp", "instagram", "discord", "email_public",
            "payment_methods", "shipping_info", "accepts_trades",
        ]
        read_only_fields = ["share_token", "store_slug", "binder_avatar_url"]

    def get_binder_avatar_url(self, obj):
        return _clean_avatar_url(obj.binder_avatar)


class PublicBinderProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    binder_avatar_url = serializers.SerializerMethodField()
    user_avatar_url = serializers.SerializerMethodField()
    country_display = serializers.CharField(source="get_country_display", read_only=True)
    selling_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = BinderProfile
        fields = [
            "username", "store_slug", "binder_avatar_url", "user_avatar_url",
            "display_name", "bio", "city", "country", "country_display",
            "whatsapp", "instagram", "discord", "email_public",
            "payment_methods", "shipping_info", "accepts_trades",
            "last_active", "selling_count",
        ]

    def get_binder_avatar_url(self, obj):
        return _clean_avatar_url(obj.binder_avatar)

    def get_user_avatar_url(self, obj):
        profile = getattr(obj.user, "profile", None)
        if profile and getattr(profile, "avatar", None):
            return _clean_avatar_url(profile.avatar)
        return None


class CollectionEntrySerializer(serializers.ModelSerializer):
    card_detail = CardListSerializer(source="card", read_only=True)
    condition_display = serializers.CharField(source="get_condition_display", read_only=True)
    language_display = serializers.CharField(source="get_language_display", read_only=True)
    in_my_wishlist = serializers.SerializerMethodField()

    class Meta:
        model = CollectionEntry
        fields = [
            "id", "card", "quantity", "price", "selling_quantity",
            "condition", "condition_display", "language", "language_display",
            "is_foil", "notes", "photo_url", "photo_url_2", "card_detail", "in_my_wishlist",
        ]
        extra_kwargs = {"card": {"write_only": True}}

    def get_in_my_wishlist(self, obj):
        wl_ids = self.context.get("viewer_wishlist_ids")
        if not wl_ids:
            return False
        return obj.card_id in wl_ids


class CollectionEntryWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = CollectionEntry
        fields = [
            "card", "quantity", "price", "selling_quantity",
            "condition", "language", "is_foil", "notes", "photo_url", "photo_url_2",
        ]


class WishlistEntrySerializer(serializers.ModelSerializer):
    card_detail = CardListSerializer(source="card", read_only=True)

    class Meta:
        model = WishlistEntry
        fields = ["id", "card", "desired_quantity", "card_detail"]
        extra_kwargs = {"card": {"write_only": True}}


class WishlistEntryWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = WishlistEntry
        fields = ["card", "desired_quantity"]


class StoreOrderItemSerializer(serializers.ModelSerializer):
    card_detail = CardListSerializer(source="card", read_only=True)

    class Meta:
        model = StoreOrderItem
        fields = [
            "id",
            "collection_entry",
            "card",
            "card_detail",
            "quantity",
            "unit_price",
            "line_total",
            "card_name",
            "card_edid",
            "language",
            "is_foil",
        ]


class StoreOrderSerializer(serializers.ModelSerializer):
    items = StoreOrderItemSerializer(many=True, read_only=True)
    buyer_username = serializers.CharField(source="buyer_user.username", read_only=True)
    store_owner = serializers.CharField(source="store_profile.user.username", read_only=True)
    total_items = serializers.SerializerMethodField()

    class Meta:
        model = StoreOrder
        fields = [
            "id",
            "store_profile",
            "store_owner",
            "buyer_user",
            "buyer_username",
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


class StoreOrderCreateItemSerializer(serializers.Serializer):
    entry_id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1, max_value=999)


class StoreOrderCreateSerializer(serializers.Serializer):
    buyer_name = serializers.CharField(required=True, allow_blank=False, max_length=100)
    buyer_whatsapp = serializers.CharField(required=True, allow_blank=False, max_length=30)
    buyer_note = serializers.CharField(required=False, allow_blank=True, max_length=800)
    items = StoreOrderCreateItemSerializer(many=True, allow_empty=False)
