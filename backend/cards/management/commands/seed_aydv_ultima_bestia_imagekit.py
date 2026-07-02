"""
Seed idempotente de la carta AYDV-357-P (La Ultima Bestia) usando ImageKit.

Uso:
  python manage.py seed_aydv_ultima_bestia_imagekit
  python manage.py seed_aydv_ultima_bestia_imagekit --image-url <url>
  python manage.py seed_aydv_ultima_bestia_imagekit --mapping-file ../aydv_ultima_bestia_imagekit_mapping.json
"""

from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from cards.models import Card, CardType, Edition, Race, Rarity


DEFAULT_MAPPING_FILE = (
    Path(__file__).resolve().parents[4] / "aydv_ultima_bestia_imagekit_mapping.json"
)
DEFAULT_IMAGE_URL = (
    "https://ik.imagekit.io/crttm6rou/deckshado/myl_cards/aydv_custom_2026_07/"
    "aydv_357_p_la_ultima_bestia.png"
)


class Command(BaseCommand):
    help = "Upsert de La Ultima Bestia (AYDV-357-P) con ImageKit"

    def add_arguments(self, parser):
        parser.add_argument(
            "--mapping-file",
            default=str(DEFAULT_MAPPING_FILE),
            help="Ruta al mapping JSON con imagekit_url",
        )
        parser.add_argument(
            "--image-url",
            default="",
            help="URL explicita de imagen (tiene prioridad sobre mapping)",
        )

    def _resolve_image_url(self, explicit_url: str, mapping_file: Path) -> str:
        if explicit_url.strip():
            return explicit_url.strip()

        if mapping_file.exists():
            try:
                payload = json.loads(mapping_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise CommandError(f"JSON invalido en mapping file: {mapping_file}: {exc}") from exc

            image_url = (payload.get("imagekit_url") or "").strip()
            if image_url:
                return image_url

        return DEFAULT_IMAGE_URL

    def handle(self, *args, **options):
        mapping_file = Path(options["mapping_file"]).expanduser().resolve()
        image_url = self._resolve_image_url(options.get("image_url") or "", mapping_file)
        if not image_url:
            raise CommandError("No se pudo resolver image_url")

        edition = Edition.objects.filter(slug="aydv").first()
        if not edition:
            raise CommandError("No existe Edition con slug='aydv'")

        card_type = CardType.objects.filter(slug="aliado").first()
        if not card_type:
            raise CommandError("No existe CardType con slug='aliado'")

        race = Race.objects.filter(slug="bestia/dragon/sombra").first()
        if not race:
            raise CommandError("No existe Race con slug='bestia/dragon/sombra'")

        rarity = Rarity.objects.filter(slug="promo").first()

        ability = (
            "Exhumar.\n"
            "Cuando entra en juego, si no lo jugaste desde tu mano, genera un Oro para jugar Aliados.\n"
            "Una vez por turno, puedes pagar un Oro para Anular una carta o jugar un Aliado de tu Cementerio "
            "reduciendo su coste en un Oro hasta un m\u00ednimo de 1."
        )
        flavour = (
            "Surge en tierra hostil y espantada por el miedo de los pueblos. "
            "No reina por justicia, y su trono se alza sobre la debilidad de los d\u00e9biles."
        )

        card, created = Card.objects.update_or_create(
            myl_id="custom_aydv_357_p",
            defaults={
                "edid": "AYDV-357-P",
                "slug": "la-ultima-bestia-aydv-p",
                "name": "La \u00daltima Bestia",
                "edition": edition,
                "rarity": rarity,
                "race": race,
                "card_type": card_type,
                "cost": "2",
                "damage": "4",
                "ability": ability,
                "flavour": flavour,
                "custom_image_url": image_url,
            },
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"{'Created' if created else 'Updated'}: {card.name} ({card.edid}) -> {card.custom_image_url}"
            )
        )
