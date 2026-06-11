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
    RiftboundIcon,
    ZONE_CHAMPION,
    ZONE_BATTLEFIELD,
    ZONE_MAIN,
    ZONE_SIDE,
    ZONE_RUNE,
)


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
        return obj.image_url or obj.cdn_image_url or obj.image_url_small or ""


class RiftboundCardLiteSerializer(serializers.ModelSerializer):
    """Versión compacta para listados grandes."""
    image = serializers.SerializerMethodField()

    class Meta:
        model = RiftboundCard
        fields = [
            "id", "card_number", "name", "card_type", "rarity",
            "colors", "energy", "power", "might", "image",
            "description", "subtypes",
        ]

    def get_image(self, obj):
        return obj.image_url or obj.cdn_image_url or obj.image_url_small or ""


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
        return c.image_url or c.cdn_image_url or c.image_url_small or ""


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
            "username", "share_token", "binder_avatar", "binder_avatar_url",
            "user_avatar_url",
            "store_slug", "is_store_public", "display_name", "bio",
            "city", "country", "whatsapp", "instagram", "discord",
            "email_public", "payment_methods", "shipping_info",
            "accepts_trades", "last_active",
        ]
        read_only_fields = ["store_slug", "last_active"]

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
        return obj.cdn_image_url or obj.image_url
