"""
Seed de la banlist de Riftbound Standard.

Fuente oficial: anuncio del 31 de marzo de 2026.
Cartas baneadas en Standard Constructed:
  - Called Shot (SFD-122)
  - Draven, Vanquisher (SFD-020)
  - Fight or Flight (OGN-168)
  - Scrapheap (OGN-182)
  - The Dreaming Tree (OGN-292) — Battlefield
  - Obelisk of Power (OGN-284) — Battlefield
  - Reaver's Row (OGN-285) — Battlefield

Uso:
    python manage.py seed_riftbound_banlist
"""
from __future__ import annotations

from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction

from riftbound.models import RiftboundBanlistEntry, RiftboundCard, RiftboundFormat


# (card_number, nota opcional)
BANLIST_2026_03_31 = [
    ("SFD-122", "Called Shot"),
    ("SFD-020", "Draven, Vanquisher"),
    ("OGN-168", "Fight or Flight"),
    ("OGN-182", "Scrapheap"),
    ("OGN-292", "The Dreaming Tree (Battlefield)"),
    ("OGN-284", "Obelisk of Power (Battlefield)"),
    ("OGN-285", "Reaver's Row (Battlefield)"),
]


class Command(BaseCommand):
    help = "Crea/actualiza las entradas de banlist de Riftbound Standard (efectivo 2026-03-31)."

    def handle(self, *args, **opts):
        fmt, _ = RiftboundFormat.objects.get_or_create(
            code="standard", defaults={"name": "Standard", "is_active": True},
        )

        # Limpieza: eliminar entradas previas que ya no estén en la lista
        keep_numbers = {n for n, _ in BANLIST_2026_03_31}
        existing = RiftboundBanlistEntry.objects.filter(format=fmt).select_related("card")
        removed = 0
        for be in existing:
            if be.card.card_number not in keep_numbers:
                be.delete()
                removed += 1

        created = updated = missing = 0
        with transaction.atomic():
            for number, note in BANLIST_2026_03_31:
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
                        "effective_from": date(2026, 3, 31),
                    },
                )
                if was_created:
                    created += 1
                else:
                    updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"Banlist Riftbound Standard: {created} creadas, {updated} actualizadas, "
            f"{removed} eliminadas, {missing} no encontradas."
        ))
