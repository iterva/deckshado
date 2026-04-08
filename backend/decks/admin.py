from django.contrib import admin
from .models import Deck, DeckEntry


class DeckEntryInline(admin.TabularInline):
    model = DeckEntry
    extra = 0
    raw_id_fields = ["card"]


@admin.register(Deck)
class DeckAdmin(admin.ModelAdmin):
    list_display = ["name", "owner", "is_public", "get_card_count", "updated_at"]
    list_filter = ["is_public"]
    search_fields = ["name", "owner__username"]
    inlines = [DeckEntryInline]

    @admin.display(description="Cartas")
    def get_card_count(self, obj):
        return sum(e.quantity for e in obj.entries.all())
