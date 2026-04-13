from django.conf import settings
from django.db import models


class BinderProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="binder_profile"
    )
    binder_avatar = models.ImageField(upload_to="binder_avatars/", blank=True, null=True)

    def __str__(self):
        return f"Carpeta de {self.user.username}"


class CollectionEntry(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="collection_entries"
    )
    card = models.ForeignKey(
        "cards.Card", on_delete=models.CASCADE, related_name="collection_entries"
    )
    quantity = models.PositiveIntegerField(default=1)
    price = models.PositiveIntegerField(blank=True, null=True, help_text="Precio asignado por el usuario")
    selling_quantity = models.PositiveIntegerField(default=0, help_text="Copias en venta")

    class Meta:
        unique_together = ("user", "card")
        ordering = ["-id"]

    def __str__(self):
        return f"{self.user.username}: {self.quantity}x {self.card.name}"


class WishlistEntry(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wishlist_entries"
    )
    card = models.ForeignKey(
        "cards.Card", on_delete=models.CASCADE, related_name="wishlist_entries"
    )
    desired_quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ("user", "card")
        ordering = ["-id"]

    def __str__(self):
        return f"{self.user.username} quiere {self.desired_quantity}x {self.card.name}"
