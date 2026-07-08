"""
Seed de reparacion para tipado de cartas AYDV en formato MyL/Imperio.

Corrige a tipo Oro las cartas:
- Libro de Enoc (custom_aydv_019_150_u)
- Libro de Revelaciones (custom_aydv_020_150_u)
- Infernum Vox (custom_aydv_232_p)
- Tablas del Juramento (custom_aydv_090_150_r)
"""

from django.core.management.base import BaseCommand, CommandError

from cards.models import Card, CardType


TARGET_MYLS = [
    "custom_aydv_019_150_u",
    "custom_aydv_020_150_u",
    "custom_aydv_232_p",
    "custom_aydv_090_150_r",
]


class Command(BaseCommand):
    help = "Fixea a tipo Oro cartas AYDV (Libros + Infernum Vox + Tablas)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Muestra cambios sin escribir en BD",
        )

    def handle(self, *args, **options):
        dry_run = bool(options["dry_run"])

        oro_type = CardType.objects.filter(slug="oro").first()
        if oro_type is None:
            raise CommandError("No existe CardType con slug='oro'")

        cards = list(
            Card.objects.filter(myl_id__in=TARGET_MYLS)
            .select_related("card_type", "edition")
            .order_by("myl_id")
        )

        found_ids = {c.myl_id for c in cards}
        missing_ids = [myl_id for myl_id in TARGET_MYLS if myl_id not in found_ids]

        if missing_ids:
            self.stdout.write(
                self.style.WARNING(
                    "No encontradas en BD: " + ", ".join(missing_ids)
                )
            )

        updated = 0
        kept = 0

        for card in cards:
            current_slug = card.card_type.slug if card.card_type else None
            if current_slug == "oro":
                kept += 1
                self.stdout.write(f"KEEP {card.name} ({card.myl_id}) ya es oro")
                continue

            self.stdout.write(
                f"{'[DRY] ' if dry_run else ''}FIX {card.name} ({card.myl_id}) "
                f"{current_slug} -> oro"
            )

            if not dry_run:
                card.card_type = oro_type
                card.save(update_fields=["card_type"])

            updated += 1

        action = "Would update" if dry_run else "Updated"
        self.stdout.write(
            self.style.SUCCESS(
                f"Done. {action}={updated} Kept={kept} Missing={len(missing_ids)}"
            )
        )
