from django.core.management.base import BaseCommand, CommandError

from cards.models import Card


TARGET_MYL_ID = "custom_aydv_190"
TARGET_EDITION_SLUG = "aydv"
TARGET_EDID = "AYDV-190"
TARGET_IMAGE_URL = "https://blog.myl.cl/wp-content/uploads/2026/05/AYDV_190.png"


class Command(BaseCommand):
    help = "Fixea la imagen de Gehena (AYDV-190) a la version correcta"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Muestra cambios sin escribir en BD",
        )

    def handle(self, *args, **options):
        dry_run = bool(options.get("dry_run"))

        card = Card.objects.filter(myl_id=TARGET_MYL_ID).first()
        if card is None:
            card = Card.objects.filter(
                edition__slug=TARGET_EDITION_SLUG,
                edid=TARGET_EDID,
                name__iexact="gehena",
            ).first()

        if card is None:
            raise CommandError("No se encontro Gehena (custom_aydv_190 / AYDV-190)")

        previous_url = (card.custom_image_url or "").strip()
        if previous_url == TARGET_IMAGE_URL:
            self.stdout.write(self.style.SUCCESS("Gehena ya tiene la URL correcta."))
            return

        self.stdout.write(
            f"{'[DRY] ' if dry_run else ''}FIX {card.name} ({card.myl_id}) URL -> {TARGET_IMAGE_URL}"
        )
        self.stdout.write(f"Antes: {previous_url or '(vacio)'}")

        if not dry_run:
            card.custom_image_url = TARGET_IMAGE_URL
            card.save(update_fields=["custom_image_url"])

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. {'Would update' if dry_run else 'Updated'}=1"
            )
        )
