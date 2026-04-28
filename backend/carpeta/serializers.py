from rest_framework import serializers
from .models import BinderProfile, CollectionEntry, WishlistEntry
from cards.serializers import CardListSerializer


class BinderProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    binder_avatar_url = serializers.SerializerMethodField()
    share_token = serializers.UUIDField(read_only=True)

    class Meta:
        model = BinderProfile
        fields = ["id", "username", "binder_avatar_url", "share_token"]

    def get_binder_avatar_url(self, obj):
        return obj.binder_avatar or None


class CollectionEntrySerializer(serializers.ModelSerializer):
    card_detail = CardListSerializer(source="card", read_only=True)

    class Meta:
        model = CollectionEntry
        fields = ["id", "card", "quantity", "price", "selling_quantity", "card_detail"]
        extra_kwargs = {"card": {"write_only": True}}


class CollectionEntryWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = CollectionEntry
        fields = ["card", "quantity", "price", "selling_quantity"]


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
