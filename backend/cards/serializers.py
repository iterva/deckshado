from rest_framework import serializers
from .models import Card, Edition, Format, Race, CardType, Rarity, BanlistEntry


class FormatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Format
        fields = ["id", "code", "name"]


class RaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Race
        fields = ["id", "myl_id", "slug", "name"]


class CardTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CardType
        fields = ["id", "myl_id", "slug", "name"]


class RaritySerializer(serializers.ModelSerializer):
    class Meta:
        model = Rarity
        fields = ["id", "myl_id", "slug", "name"]


class EditionSerializer(serializers.ModelSerializer):
    format_code = serializers.CharField(source="format.code", read_only=True, default=None)
    format_name = serializers.CharField(source="format.name", read_only=True, default=None)

    class Meta:
        model = Edition
        fields = ["id", "myl_id", "slug", "title", "image", "date_release", "date_empire_valid", "format_code", "format_name", "active"]


class CardListSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    is_unique = serializers.SerializerMethodField()
    edition_slug = serializers.CharField(source="edition.slug", read_only=True)
    edition_title = serializers.CharField(source="edition.title", read_only=True)
    rarity_name = serializers.CharField(source="rarity.name", read_only=True, default=None)
    race_name = serializers.CharField(source="race.name", read_only=True, default=None)
    race_slug = serializers.CharField(source="race.slug", read_only=True, default=None)
    type_name = serializers.CharField(source="card_type.name", read_only=True, default=None)

    class Meta:
        model = Card
        fields = [
            "id", "myl_id", "edid", "slug", "name",
            "edition_slug", "edition_title",
            "rarity_name", "race_name", "race_slug", "type_name",
            "cost", "damage", "ability", "is_unique",
            "image_url",
        ]

    def get_image_url(self, obj):
        # Prefer custom URL for promo/extra cards
        custom = getattr(obj, 'custom_image_url', None)
        if custom:
            return custom
        # Use annotated value if present, otherwise compute
        if hasattr(obj, '_image_url_cache'):
            return obj._image_url_cache
        val = getattr(obj, 'image_url', None)
        if val and not callable(val):
            return val
        return f"https://api.myl.cl/static/cards/{obj.edition.myl_id}/{obj.edid}.png"

    def get_is_unique(self, obj):
        val = getattr(obj, 'is_unique', None)
        if isinstance(val, bool):
            return val
        return bool(obj.ability and obj.ability.startswith("Única"))


class BanlistEntrySerializer(serializers.ModelSerializer):
    card_id = serializers.IntegerField(source="card.id", read_only=True, default=None)
    card_image_url = serializers.SerializerMethodField()

    class Meta:
        model = BanlistEntry
        fields = [
            "id", "card_name", "card_id", "card_image_url",
            "format_code", "sub_format",
            "status", "max_copies", "last_synced",
        ]

    def get_card_image_url(self, obj):
        if obj.card and obj.card.edition:
            return f"https://api.myl.cl/static/cards/{obj.card.edition.myl_id}/{obj.card.edid}.png"
        return None


class CardDetailSerializer(CardListSerializer):
    edition = EditionSerializer(read_only=True)
    rarity = RaritySerializer(read_only=True)
    race = RaceSerializer(read_only=True)
    card_type = CardTypeSerializer(read_only=True)

    class Meta(CardListSerializer.Meta):
        fields = [
            "id", "myl_id", "edid", "slug", "name",
            "edition", "rarity", "race", "card_type",
            "edition_slug", "edition_title",
            "rarity_name", "race_name", "race_slug", "type_name",
            "cost", "damage", "ability", "flavour",
            "image_url", "is_unique",
        ]
