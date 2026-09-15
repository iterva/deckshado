"""
Parche de banlist de Riftbound Standard — anuncio del 14 de septiembre de 2026.

Cartas baneadas (se agregan a la banlist existente, no se toca nada más):
  - Stacked Deck (OGN-183 y OPP-183, ambas reimpresiones)
  - Ekko, Recurrent (OGN-110)

A diferencia de `seed_riftbound_banlist` (que resincroniza toda la lista y borra lo
que no está en su tabla), este comando es aditivo: solo crea/actualiza las entradas
de abajo y no borra ninguna entrada existente.

Uso:
    python manage.py seed_riftbound_banlist_2026_09
"""
from __future__ import annotations

from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction

from riftbound.models import RiftboundBanlistEntry, RiftboundCard, RiftboundFormat

EFFECTIVE_FROM = date(2026, 9, 14)

# (card_number, nota)
BANLIST_PATCH_2026_09_14 = [
    ("OGN-183", "Stacked Deck"),
    ("OPP-183", "Stacked Deck"),
    ("OGN-110", "Ekko, Recurrent (Mind)"),
]


class Command(BaseCommand):
    help = "Agrega/actualiza a la banlist de Riftbound Standard: Stacked Deck y Ekko, Recurrent (efectivo 2026-09-14)."

    def handle(self, *args, **opts):
        fmt, _ = RiftboundFormat.objects.get_or_create(
            code="standard", defaults={"name": "Standard", "is_active": True},
        )

        created = updated = missing = 0
        with transaction.atomic():
            for number, note in BANLIST_PATCH_2026_09_14:
                card = RiftboundCard.objects.filter(card_number=number).first()
                if not card:
                    self.stderr.write(self.style.WARNING(f"[skip] No existe carta {number}"))
                    missing += 1
                    continue
                obj, was_created = RiftboundBanlistEntry.objects.update_or_create(
                    format=fmt, card=card,
                    defaults={
                        "status": RiftboundBanlistEntry.BANNED,
                        "max_copies": 0,
                        "note": note,
                        "effective_from": EFFECTIVE_FROM,
                    },
                )
                if was_created:
                    created += 1
                else:
                    updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"Banlist Riftbound Standard (patch 2026-09-14): {created} creadas, "
            f"{updated} actualizadas, {missing} no encontradas."
        ))
