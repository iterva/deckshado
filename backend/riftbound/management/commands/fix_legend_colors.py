"""
Repara colores faltantes uniendo los colores de todas las variantes
que comparten el mismo `name`. Útil cuando el scraper detectó 1 color
en la versión base pero 2 en las Overnumbered/Signed (o viceversa).

Por defecto procesa SOLO legends (es donde se ve el bug); con
``--all-types`` aplica a todas las cartas.

Uso:
    python manage.py fix_legend_colors            # solo legends
    python manage.py fix_legend_colors --all-types
    python manage.py fix_legend_colors --dry-run
"""
from __future__ import annotations

from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction

from riftbound.models import RiftboundCard


class Command(BaseCommand):
    help = "Unifica los colores entre variantes que comparten el mismo nombre."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--all-types", action="store_true",
                            help="Aplica a todas las cartas, no solo legends.")

    def handle(self, *args, **opts):
        dry = opts["dry_run"]
        qs = RiftboundCard.objects.all()
        if not opts["all_types"]:
            qs = qs.filter(card_type="legend")

        groups: dict[str, list[RiftboundCard]] = defaultdict(list)
        for c in qs:
            groups[c.name].append(c)

        changed = 0
        with transaction.atomic():
            for name, cards in groups.items():
                # Unión de colores de todas las variantes
                union = sorted({col for c in cards for col in (c.colors or [])})
                if not union:
                    continue
                for c in cards:
                    current = sorted(c.colors or [])
                    if current != union:
                        self.stdout.write(
                            f"  {c.card_number:14s} {name[:35]:35s} "
                            f"{current} -> {union}"
                        )
                        if not dry:
                            c.colors = union
                            c.save(update_fields=["colors"])
                        changed += 1

            self.stdout.write(self.style.SUCCESS(
                f"\nCartas actualizadas: {changed}"
            ))
            if dry:
                self.stdout.write(self.style.WARNING("DRY-RUN: nada se guardó."))
