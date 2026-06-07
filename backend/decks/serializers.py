from rest_framework import serializers
from .models import Deck, DeckEntry, DeckChangeLog, DeckLike, DeckSnapshot, DeckComment
from cards.serializers import CardListSerializer


class DeckEntrySerializer(serializers.ModelSerializer):
    card_detail = CardListSerializer(source="card", read_only=True)

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

    def create(self, validated_data):
        entries_data = validated_data.pop("entries", [])
        deck = Deck.objects.create(**validated_data)
        for entry in entries_data:
            DeckEntry.objects.create(deck=deck, **entry)
        return deck

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
