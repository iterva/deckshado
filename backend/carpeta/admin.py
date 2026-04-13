from django.contrib import admin
from .models import BinderProfile, CollectionEntry, WishlistEntry


@admin.register(BinderProfile)
class BinderProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "binder_avatar")


@admin.register(CollectionEntry)
class CollectionEntryAdmin(admin.ModelAdmin):
    list_display = ("user", "card", "quantity", "price", "selling_quantity")
    list_filter = ("user",)


@admin.register(WishlistEntry)
class WishlistEntryAdmin(admin.ModelAdmin):
    list_display = ("user", "card", "desired_quantity")
    list_filter = ("user",)
