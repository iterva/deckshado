import re
import uuid

from django.conf import settings
from django.db import models


def _slugify_username(value: str) -> str:
    value = (value or "").strip().lower()
    value = re.sub(r"[^a-z0-9_-]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value[:60] or str(uuid.uuid4())[:8]


COUNTRY_CHOICES = [
    ("CL", "Chile"), ("AR", "Argentina"), ("PE", "Perú"), ("MX", "México"),
    ("CO", "Colombia"), ("UY", "Uruguay"), ("EC", "Ecuador"), ("BO", "Bolivia"),
    ("VE", "Venezuela"), ("PY", "Paraguay"), ("ES", "España"), ("US", "EE.UU."),
    ("OT", "Otro"),
]


class BinderProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="binder_profile"
    )
    binder_avatar = models.URLField(max_length=500, blank=True, default="")
    share_token = models.UUIDField(default=uuid.uuid4, unique=True)

    # ── Tienda pública ──
    store_slug = models.SlugField(max_length=60, unique=True, blank=True)
    is_store_public = models.BooleanField(default=False)
    display_name = models.CharField(max_length=80, blank=True, default="")
    bio = models.TextField(max_length=500, blank=True, default="")
    city = models.CharField(max_length=80, blank=True, default="")
    country = models.CharField(max_length=2, choices=COUNTRY_CHOICES, default="CL")
    whatsapp = models.CharField(max_length=20, blank=True, default="")
    instagram = models.CharField(max_length=80, blank=True, default="")
    discord = models.CharField(max_length=80, blank=True, default="")
    email_public = models.EmailField(blank=True, default="")
    payment_methods = models.CharField(max_length=200, blank=True, default="")
    shipping_info = models.TextField(max_length=500, blank=True, default="")
    accepts_trades = models.BooleanField(default=False)
    last_active = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.store_slug:
            base = _slugify_username(self.user.username)
            slug = base
            i = 2
            while BinderProfile.objects.filter(store_slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{i}"
                i += 1
            self.store_slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Carpeta de {self.user.username}"


CONDITION_CHOICES = [
    ("NM", "Near Mint"),
    ("LP", "Lightly Played"),
    ("MP", "Moderately Played"),
    ("HP", "Heavily Played"),
    ("DMG", "Damaged"),
]

LANGUAGE_CHOICES = [
    ("ES", "Español"),
    ("EN", "English"),
    ("PT", "Portugués"),
    ("FR", "Francés"),
    ("OT", "Otro"),
]


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
    condition = models.CharField(max_length=4, choices=CONDITION_CHOICES, default="NM")
    language = models.CharField(max_length=4, choices=LANGUAGE_CHOICES, default="ES")
    is_foil = models.BooleanField(default=False)
    notes = models.CharField(max_length=200, blank=True, default="")
    photo_url = models.URLField(max_length=500, blank=True, default="", help_text="Foto real de la carta (Cloudinary)")

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
