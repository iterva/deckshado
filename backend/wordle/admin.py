from django.contrib import admin

from .models import DailyWord, WordleAttempt


@admin.register(DailyWord)
class DailyWordAdmin(admin.ModelAdmin):
    list_display = ("date", "display_word", "length", "card")
    search_fields = ("display_word", "word", "card__name")
    list_filter = ("date",)
    autocomplete_fields = ("card",)


@admin.register(WordleAttempt)
class WordleAttemptAdmin(admin.ModelAdmin):
    list_display = ("user", "daily", "attempts_used", "won", "finished", "score")
    list_filter = ("won", "finished")
    search_fields = ("user__username",)
