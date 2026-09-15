from django.contrib import admin
from django.utils.html import format_html

from .models import (
    RiftboundSet,
    RiftboundCard,
    RiftboundFormat,
    RiftboundBanlistEntry,
    RiftboundDeck,
    RiftboundDeckEntry,
    RiftboundCollectionEntry,
    RiftboundWishlistEntry,
    RiftboundBinderProfile,
    RiftboundStoreOrder,
    RiftboundStoreOrderItem,
    RiftboundStorePermission,
    RiftboundIcon,
)


@admin.register(RiftboundBinderProfile)
class RiftboundBinderProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "display_name", "store_slug", "is_store_public", "city", "country")
    list_filter = ("is_store_public", "country")
    search_fields = ("user__username", "display_name", "store_slug")


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
    list_display = (
        "id",
        "status_badge",
        "store_owner_link",
        "buyer_name",
        "buyer_user_link",
        "items_count",
        "total_formatted",
        "created_at",
    )
    list_display_links = ("id",)
    list_filter = ("status", "created_at")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    search_fields = (
        "id",
        "buyer_name",
        "buyer_whatsapp",
        "store_profile__user__username",
        "buyer_user__username",
    )
    autocomplete_fields = ("store_profile", "buyer_user", "responded_by")
    list_select_related = ("store_profile", "store_profile__user", "buyer_user")
    inlines = [StoreOrderItemInline]
    readonly_fields = ("created_at", "updated_at", "responded_at")

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("items")

    fieldsets = (
        ("Pedido", {"fields": ("store_profile", "status", "total_estimated")}),
        ("Comprador", {"fields": ("buyer_user", "buyer_name", "buyer_whatsapp", "buyer_note")}),
        ("Respuesta del vendedor", {"fields": ("seller_note", "responded_by", "responded_at")}),
        ("Fechas", {"fields": ("created_at", "updated_at")}),
    )

    STATUS_COLORS = {
        "pending": "#f59e0b",
        "accepted": "#10b981",
        "cancelled": "#ef4444",
    }
    STATUS_LABELS = {
        "pending": "Pendiente",
        "accepted": "Aceptado",
        "cancelled": "Cancelado",
    }

    @admin.display(description="Estado", ordering="status")
    def status_badge(self, obj):
        color = self.STATUS_COLORS.get(obj.status, "#6b7280")
        label = self.STATUS_LABELS.get(obj.status, obj.status)
        return format_html(
            '<span style="display:inline-block;padding:2px 10px;border-radius:999px;'
            'font-weight:600;font-size:11px;color:#fff;background:{}">{}</span>',
            color, label,
        )

    @admin.display(description="Tienda", ordering="store_profile__user__username")
    def store_owner_link(self, obj):
        owner = obj.store_profile.user
        return format_html(
            '<a href="/admin/auth/user/{}/change/">{}</a>', owner.id, owner.username,
        )

    @admin.display(description="Comprador (cuenta)", ordering="buyer_user__username")
    def buyer_user_link(self, obj):
        if not obj.buyer_user_id:
            return format_html('<span style="color:#9ca3af">— invitado —</span>')
        return format_html(
            '<a href="/admin/auth/user/{}/change/">{}</a>', obj.buyer_user_id, obj.buyer_user.username,
        )

    @admin.display(description="Items")
    def items_count(self, obj):
        return len(obj.items.all())

    @admin.display(description="Total", ordering="total_estimated")
    def total_formatted(self, obj):
        if obj.total_estimated is None:
            return "—"
        return f"${obj.total_estimated:,.0f}".replace(",", ".")


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
