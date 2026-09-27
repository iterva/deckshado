import re
import unicodedata
from collections import defaultdict

from django.db import transaction
from rest_framework import serializers
from cards.models import BanlistEntry, Format
from .models import Deck, DeckEntry, DeckChangeLog, DeckLike, DeckSnapshot, DeckComment
from cards.serializers import CardListSerializer


ESC_EDITION_SLUGS = {
    "bushido",
    "sol-naciente",
    "dominio",
    "contraataque",
    "aguila-imperial",
    "steampunk",
    "axis-mundi",
    "hijos-del-sol",
    "legado-gotico",
    "escuelas_elementales",
    "heroes_de_dharma",
}


# Hard limits mirrored from the Angular builder (deck-builder.component.ts).
MAIN_DECK_MAX = 50
SIDEBOARD_MAX = 15
DEFAULT_MAX_COPIES = 3
SUB_FORMATS = {"racial", "vcr", ""}
RACE_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _normalize_card_name(name):
    """Same normalization as `normalizeName` in the deck builder."""
    name = re.sub(r"\(v\d+\)", "", name or "", flags=re.IGNORECASE)
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", name).strip()


class DeckEntrySerializer(serializers.ModelSerializer):
    card_detail = CardListSerializer(source="card", read_only=True)
    quantity = serializers.IntegerField(min_value=1, max_value=32767)

    class Meta:
        model = DeckEntry
        fields = ["id", "card", "quantity", "is_sideboard", "card_detail"]


class DeckListSerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(source="owner.username", read_only=True)
    card_count = serializers.IntegerField(read_only=True)
    like_count = serializers.IntegerField(read_only=True, default=0)
    cover_card_detail = CardListSerializer(source="cover_card", read_only=True)
    cover_preview = serializers.SerializerMethodField()

    class Meta:
        model = Deck
        fields = ["id", "name", "description", "is_public", "shared_with_team", "owner_username", "card_count", "like_count", "format", "sub_format", "race", "pb_edition", "starting_gold", "cover_card", "cover_card_detail", "cover_preview", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]

    def get_cover_preview(self, obj):
        """Up to 3 cards as a fallback mosaic when no cover is set.
        Picks one of each main type if available."""
        if obj.cover_card_id:
            return []
        seen_types = set()
        result = []
        for entry in obj.entries.filter(is_sideboard=False).select_related("card", "card__card_type").order_by("-quantity")[:30]:
            t = entry.card.card_type_id
            if t in seen_types:
                continue
            seen_types.add(t)
            result.append(CardListSerializer(entry.card).data)
            if len(result) >= 3:
                break
        # If we didn't fill 3 slots by type, fill with whatever else
        if len(result) < 3:
            existing_ids = {c["id"] for c in result}
            for entry in obj.entries.filter(is_sideboard=False).select_related("card")[:3 - len(result) + len(existing_ids)]:
                if entry.card_id in existing_ids:
                    continue
                result.append(CardListSerializer(entry.card).data)
                if len(result) >= 3:
                    break
        return result


class DeckDetailSerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(source="owner.username", read_only=True)
    entries = serializers.SerializerMethodField()
    sideboard_entries = serializers.SerializerMethodField()
    card_count = serializers.IntegerField(read_only=True)
    like_count = serializers.IntegerField(read_only=True, default=0)
    user_liked = serializers.SerializerMethodField()
    starting_gold_detail = CardListSerializer(source="starting_gold", read_only=True)
    cover_card_detail = CardListSerializer(source="cover_card", read_only=True)
    comment_count = serializers.SerializerMethodField()

    class Meta:
        model = Deck
        fields = ["id", "name", "description", "is_public", "shared_with_team", "owner_username", "card_count", "like_count", "user_liked", "comment_count", "format", "sub_format", "race", "pb_edition", "starting_gold", "starting_gold_detail", "cover_card", "cover_card_detail", "entries", "sideboard_entries", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]

    def get_user_liked(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return DeckLike.objects.filter(user=request.user, deck=obj).exists()
        return False

    def get_comment_count(self, obj):
        return obj.comments.count()

    def get_entries(self, obj):
        qs = obj.entries.filter(is_sideboard=False)
        return DeckEntrySerializer(qs, many=True).data

    def get_sideboard_entries(self, obj):
        qs = obj.entries.filter(is_sideboard=True)
        return DeckEntrySerializer(qs, many=True).data


class DeckCreateSerializer(serializers.ModelSerializer):
    entries = DeckEntrySerializer(many=True, required=False)

    class Meta:
        model = Deck
        fields = ["id", "name", "description", "is_public", "shared_with_team", "format", "sub_format", "race", "pb_edition", "starting_gold", "cover_card", "entries"]

    def validate_format(self, value):
        if not Format.objects.filter(code=value).exists():
            raise serializers.ValidationError(f"Formato desconocido: '{value}'.")
        return value

    def validate_sub_format(self, value):
        if value not in SUB_FORMATS:
            raise serializers.ValidationError("Sub-formato inválido (racial o vcr).")
        return value

    def validate_race(self, value):
        if value and not RACE_SLUG_RE.match(value):
            raise serializers.ValidationError("Raza inválida.")
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)

        entries_data = attrs.get("entries")
        if entries_data is None:
            return attrs

        current_fmt = attrs.get("format")
        if not current_fmt and self.instance is not None:
            current_fmt = self.instance.format
        current_fmt = current_fmt or "imp"

        invalid_cards = []
        for entry in entries_data:
            card = entry.get("card")
            if card is None:
                continue
            if not self._card_matches_deck_format(card, current_fmt):
                invalid_cards.append(card.name)

        if invalid_cards:
            preview = ", ".join(sorted(set(invalid_cards))[:8])
            raise serializers.ValidationError({
                "entries": (
                    f"Hay cartas fuera del formato '{current_fmt}'. "
                    f"Revisa: {preview}."
                )
            })

        sub_format = attrs.get("sub_format")
        if sub_format is None and self.instance is not None:
            sub_format = self.instance.sub_format
        rule_errors = self._deck_rule_errors(entries_data, current_fmt, sub_format)
        if rule_errors:
            raise serializers.ValidationError({"entries": rule_errors})

        return attrs

    def _deck_rule_errors(self, entries_data, deck_format, sub_format):
        """Hard limits that are never valid, not even in a draft. An incomplete
        deck (<50 cards) is still allowed. Race restrictions are enforced only in
        the builder: they depend on per-card race/ability heuristics that change
        with the data and would block editing legacy decks."""
        errors = []
        main_total = sum(e["quantity"] for e in entries_data if not e.get("is_sideboard"))
        side_total = sum(e["quantity"] for e in entries_data if e.get("is_sideboard"))
        if main_total > MAIN_DECK_MAX:
            errors.append(f"El mazo principal tiene {main_total} cartas (máximo {MAIN_DECK_MAX}).")
        if side_total > SIDEBOARD_MAX:
            errors.append(f"El sidedeck tiene {side_total} cartas (máximo {SIDEBOARD_MAX}).")

        bans = BanlistEntry.objects.filter(format_code=deck_format)
        if sub_format:
            bans = bans.filter(sub_format=sub_format)
        ban_by_card_id, ban_by_name = {}, {}
        for ban in bans:
            ban_by_name[_normalize_card_name(ban.card_name)] = ban.max_copies
            if ban.card_id:
                ban_by_card_id[ban.card_id] = ban.max_copies

        # Copies are counted per normalized name (main + side, all versions) and the
        # limit is the strictest one among the versions present, like the builder.
        copies = defaultdict(int)
        limits = {}
        names = {}
        for entry in entries_data:
            card = entry.get("card")
            if card is None:
                continue
            key = _normalize_card_name(card.name)
            copies[key] += entry["quantity"]
            names.setdefault(key, card.name)
            if card.id in ban_by_card_id:
                limit = ban_by_card_id[card.id]
            elif key in ban_by_name:
                limit = ban_by_name[key]
            else:
                limit = 1 if (card.ability or "").startswith("Única") else DEFAULT_MAX_COPIES
            limits[key] = min(limits.get(key, limit), limit)

        for key, qty in copies.items():
            limit = limits[key]
            if limit == 0:
                errors.append(f"'{names[key]}' está prohibida en este formato.")
            elif qty > limit:
                errors.append(f"'{names[key]}': {qty} copias (máximo {limit}).")
        return errors

    def _card_matches_deck_format(self, card, deck_format):
        edition = getattr(card, "edition", None)
        if edition is None:
            return True

        if deck_format == "esc":
            return getattr(edition, "slug", "") in ESC_EDITION_SLUGS

        card_format = getattr(getattr(edition, "format", None), "code", None)
        if not card_format:
            return True
        return card_format == deck_format

    @transaction.atomic
    def create(self, validated_data):
        entries_data = validated_data.pop("entries", [])
        deck = Deck.objects.create(**validated_data)
        for entry in entries_data:
            DeckEntry.objects.create(deck=deck, **entry)
        return deck

    @transaction.atomic
    def update(self, instance, validated_data):
        entries_data = validated_data.pop("entries", None)

        # Track changes for changelog
        changes = []
        for field in ("name", "description", "format", "sub_format", "is_public", "shared_with_team", "starting_gold", "cover_card"):
            new_val = validated_data.get(field)
            if new_val is not None and getattr(instance, field) != new_val:
                changes.append(field)

        instance.name = validated_data.get("name", instance.name)
        instance.description = validated_data.get("description", instance.description)
        instance.format = validated_data.get("format", instance.format)
        instance.sub_format = validated_data.get("sub_format", instance.sub_format)
        instance.is_public = validated_data.get("is_public", instance.is_public)
        instance.shared_with_team = validated_data.get("shared_with_team", instance.shared_with_team)
        instance.starting_gold = validated_data.get("starting_gold", instance.starting_gold)
        instance.cover_card = validated_data.get("cover_card", instance.cover_card)
        instance.save()

        if entries_data is not None:
            old_entries = {(e.card_id, e.is_sideboard): e.quantity for e in instance.entries.all()}
            instance.entries.all().delete()
            new_entries = {}
            for entry in entries_data:
                DeckEntry.objects.create(deck=instance, **entry)
                new_entries[(entry["card"].id if hasattr(entry["card"], "id") else entry["card"], entry.get("is_sideboard", False))] = entry["quantity"]
            if old_entries != new_entries:
                changes.append("cartas")

        if changes:
            summary = "Actualizado: " + ", ".join(changes)
            DeckChangeLog.objects.create(deck=instance, summary=summary)

        return instance


class DeckChangeLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeckChangeLog
        fields = ["id", "summary", "created_at"]


class DeckCommentSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = DeckComment
        fields = ["id", "username", "avatar_url", "text", "created_at"]
        read_only_fields = ["created_at"]

    def get_avatar_url(self, obj):
        if hasattr(obj.user, "profile") and obj.user.profile.avatar:
            return obj.user.profile.avatar
        return None


class DeckSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeckSnapshot
        fields = ["id", "label", "created_at"]
