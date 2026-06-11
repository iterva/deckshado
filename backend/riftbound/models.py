"""
Modelos del juego Riftbound (Riot Games / League of Legends TCG).

Mantenidos completamente separados de los modelos `cards` / `decks` (Mitos y Leyendas)
para no acoplar dos juegos con reglas distintas.

Reglas oficiales de construcción de mazo (Riftbound Standard, fuente: Riot Core Rules + Deckbuilding Primer):
- Mazo principal: mínimo 40 cartas (puedes ir a más; recomendado 40).
- Mazo de runas: 12 runas exactas.
- Champion Legend: 1 carta (define los dominios del mazo, va aparte del main).
- Chosen Champion: 1 unidad campeón designada (cuenta dentro del Main Deck;
  la copia que parte en juego cuenta hacia el límite de 3 copias).
- Battlefields: 3 cartas distintas (no se permiten duplicados).
- Sideboard: 8 cartas exactas (sólo en juego de torneo, opcional en casual).
- Máximo 3 copias de cualquier carta no-banlist.
"""
from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


# ───────────────────────── Catálogo ──────────────────────────


class RiftboundSet(models.Model):
    """Expansión / set (ej: OGN, ARC)."""
    code = models.CharField(max_length=10, unique=True, db_index=True)
    name = models.CharField(max_length=120)
    release_date = models.DateField(blank=True, null=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} — {self.name}"


# Colores oficiales: Fury, Calm, Mind, Body, Chaos, Order
COLOR_CHOICES = [
    ("fury", "Fury"),
    ("calm", "Calm"),
    ("mind", "Mind"),
    ("body", "Body"),
    ("chaos", "Chaos"),
    ("order", "Order"),
    ("neutral", "Neutral"),
]


# Tipos principales: Champion, Legend, Unit, Spell, Gear, Battlefield, Rune
TYPE_CHOICES = [
    ("champion", "Champion"),
    ("legend", "Legend"),
    ("unit", "Unit"),
    ("spell", "Spell"),
    ("gear", "Gear"),
    ("battlefield", "Battlefield"),
    ("rune", "Rune"),
    ("other", "Other"),
]


RARITY_CHOICES = [
    ("common", "Common"),
    ("uncommon", "Uncommon"),
    ("rare", "Rare"),
    ("epic", "Epic"),
    ("legendary", "Legendary"),
    ("champion", "Champion"),
    ("promo", "Promo"),
    ("other", "Other"),
]


class RiftboundCard(models.Model):
    """
    Una carta de Riftbound. Identificador estable: número de carta (`SET-NNN[+suffix]`).
    También guardamos el UUID del Piltover Archive para idempotencia del scraper.
    """
    # Identidad
    card_number = models.CharField(
        max_length=20, unique=True, db_index=True,
        help_text="Ej: OGN-001, OGN-007a",
    )
    external_id = models.UUIDField(
        unique=True, default=uuid.uuid4,
        help_text="UUID en Piltover Archive (o generado si no se conoce)",
    )
    name = models.CharField(max_length=200, db_index=True)
    slug = models.SlugField(max_length=220, db_index=True)

    # Clasificación
    set = models.ForeignKey(
        RiftboundSet, on_delete=models.PROTECT, related_name="cards", null=True, blank=True,
    )
    card_type = models.CharField(max_length=20, choices=TYPE_CHOICES, db_index=True, default="unit")
    supertype = models.CharField(max_length=50, blank=True, default="")
    subtypes = models.JSONField(default=list, blank=True, help_text="Lista de subtipos/tags")
    rarity = models.CharField(max_length=20, choices=RARITY_CHOICES, default="common", db_index=True)
    variant = models.CharField(
        max_length=40, blank=True, default="",
        help_text="Promo, Alt-art, Foil, etc.",
    )
    colors = models.JSONField(
        default=list, blank=True,
        help_text="Lista de colores: ['fury','calm',...]",
    )

    # Stats
    energy = models.SmallIntegerField(blank=True, null=True, help_text="Coste de energía")
    power = models.SmallIntegerField(blank=True, null=True)
    might = models.SmallIntegerField(blank=True, null=True)

    # Texto
    description = models.TextField(blank=True, default="", help_text="Texto de la carta (con keywords)")
    flavor = models.TextField(blank=True, default="")

    # Recursos
    image_url = models.URLField(max_length=500, blank=True, default="")
    image_url_small = models.URLField(max_length=500, blank=True, default="")
    cdn_image_url = models.URLField(
        max_length=500, blank=True, default="",
        help_text="URL en Cloudinary u otro CDN propio (opcional)",
    )

    # Origen / metadata
    source_url = models.URLField(max_length=500, blank=True, default="")
    raw = models.JSONField(default=dict, blank=True, help_text="Datos brutos del scraper")
    is_active = models.BooleanField(default=True, help_text="Visible en el catálogo")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["card_number"]
        indexes = [
            models.Index(fields=["card_type"]),
            models.Index(fields=["rarity"]),
            models.Index(fields=["set", "card_number"]),
        ]

    def __str__(self):
        return f"{self.name} [{self.card_number}]"


# ───────────────────────── Banlist ──────────────────────────


class RiftboundFormat(models.Model):
    """Por ahora solo `standard`, pero dejamos extensible."""
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=80)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class RiftboundBanlistEntry(models.Model):
    BANNED = "banned"
    LIMITED_1 = "limited_1"
    LIMITED_2 = "limited_2"
    STATUS_CHOICES = [
        (BANNED, "Prohibida"),
        (LIMITED_1, "Limitada a 1 copia"),
        (LIMITED_2, "Limitada a 2 copias"),
    ]

    format = models.ForeignKey(
        RiftboundFormat, on_delete=models.CASCADE, related_name="banlist_entries",
    )
    card = models.ForeignKey(
        RiftboundCard, on_delete=models.CASCADE, related_name="banlist_entries",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    max_copies = models.PositiveSmallIntegerField(default=0)
    note = models.CharField(max_length=200, blank=True, default="")
    effective_from = models.DateField(blank=True, null=True)

    class Meta:
        unique_together = ("format", "card")
        ordering = ["format", "status", "card__name"]

    def __str__(self):
        return f"{self.card.name} — {self.get_status_display()} ({self.format.code})"


# ───────────────────────── Mazos ──────────────────────────


# Zonas del mazo en Riftbound
ZONE_MAIN = "main"          # mínimo 40 cartas
ZONE_SIDE = "side"          # 8 cartas (sólo torneo)
ZONE_RUNE = "rune"          # 12 runas exactas
ZONE_CHAMPION = "champion"  # 1 Champion Legend
ZONE_BATTLEFIELD = "bg"     # 3 Battlefields distintos

ZONE_CHOICES = [
    (ZONE_MAIN, "Main Deck"),
    (ZONE_SIDE, "Sideboard"),
    (ZONE_RUNE, "Runas"),
    (ZONE_CHAMPION, "Champion Legend"),
    (ZONE_BATTLEFIELD, "Battlefields"),
]


class RiftboundDeck(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="riftbound_decks",
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    format = models.ForeignKey(
        RiftboundFormat, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="decks",
    )
    is_public = models.BooleanField(default=True)
    cover_card = models.ForeignKey(
        RiftboundCard, on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
    )
    # Champion Unit designado: una de las unidades del Main Deck cuyo subtype
    # principal coincide con el nombre del champion legend (p.ej. "Annie, Stubborn"
    # como champion unit del legend "Annie, Dark Child").
    champion_unit = models.ForeignKey(
        RiftboundCard, on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
    )
    primary_colors = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.name} ({self.owner.username})"


class RiftboundDeckEntry(models.Model):
    deck = models.ForeignKey(RiftboundDeck, on_delete=models.CASCADE, related_name="entries")
    card = models.ForeignKey(RiftboundCard, on_delete=models.PROTECT)
    quantity = models.PositiveSmallIntegerField(default=1)
    zone = models.CharField(max_length=12, choices=ZONE_CHOICES, default=ZONE_MAIN, db_index=True)

    class Meta:
        unique_together = ("deck", "card", "zone")

    def __str__(self):
        return f"{self.quantity}x {self.card.name} [{self.zone}]"


# ───────────────────────── Carpeta / Colección ──────────────────────────


class RiftboundCollectionEntry(models.Model):
    CONDITION_CHOICES = [
        ("NM", "Near Mint"),
        ("LP", "Lightly Played"),
        ("MP", "Moderately Played"),
        ("HP", "Heavily Played"),
        ("DMG", "Damaged"),
    ]
    LANGUAGE_CHOICES = [
        ("EN", "English"),
        ("ZH", "中文"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="riftbound_collection",
    )
    card = models.ForeignKey(
        RiftboundCard, on_delete=models.CASCADE, related_name="collection_entries",
    )
    quantity = models.PositiveIntegerField(default=1)
    price = models.PositiveIntegerField(blank=True, null=True, help_text="Precio asignado por el usuario")
    selling_quantity = models.PositiveIntegerField(default=0, help_text="Copias en venta")
    condition = models.CharField(max_length=4, choices=CONDITION_CHOICES, default="NM")
    language = models.CharField(max_length=4, choices=LANGUAGE_CHOICES, default="EN")
    is_foil = models.BooleanField(default=False)
    notes = models.CharField(max_length=200, blank=True, default="")
    photo_url = models.URLField(max_length=500, blank=True, default="", help_text="Foto real de la carta (Cloudinary)")
    photo_url_2 = models.URLField(max_length=500, blank=True, default="", help_text="Segunda foto real (Cloudinary)")

    class Meta:
        unique_together = ("user", "card", "is_foil")
        ordering = ["-id"]

    def __str__(self):
        return f"{self.user.username}: {self.quantity}x {self.card.name}"


class RiftboundWishlistEntry(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="riftbound_wishlist",
    )
    card = models.ForeignKey(
        RiftboundCard, on_delete=models.CASCADE, related_name="wishlist_entries",
    )
    desired_quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ("user", "card")
        ordering = ["-id"]

    def __str__(self):
        return f"{self.user.username} quiere {self.desired_quantity}x {self.card.name}"


# ─────────────────────── Sync estado externo ───────────────────────


class RiftboundSyncState(models.Model):
    """Estado de sincronizacion con proveedores externos (ej. Riftcodex)."""

    key = models.CharField(max_length=50, unique=True, db_index=True)
    provider = models.CharField(max_length=30, default="riftcodex", db_index=True)
    last_cursor = models.DateTimeField(blank=True, null=True)
    last_started_at = models.DateTimeField(blank=True, null=True)
    last_success_at = models.DateTimeField(blank=True, null=True)
    last_stats = models.JSONField(default=dict, blank=True)
    last_error = models.TextField(blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["provider", "key"]

    def __str__(self):
        return f"[{self.provider}] {self.key}"


class RiftboundOpsRun(models.Model):
    """Historial de ejecuciones operativas Riftcodex (sync/audit)."""

    KIND_SYNC = "sync"
    KIND_AUDIT = "audit"
    KIND_CHOICES = [
        (KIND_SYNC, "Sync"),
        (KIND_AUDIT, "Audit"),
    ]

    STATUS_RUNNING = "running"
    STATUS_SUCCESS = "success"
    STATUS_ERROR = "error"
    STATUS_CHOICES = [
        (STATUS_RUNNING, "Running"),
        (STATUS_SUCCESS, "Success"),
        (STATUS_ERROR, "Error"),
    ]

    provider = models.CharField(max_length=30, default="riftcodex", db_index=True)
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, db_index=True)
    command = models.CharField(max_length=80)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_RUNNING, db_index=True)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="riftbound_ops_runs",
    )
    args = models.JSONField(default=dict, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(blank=True, null=True)
    duration_ms = models.PositiveIntegerField(blank=True, null=True)
    output = models.TextField(blank=True, default="")
    error = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"[{self.provider}] {self.kind} {self.status} #{self.id}"


# ─────────────────────── Binder Profile (Tienda) ───────────────────────


import re as _re
import uuid as _uuid


def _rb_slugify(value: str) -> str:
    value = (value or "").strip().lower()
    value = _re.sub(r"[^a-z0-9_-]+", "-", value)
    value = _re.sub(r"-+", "-", value).strip("-")
    return value[:60] or str(_uuid.uuid4())[:8]


RB_COUNTRY_CHOICES = [
    ("CL", "Chile"), ("AR", "Argentina"), ("PE", "Perú"), ("MX", "México"),
    ("CO", "Colombia"), ("UY", "Uruguay"), ("EC", "Ecuador"), ("BO", "Bolivia"),
    ("VE", "Venezuela"), ("PY", "Paraguay"), ("ES", "España"), ("US", "EE.UU."),
    ("OT", "Otro"),
]


class RiftboundBinderProfile(models.Model):
    """Perfil de carpeta / tienda para Riftbound (espejo de carpeta.BinderProfile)."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="riftbound_binder_profile",
    )
    binder_avatar = models.URLField(max_length=500, blank=True, default="")
    share_token = models.UUIDField(default=_uuid.uuid4, unique=True)

    # Tienda pública
    store_slug = models.SlugField(max_length=60, unique=True, blank=True)
    is_store_public = models.BooleanField(default=False)
    display_name = models.CharField(max_length=80, blank=True, default="")
    bio = models.TextField(max_length=500, blank=True, default="")
    city = models.CharField(max_length=80, blank=True, default="")
    country = models.CharField(max_length=2, choices=RB_COUNTRY_CHOICES, default="CL")
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
            base = _rb_slugify(self.user.username)
            slug = base
            i = 2
            while RiftboundBinderProfile.objects.filter(store_slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{i}"
                i += 1
            self.store_slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Carpeta Riftbound de {self.user.username}"


# ───────────────────────── Iconografía ──────────────────────────


class RiftboundIcon(models.Model):
    """
    Recursos gráficos auxiliares: iconos de coste, colores, keywords, supertipos, etc.
    Nos permite mapear nombres de keyword (ej: 'GANKING') a una URL de Cloudinary
    sin acoplar el frontend a piltoverarchive.com.
    """
    KIND_COLOR = "color"
    KIND_KEYWORD = "keyword"
    KIND_STAT = "stat"
    KIND_TYPE = "type"
    KIND_OTHER = "other"
    KIND_CHOICES = [
        (KIND_COLOR, "Color"),
        (KIND_KEYWORD, "Keyword"),
        (KIND_STAT, "Stat"),
        (KIND_TYPE, "Type"),
        (KIND_OTHER, "Other"),
    ]

    kind = models.CharField(max_length=20, choices=KIND_CHOICES, db_index=True)
    code = models.CharField(max_length=80, db_index=True, help_text="Ej: GANKING, fury, might")
    label = models.CharField(max_length=120, blank=True, default="")
    image_url = models.URLField(max_length=500)
    cdn_image_url = models.URLField(max_length=500, blank=True, default="")

    class Meta:
        unique_together = ("kind", "code")
        ordering = ["kind", "code"]

    def __str__(self):
        return f"[{self.kind}] {self.code}"
