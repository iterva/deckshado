"""Crea formatos base de Riftbound (por ahora solo Standard)."""
from django.core.management.base import BaseCommand

from riftbound.models import RiftboundFormat


class Command(BaseCommand):
    help = "Crea/asegura los formatos base de Riftbound"

    def handle(self, *args, **opts):
        fmt, created = RiftboundFormat.objects.get_or_create(
            code="standard", defaults={"name": "Standard", "is_active": True},
        )
        msg = "creado" if created else "ya existía"
        self.stdout.write(self.style.SUCCESS(f"Formato 'standard' {msg}"))
