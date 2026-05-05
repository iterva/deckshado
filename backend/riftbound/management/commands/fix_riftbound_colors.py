"""Aplica correcciones puntuales de colores en cartas Riftbound.

Uso: python manage.py fix_riftbound_colors
"""
from django.core.management.base import BaseCommand
from riftbound.models import RiftboundCard


# (card_number, [colors])
FIXES = [
    ("OGS-017", ["fury", "chaos"]),   # Annie, Dark Child  - rojo morado
    ("SFD-250", ["body", "chaos"]),   # Sivir, Battle Mistress - naranjo morado
    ("UNL-181", ["fury", "mind"]),    # Jhin, Virtuoso - rojo azul
]


class Command(BaseCommand):
    help = "Corrige colores de cartas Riftbound especificas."

    def handle(self, *args, **opts):
        updated = 0
        for cn, cols in FIXES:
            try:
                c = RiftboundCard.objects.get(card_number=cn)
            except RiftboundCard.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"  - {cn} no existe, omitido"))
                continue
            if c.colors == cols:
                self.stdout.write(f"  = {cn} {c.name}: ya esta {cols}")
                continue
            self.stdout.write(self.style.SUCCESS(
                f"  ~ {cn} {c.name}: {c.colors} -> {cols}"
            ))
            c.colors = cols
            c.save(update_fields=["colors"])
            updated += 1
        self.stdout.write(self.style.SUCCESS(f"Listo. {updated} cartas actualizadas."))
