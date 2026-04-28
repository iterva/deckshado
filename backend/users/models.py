from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    first_name = models.CharField(max_length=50, blank=True, default="")
    last_name = models.CharField(max_length=50, blank=True, default="")
    league_code = models.CharField(
        max_length=30, blank=True, default="", verbose_name="Código Liga"
    )
    avatar = models.URLField(max_length=500, blank=True, default="")

    def __str__(self):
        return f"Perfil de {self.user.username}"


class Notification(models.Model):
    """In-app notifications."""
    TYPE_CHOICES = [
        ("team_join", "Solicitud de equipo"),
        ("team_accepted", "Solicitud aceptada"),
        ("team_rejected", "Solicitud rechazada"),
        ("deck_like", "Like en mazo"),
        ("deck_comment", "Comentario en mazo"),
        ("general", "General"),
    ]
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    notif_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default="general")
    message = models.CharField(max_length=300)
    link = models.CharField(max_length=200, blank=True, default="")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.notif_type}] {self.message[:50]}"


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_or_update_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    else:
        Profile.objects.get_or_create(user=instance)
