"""
Fix una sola vez: elimina UNL-R01..R06 (que apuntan al arte de OGN) y
renombra UNL-R0Xa -> UNL-R0X para que las runas de Unleashed queden
con su arte propio. Las referencias en mazos / colección / wishlist /
banlist se transfieren a la variante 'a' antes de borrar la base.

Uso:
    python manage.py fix_unl_runes [--dry-run]
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from riftbound.models import (
    RiftboundCard,
    RiftboundDeckEntry,
    RiftboundCollectionEntry,
    RiftboundWishlistEntry,
    RiftboundBanlistEntry,
)


REF_MODELS = (
    RiftboundDeckEntry,
    RiftboundCollectionEntry,
    RiftboundWishlistEntry,
    RiftboundBanlistEntry,
)


class Command(BaseCommand):
    help = "Borra UNL-R01..R06 (arte OGN) y renombra UNL-R0Xa -> UNL-R0X."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **opts):
        dry = opts["dry_run"]
        with transaction.atomic():
            for i in range(1, 7):
                base_n = f"UNL-R0{i}"
                alt_n = f"UNL-R0{i}a"
                base = RiftboundCard.objects.filter(card_number=base_n).first()
                alt = RiftboundCard.objects.filter(card_number=alt_n).first()

                if not alt:
                    self.stdout.write(self.style.WARNING(
                        f"  {alt_n} no existe, salto"
                    ))
                    continue

                if base:
                    for Model in REF_MODELS:
                        refs = Model.objects.filter(card=base)
                        n = refs.count()
                        if n:
                            self.stdout.write(
                                f"   {base_n}: {n} refs {Model.__name__} -> {alt_n}"
                            )
                            if not dry:
                                refs.update(card=alt)
                    if not dry:
                        base.delete()
                    self.stdout.write(self.style.SUCCESS(f"borrada {base_n}"))

                if not dry:
                    alt.card_number = base_n
                    alt.save(update_fields=["card_number"])
                self.stdout.write(self.style.SUCCESS(
                    f"renombrada {alt_n} -> {base_n}"
                ))

            if dry:
                self.stdout.write(self.style.WARNING(
                    "DRY-RUN: ningún cambio aplicado. Vuelve a correr sin --dry-run."
                ))
                # Forzamos rollback de la transacción saliendo con excepción
                # silenciosa no es ideal, pero como --dry-run no hizo .save()
                # ni .delete(), no hay nada que revertir.
