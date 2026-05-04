from django.conf import settings
from django.db import models


class DailyWord(models.Model):
    """Palabra del día (carta) de la Wordle diaria."""

    date = models.DateField(unique=True, db_index=True)
    card = models.ForeignKey(
        "cards.Card", on_delete=models.PROTECT, related_name="wordle_days"
    )
    word = models.CharField(
        max_length=64,
        help_text="Nombre normalizado (sin tildes, minúsculas, sólo letras)",
    )
    display_word = models.CharField(max_length=255, help_text="Nombre original de la carta")
    length = models.PositiveSmallIntegerField()
    hint = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-date"]

    def __str__(self):  # pragma: no cover
        return f"{self.date} - {self.display_word}"


class WordleAttempt(models.Model):
    """Intento(s) de un usuario para la palabra de un día."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wordle_attempts"
    )
    daily = models.ForeignKey(
        DailyWord, on_delete=models.CASCADE, related_name="user_attempts"
    )
    guesses = models.JSONField(default=list, blank=True)
    attempts_used = models.PositiveSmallIntegerField(default=0)
    won = models.BooleanField(default=False)
    finished = models.BooleanField(default=False)
    score = models.PositiveIntegerField(default=0)
    hint_revealed = models.BooleanField(default=False)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [("user", "daily")]
        indexes = [
            models.Index(fields=["user", "daily"]),
            models.Index(fields=["daily"]),
        ]

    def __str__(self):  # pragma: no cover
        return f"{self.user_id} @ {self.daily_id} ({self.attempts_used})"
