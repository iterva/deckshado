from django.contrib import admin
from .models import BinderProfile, CollectionEntry, WishlistEntry, StoreOrder, StoreOrderItem


@admin.register(BinderProfile)
class BinderProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "binder_avatar")


@admin.register(CollectionEntry)
class CollectionEntryAdmin(admin.ModelAdmin):
    list_display = ("user", "card", "quantity", "price", "selling_quantity")
    list_filter = ("user",)
    search_fields = ("user__username", "card__name")


@admin.register(WishlistEntry)
class WishlistEntryAdmin(admin.ModelAdmin):
    list_display = ("user", "card", "desired_quantity")
    list_filter = ("user",)


class StoreOrderItemInline(admin.TabularInline):
    model = StoreOrderItem
    extra = 0
    autocomplete_fields = ("card", "collection_entry")
    readonly_fields = ("card_name", "card_edid", "unit_price", "line_total", "language", "is_foil")


@admin.register(StoreOrder)
class StoreOrderAdmin(admin.ModelAdmin):
    list_display = ("id", "store_profile", "status", "buyer_name", "buyer_user", "total_estimated", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("buyer_name", "buyer_whatsapp", "store_profile__user__username")
    inlines = [StoreOrderItemInline]
    readonly_fields = ("created_at", "updated_at", "responded_at")
