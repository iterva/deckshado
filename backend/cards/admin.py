from django.contrib import admin
from .models import Format, Season, Edition, Race, CardType, Rarity, Keyword, Card, BanlistEntry


@admin.register(Format)
class FormatAdmin(admin.ModelAdmin):
    list_display = ["code", "name"]
    search_fields = ["code", "name"]


@admin.register(Season)
class SeasonAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "start_date", "end_date", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["code", "name"]


@admin.register(Edition)
class EditionAdmin(admin.ModelAdmin):
    list_display = ["title", "slug", "format", "season", "active", "date_release"]
    list_filter = ["format", "season", "active"]
    search_fields = ["title", "slug"]


@admin.register(Race)
class RaceAdmin(admin.ModelAdmin):
    list_display = ["name", "slug"]
    search_fields = ["name"]


@admin.register(CardType)
class CardTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "slug"]


@admin.register(Rarity)
class RarityAdmin(admin.ModelAdmin):
    list_display = ["name", "slug"]


@admin.register(Keyword)
class KeywordAdmin(admin.ModelAdmin):
    list_display = ["title", "slug", "flag"]


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    list_display = ["name", "edition", "card_type", "rarity", "cost", "damage"]
    list_filter = ["edition", "card_type", "rarity"]
    search_fields = ["name", "slug", "ability"]


@admin.register(BanlistEntry)
class BanlistEntryAdmin(admin.ModelAdmin):
    list_display = ["card_name", "format_code", "sub_format", "status", "max_copies", "card"]
    list_filter = ["format_code", "sub_format", "status"]
    search_fields = ["card_name"]
    raw_id_fields = ["card"]
