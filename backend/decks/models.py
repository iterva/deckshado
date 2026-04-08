from django.conf import settings
from django.db import models


class Deck(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="decks")
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    race = models.CharField(max_length=50, blank=True, default="")
    is_public = models.BooleanField(default=True)
    shared_with_team = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.name} ({self.owner.username})"


class DeckEntry(models.Model):
    deck = models.ForeignKey(Deck, on_delete=models.CASCADE, related_name="entries")
    card = models.ForeignKey("cards.Card", on_delete=models.CASCADE)
    quantity = models.PositiveSmallIntegerField(default=1)
    is_sideboard = models.BooleanField(default=False)

    class Meta:
        unique_together = ("deck", "card", "is_sideboard")

    def __str__(self):
        return f"{self.quantity}x {self.card.name}"
