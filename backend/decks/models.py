from django.conf import settings
from django.db import models


class Deck(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="decks")
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    format = models.CharField(max_length=20, default="imp")
    sub_format = models.CharField(max_length=20, blank=True, default="racial")
    race = models.CharField(max_length=50, blank=True, default="")
    is_public = models.BooleanField(default=True)
    shared_with_team = models.BooleanField(default=False)
    starting_gold = models.ForeignKey(
        "cards.Card", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.name} ({self.owner.username})"


class DeckEntry(models.Model):
    deck = models.ForeignKey(Deck, on_delete=models.CASCADE, related_name="entries")
    card = models.ForeignKey("cards.Card", on_delete=models.PROTECT)
    quantity = models.PositiveSmallIntegerField(default=1)
    is_sideboard = models.BooleanField(default=False)

    class Meta:
        unique_together = ("deck", "card", "is_sideboard")

    def __str__(self):
        return f"{self.quantity}x {self.card.name}"


class DeckChangeLog(models.Model):
    """Lightweight changelog: one row per save/update."""
    deck = models.ForeignKey(Deck, on_delete=models.CASCADE, related_name="changelog")
    summary = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.created_at:%Y-%m-%d %H:%M}] {self.summary[:60]}"
