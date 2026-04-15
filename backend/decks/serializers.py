from rest_framework import serializers
from .models import Deck, DeckEntry
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
        fields = ["id", "name", "description", "is_public", "shared_with_team", "owner_username", "card_count", "format", "sub_format", "race", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]


class DeckDetailSerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(source="owner.username", read_only=True)
    entries = serializers.SerializerMethodField()
    sideboard_entries = serializers.SerializerMethodField()
    card_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Deck
        fields = ["id", "name", "description", "is_public", "shared_with_team", "owner_username", "card_count", "format", "sub_format", "race", "entries", "sideboard_entries", "created_at", "updated_at"]
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
        fields = ["id", "name", "description", "is_public", "shared_with_team", "format", "sub_format", "race", "entries"]

    def create(self, validated_data):
        entries_data = validated_data.pop("entries", [])
        deck = Deck.objects.create(**validated_data)
        for entry in entries_data:
            DeckEntry.objects.create(deck=deck, **entry)
        return deck

    def update(self, instance, validated_data):
        entries_data = validated_data.pop("entries", None)
        instance.name = validated_data.get("name", instance.name)
        instance.description = validated_data.get("description", instance.description)
        instance.format = validated_data.get("format", instance.format)
        instance.sub_format = validated_data.get("sub_format", instance.sub_format)
        instance.is_public = validated_data.get("is_public", instance.is_public)
        instance.shared_with_team = validated_data.get("shared_with_team", instance.shared_with_team)
        instance.save()

        if entries_data is not None:
            instance.entries.all().delete()
            for entry in entries_data:
                DeckEntry.objects.create(deck=instance, **entry)
        return instance
