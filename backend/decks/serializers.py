from rest_framework import serializers
from .models import Deck, DeckEntry, DeckChangeLog
from cards.serializers import CardListSerializer


class DeckEntrySerializer(serializers.ModelSerializer):
    card_detail = CardListSerializer(source="card", read_only=True)

    class Meta:
        model = DeckEntry
        fields = ["id", "card", "quantity", "is_sideboard", "card_detail"]


class DeckListSerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(source="owner.username", read_only=True)
    card_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Deck
        fields = ["id", "name", "description", "is_public", "shared_with_team", "owner_username", "card_count", "format", "sub_format", "race", "starting_gold", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]


class DeckDetailSerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(source="owner.username", read_only=True)
    entries = serializers.SerializerMethodField()
    sideboard_entries = serializers.SerializerMethodField()
    card_count = serializers.IntegerField(read_only=True)
    starting_gold_detail = CardListSerializer(source="starting_gold", read_only=True)

    class Meta:
        model = Deck
        fields = ["id", "name", "description", "is_public", "shared_with_team", "owner_username", "card_count", "format", "sub_format", "race", "starting_gold", "starting_gold_detail", "entries", "sideboard_entries", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]

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
        fields = ["id", "name", "description", "is_public", "shared_with_team", "format", "sub_format", "race", "starting_gold", "entries"]

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
        for field in ("name", "description", "format", "sub_format", "is_public", "shared_with_team", "starting_gold"):
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
