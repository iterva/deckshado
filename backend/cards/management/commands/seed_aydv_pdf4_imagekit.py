"""
Seed de 4 cartas JO (extraidas desde PDF local) para
Angeles y Demonios: Vigilantes en formato Imperio.

Uso:
  python manage.py seed_aydv_pdf4_imagekit
  python manage.py seed_aydv_pdf4_imagekit --skip-url-check
  python manage.py seed_aydv_pdf4_imagekit --mapping-file /ruta/jo_nueva_era_2026_06_pdf_4cards_mapping.json
"""

from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from cards.models import Card, CardType, Edition, Format, Race, Rarity

from ._mapping_health import validate_mapping_urls


DEFAULT_MAPPING_FILE = (
    Path(__file__).resolve().parents[4] / "jo_nueva_era_2026_06_pdf_4cards_mapping.json"
)


CARD_SPECS = [
    {
        "myl_id": "custom_aydv_243_p",
        "edid": "AYDV-243-P",
        "slug": "la-serpiente-del-eden-aydv-p",
        "name": "La Serpiente del Eden",
        "type_slug": "aliado",
        "race_slug": "dragon",
        "rarity_slug": "promo",
        "cost": "1",
        "damage": "3",
        "ability": (
            "Furia. Cuando entra en juego, busca una carta que no sea Talisman "
            "en tu Castillo y ponla en tu mano. En tu Fase Final, Baraja y/o "
            "Destierra hasta dos cartas de los Cementerios y Roba una carta. "
            "Cuando sea Destruido, tu oponente Bota tres cartas."
        ),
    },
    {
        "myl_id": "custom_aydv_234_p",
        "edid": "AYDV-234-P",
        "slug": "agabar-la-esperanza-aydv-p",
        "name": "Agabar la Esperanza",
        "type_slug": "talisman",
        "race_slug": None,
        "rarity_slug": "promo",
        "cost": "1",
        "damage": None,
        "ability": (
            "Exhumar. Si es Anulado, genera un Oro y Roba una carta. Convierte "
            "un Oro o carta de coste 3 o menos en una carta del mismo tipo, sin "
            "habilidad. Muestra cartas del tope de tu Castillo hasta mostrar hasta "
            "dos cartas de ese tipo, ponlas en tu mano y Baraja el resto."
        ),
    },
    {
        "myl_id": "custom_aydv_239_p",
        "edid": "AYDV-239-P",
        "slug": "guerrillero-rodriguez-aydv-p",
        "name": "Guerrillero Rodriguez",
        "type_slug": "aliado",
        "race_slug": "guerrero",
        "rarity_slug": "promo",
        "cost": "1",
        "damage": "2",
        "ability": (
            "Indestructible. Puedes jugarlo al comienzo de la Vigilia. Cuando "
            "entra en juego, Roba una carta. Las cartas solo pueden ser puestas "
            "en juego desde la mano de su dueno. No puede ser afectado por Oros "
            "oponentes."
        ),
    },
    {
        "myl_id": "custom_aydv_232_p",
        "edid": "AYDV-232-P",
        "slug": "aniquilar-titanes-aydv-p",
        "name": "Aniquilar Titanes",
        "type_slug": "talisman",
        "race_slug": None,
        "rarity_slug": "promo",
        "cost": "1",
        "damage": None,
        "ability": (
            "No puede ser Anulado. Destruye una carta oponente de coste 2 o menos, "
            "o Baraja una carta sin habilidad que no sea Oro. Cuando se resuelva, "
            "conviertelo en un Oro sin habilidad y ponlo en tu Oro Pagado."
        ),
    },
]


class Command(BaseCommand):
    help = "Seed de 4 cartas AYDV desde PDF/ImageKit para Imperio"

    def add_arguments(self, parser):
        parser.add_argument(
            "--mapping-file",
            default=str(DEFAULT_MAPPING_FILE),
            help="Ruta al mapping JSON de las 4 cartas en ImageKit",
        )
        parser.add_argument(
            "--skip-url-check",
            action="store_true",
            help="Omite validacion HTTP de URLs antes del seed",
        )
        parser.add_argument(
            "--url-check-timeout",
            type=int,
            default=10,
            help="Timeout en segundos para health check de URLs",
        )

    def _load_image_map(self, mapping_file: Path) -> dict[str, str]:
        if not mapping_file.exists():
            raise CommandError(f"No existe mapping file: {mapping_file}")

        try:
            payload = json.loads(mapping_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise CommandError(f"JSON invalido en mapping file: {exc}") from exc

        records = payload.get("records")
        if not isinstance(records, list):
            raise CommandError("El mapping no contiene una lista valida en 'records'.")

        image_map: dict[str, str] = {}
        for rec in records:
            if not isinstance(rec, dict):
                continue
            edid = (rec.get("edid") or "").strip()
            url = (rec.get("imagekit_url") or "").strip()
            if not edid or not url:
                continue
            image_map[edid] = url

        return image_map

    def handle(self, *args, **options):
        mapping_file = Path(options["mapping_file"]).expanduser().resolve()
        image_map = self._load_image_map(mapping_file)

        required_edids = {c["edid"] for c in CARD_SPECS}
        missing = sorted(required_edids - set(image_map.keys()))
        if missing:
            raise CommandError(
                "Faltan imagenes en mapping para EDID requeridos: " + ", ".join(missing)
            )

        validate_mapping_urls(
            {edid: image_map[edid] for edid in sorted(required_edids)},
            self,
            "AYDV PDF 4 cartas ImageKit",
            skip_check=options["skip_url_check"],
            timeout=max(1, int(options["url_check_timeout"])),
        )

        imp_format, _ = Format.objects.get_or_create(
            code="imp",
            defaults={"name": "Imperio"},
        )

        edition, edition_created = Edition.objects.update_or_create(
            myl_id="custom_aydv",
            defaults={
                "slug": "aydv",
                "title": "Angeles y Demonios: Vigilantes",
                "image": image_map.get("AYDV-232-P", ""),
                "date_release": "2025-07-03",
                "format": imp_format,
                "active": True,
            },
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"{'Created' if edition_created else 'Updated'} edition: {edition.title}"
            )
        )

        created_count = 0
        updated_count = 0

        for spec in CARD_SPECS:
            card_type = CardType.objects.filter(slug=spec["type_slug"]).first()
            if not card_type:
                raise CommandError(
                    f"No existe CardType con slug '{spec['type_slug']}'. "
                    "Corre el seed base de tipos primero."
                )

            race = None
            if spec["race_slug"]:
                race = Race.objects.filter(slug=spec["race_slug"]).first()
                if not race:
                    race, _ = Race.objects.get_or_create(
                        slug=spec["race_slug"],
                        defaults={
                            "myl_id": f"custom_{spec['race_slug']}",
                            "name": spec["race_slug"].capitalize(),
                        },
                    )

            rarity = Rarity.objects.filter(slug=spec["rarity_slug"]).first()
            image_url = image_map[spec["edid"]]

            card, was_created = Card.objects.update_or_create(
                myl_id=spec["myl_id"],
                defaults={
                    "edid": spec["edid"],
                    "slug": spec["slug"],
                    "name": spec["name"],
                    "edition": edition,
                    "rarity": rarity,
                    "race": race,
                    "card_type": card_type,
                    "cost": spec["cost"],
                    "damage": spec["damage"],
                    "ability": spec["ability"],
                    "flavour": "",
                    "custom_image_url": image_url,
                },
            )

            if was_created:
                created_count += 1
            else:
                updated_count += 1

            status = "Created" if was_created else "Updated"
            self.stdout.write(
                f"  {status}: {card.name} ({card.edid}) -> {image_url[:70]}..."
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Done! Created: {created_count}, Updated: {updated_count}, Total: {len(CARD_SPECS)}"
            )
        )
