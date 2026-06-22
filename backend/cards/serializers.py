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
        fallback = self._default_myl_image_url(obj)

        # Prefer custom URL for promo/extra cards
        custom = getattr(obj, 'custom_image_url', None)
        if custom:
            rewritten_url = self._rewrite_legacy_cloudinary_url(custom)
            if rewritten_url:
                return rewritten_url
            if self._should_fallback_from_non_r2(obj, custom) and fallback:
                return fallback
            return custom

        # Use annotated value if present, otherwise compute
        if hasattr(obj, '_image_url_cache'):
            cached = obj._image_url_cache
            if self._should_fallback_from_non_r2(obj, cached) and fallback:
                return fallback
            return cached

        val = getattr(obj, 'image_url', None)
        if val and not callable(val):
            rewritten_url = self._rewrite_legacy_cloudinary_url(val)
            if rewritten_url:
                return rewritten_url
            if self._should_fallback_from_non_r2(obj, val) and fallback:
                return fallback
            return val
        return fallback

    def _rewrite_legacy_cloudinary_url(self, url):
        """Map retired Cloudinary URLs to the active Cloudinary account.

        We only rewrite known migrated folders to avoid touching unrelated assets.
        """
        if not isinstance(url, str) or not url:
            return None
        lower = url.lower()
        legacy_prefix = "https://res.cloudinary.com/dmvu6tuee/"
        if legacy_prefix not in lower:
            return None

        migrated_markers = (
            "/deckshado/extra_cards/",
            "/deckshado/myl_cards/",
            "/primera_era/",
        )
        if not any(marker in lower for marker in migrated_markers):
            return None
        return url.replace("res.cloudinary.com/dmvu6tuee", "res.cloudinary.com/drw7y27sm")

    def _default_myl_image_url(self, obj):
        edition = getattr(obj, 'edition', None)
        edition_myl_id = getattr(edition, 'myl_id', None)
        edid = getattr(obj, 'edid', None)
        if edition_myl_id and edid:
            return f"https://api.myl.cl/static/cards/{edition_myl_id}/{edid}.png"
        return None

    def _should_fallback_from_non_r2(self, obj, url):
        if not isinstance(url, str) or not url:
            return False
        lower_url = url.lower()
        if self._is_r2_url(lower_url):
            return False
        # Keep Cloudinary for fully custom cards where MYL fallback may not exist.
        myl_id = str(getattr(obj, 'myl_id', '') or '')
        return not myl_id.startswith('custom_')

    def _is_r2_url(self, lower_url):
        if '.r2.dev/' in lower_url or '.r2.cloudflarestorage.com/' in lower_url:
            return True
        return False

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
