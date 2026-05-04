"""Compacta la BD de Riftbound: vacía campos redundantes y ejecuta VACUUM."""
from django.core.management.base import BaseCommand
from django.db import connection
from riftbound.models import RiftboundCard, RiftboundIcon


class Command(BaseCommand):
    help = "Limpia campos redundantes (raw, image_url originales) y compacta la BD."

    def add_arguments(self, parser):
        parser.add_argument(
            "--keep-original-urls",
            action="store_true",
            help="No vaciar image_url originales (por defecto se vacían si hay cdn_image_url).",
        )

    def handle(self, *args, **opts):
        # 1) Vaciar `raw` en todas las cartas
        n_raw = RiftboundCard.objects.exclude(raw={}).update(raw={})
        self.stdout.write(f"raw vaciado en {n_raw} cartas")

        # 2) Vaciar image_url original si ya hay cdn_image_url
        if not opts["keep_original_urls"]:
            n_card_imgs = (
                RiftboundCard.objects
                .exclude(cdn_image_url="")
                .exclude(image_url="", image_url_small="")
                .update(image_url="", image_url_small="")
            )
            self.stdout.write(f"image_url vaciado en {n_card_imgs} cartas")

            n_icon_imgs = (
                RiftboundIcon.objects
                .exclude(cdn_image_url="")
                .exclude(image_url="")
                .update(image_url="")
            )
            self.stdout.write(f"image_url vaciado en {n_icon_imgs} iconos")

        # 3) VACUUM
        with connection.cursor() as c:
            try:
                c.execute("VACUUM")
                self.stdout.write(self.style.SUCCESS("VACUUM completado"))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"VACUUM no soportado: {e}"))
