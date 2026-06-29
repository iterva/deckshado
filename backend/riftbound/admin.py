from django.contrib import admin

from .models import (
    RiftboundSet,
    RiftboundCard,
    RiftboundFormat,
    RiftboundBanlistEntry,
    RiftboundDeck,
    RiftboundDeckEntry,
    RiftboundCollectionEntry,
    RiftboundWishlistEntry,
    RiftboundStoreOrder,
    RiftboundStoreOrderItem,
    RiftboundStorePermission,
    RiftboundIcon,
)


@admin.register(RiftboundSet)
class RiftboundSetAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "release_date")
    search_fields = ("code", "name")


@admin.register(RiftboundCard)
class RiftboundCardAdmin(admin.ModelAdmin):
    list_display = ("card_number", "name", "card_type", "rarity", "energy", "power", "might", "set")
    list_filter = ("card_type", "rarity", "set", "is_active")
    search_fields = ("card_number", "name", "description")
    list_select_related = ("set",)
    readonly_fields = ("external_id", "created_at", "updated_at")


@admin.register(RiftboundFormat)
class RiftboundFormatAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_active")


@admin.register(RiftboundBanlistEntry)
class RiftboundBanlistEntryAdmin(admin.ModelAdmin):
    list_display = ("card", "format", "status", "max_copies", "effective_from")
    list_filter = ("format", "status")
    search_fields = ("card__name", "card__card_number")
    autocomplete_fields = ("card",)


class DeckEntryInline(admin.TabularInline):
    model = RiftboundDeckEntry
    extra = 0
    autocomplete_fields = ("card",)


@admin.register(RiftboundDeck)
class RiftboundDeckAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "format", "is_public", "updated_at")
    list_filter = ("format", "is_public")
    search_fields = ("name", "owner__username")
    inlines = [DeckEntryInline]


@admin.register(RiftboundCollectionEntry)
class RiftboundCollectionEntryAdmin(admin.ModelAdmin):
    list_display = ("user", "card", "quantity", "is_foil")
    search_fields = ("user__username", "card__name")
    autocomplete_fields = ("card",)


@admin.register(RiftboundWishlistEntry)
class RiftboundWishlistEntryAdmin(admin.ModelAdmin):
    list_display = ("user", "card", "desired_quantity")
    search_fields = ("user__username", "card__name")
    autocomplete_fields = ("card",)


class StoreOrderItemInline(admin.TabularInline):
    model = RiftboundStoreOrderItem
    extra = 0
    autocomplete_fields = ("card", "collection_entry")
    readonly_fields = ("card_name", "card_number", "unit_price", "line_total", "language", "is_foil")


@admin.register(RiftboundStoreOrder)
class RiftboundStoreOrderAdmin(admin.ModelAdmin):
    list_display = ("id", "store_profile", "status", "buyer_name", "buyer_user", "total_estimated", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("buyer_name", "buyer_whatsapp", "store_profile__user__username")
    inlines = [StoreOrderItemInline]
    readonly_fields = ("created_at", "updated_at", "responded_at")


@admin.register(RiftboundIcon)
class RiftboundIconAdmin(admin.ModelAdmin):
    list_display = ("kind", "code", "label")
    list_filter = ("kind",)
    search_fields = ("code", "label")


@admin.register(RiftboundStorePermission)
class RiftboundStorePermissionAdmin(admin.ModelAdmin):
    list_display = (
        "store_profile",
        "user",
        "can_view_collection",
        "can_edit_collection",
        "can_edit_market",
        "can_view_orders",
        "can_manage_permissions",
        "updated_at",
    )
    list_filter = (
        "can_view_collection",
        "can_edit_collection",
        "can_edit_market",
        "can_view_orders",
        "can_manage_permissions",
    )
    search_fields = ("store_profile__user__username", "user__username", "user__email")
