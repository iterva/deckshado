from django.core.management.base import BaseCommand, CommandError

from cards.models import Card


TARGETS = [
    {
        "myl_id": "custom_aydv_183",
        "edition_slug": "aydv",
        "edid": "AYDV-183",
        "name": "Dulce Canasta",
        "url": "https://blog.myl.cl/wp-content/uploads/2026/05/AYDV_183-1.png",
    },
    {
        "myl_id": "custom_aydv_186",
        "edition_slug": "aydv",
        "edid": "AYDV-186",
        "name": "Don de Belial",
        "url": "https://blog.myl.cl/wp-content/uploads/2026/05/AYDV_186-1.png",
    },
]


class Command(BaseCommand):
    help = "Fixea artes de oros AYDV con imagen incorrecta (Dulce Canasta, Don de Belial)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Muestra cambios sin escribir en BD",
        )

    def _find_card(self, target):
        card = Card.objects.filter(myl_id=target["myl_id"]).first()
        if card is not None:
            return card

        return Card.objects.filter(
            edition__slug=target["edition_slug"],
            edid=target["edid"],
            name__iexact=target["name"],
        ).first()

    def handle(self, *args, **options):
        dry_run = bool(options.get("dry_run"))
        updated = 0
        kept = 0
        missing = 0

        for target in TARGETS:
            card = self._find_card(target)
            if card is None:
                missing += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"MISSING {target['name']} ({target['myl_id']})"
                    )
                )
                continue

            current_url = (card.custom_image_url or "").strip()
            new_url = target["url"].strip()

            if current_url == new_url:
                kept += 1
                self.stdout.write(
                    f"KEEP {card.name} ({card.myl_id}) ya tiene imagen correcta"
                )
                continue

            self.stdout.write(
                f"{'[DRY] ' if dry_run else ''}FIX {card.name} ({card.myl_id}) URL -> {new_url}"
            )
            self.stdout.write(f"Antes: {current_url or '(vacio)'}")

            if not dry_run:
                card.custom_image_url = new_url
                card.save(update_fields=["custom_image_url"])

            updated += 1

        if missing and updated == 0 and kept == 0:
            raise CommandError("No se encontraron cartas objetivo para corregir")

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. {'Would update' if dry_run else 'Updated'}={updated} Kept={kept} Missing={missing}"
            )
        )
