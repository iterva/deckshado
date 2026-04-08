from django.db import models


class Format(models.Model):
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Edition(models.Model):
    myl_id = models.CharField(max_length=20, unique=True)
    slug = models.CharField(max_length=100, unique=True)
    title = models.CharField(max_length=255)
    image = models.URLField(blank=True, null=True)
    date_release = models.DateField(blank=True, null=True)
    date_empire_valid = models.DateField(blank=True, null=True)
    format = models.ForeignKey(Format, on_delete=models.SET_NULL, null=True, blank=True, related_name="editions")
    active = models.BooleanField(default=True, help_text="Si la edición está en la rotación actual de su formato")

    class Meta:
        ordering = ["-date_release"]

    def __str__(self):
        return self.title


class Race(models.Model):
    myl_id = models.CharField(max_length=10, unique=True)
    slug = models.CharField(max_length=100)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class CardType(models.Model):
    myl_id = models.CharField(max_length=10, unique=True)
    slug = models.CharField(max_length=50)
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name


class Rarity(models.Model):
    myl_id = models.CharField(max_length=10, unique=True)
    slug = models.CharField(max_length=50)
    name = models.CharField(max_length=50)

    class Meta:
        verbose_name_plural = "rarities"

    def __str__(self):
        return self.name


class Keyword(models.Model):
    myl_id = models.CharField(max_length=10, unique=True)
    flag = models.IntegerField()
    slug = models.CharField(max_length=50)
    title = models.CharField(max_length=100)
    alt_title = models.CharField(max_length=200, blank=True, default="")
    definition = models.TextField(blank=True, default="")

    def __str__(self):
        return self.title


class Card(models.Model):
    myl_id = models.CharField(max_length=20, unique=True)
    edid = models.CharField(max_length=10, help_text="Número dentro de la edición")
    slug = models.CharField(max_length=255)
    name = models.CharField(max_length=255, db_index=True)
    edition = models.ForeignKey(Edition, on_delete=models.CASCADE, related_name="cards")
    rarity = models.ForeignKey(Rarity, on_delete=models.SET_NULL, null=True, blank=True)
    race = models.ForeignKey(Race, on_delete=models.SET_NULL, null=True, blank=True)
    card_type = models.ForeignKey(CardType, on_delete=models.SET_NULL, null=True, blank=True)
    cost = models.CharField(max_length=10, blank=True, null=True)
    damage = models.CharField(max_length=10, blank=True, null=True)
    ability = models.TextField(blank=True, null=True)
    flavour = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["edition", "edid"]
        indexes = [
            models.Index(fields=["edition", "edid"]),
            models.Index(fields=["card_type"]),
            models.Index(fields=["race"]),
            models.Index(fields=["rarity"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.edition.slug} #{self.edid})"


class BanlistEntry(models.Model):
    BANNED = "banned"
    LIMITED_1 = "limited_1"
    LIMITED_2 = "limited_2"
    STATUS_CHOICES = [
        (BANNED, "Prohibida"),
        (LIMITED_1, "Limitada a 1 copia"),
        (LIMITED_2, "Limitada a 2 copias"),
    ]

    card_name = models.CharField(max_length=255, help_text="Nombre tal como aparece en la banlist")
    card = models.ForeignKey(
        Card, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="banlist_entries",
        help_text="Carta enlazada (puede ser null si no se encuentra match)",
    )
    format_code = models.CharField(max_length=10, db_index=True, help_text="Código del formato: imp, fx")
    sub_format = models.CharField(max_length=30, db_index=True, help_text="Sub-formato: racial, vcr, triadas")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    max_copies = models.PositiveSmallIntegerField(
        default=0,
        help_text="0 = prohibida, 1 = limitada a 1, 2 = limitada a 2",
    )
    last_synced = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("card_name", "format_code", "sub_format")
        ordering = ["format_code", "sub_format", "status", "card_name"]
        verbose_name = "Banlist Entry"
        verbose_name_plural = "Banlist Entries"

    def __str__(self):
        return f"{self.card_name} ({self.get_status_display()}) - {self.format_code}/{self.sub_format}"
