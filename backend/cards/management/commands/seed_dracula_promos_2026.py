"""
Seed de 20 cartas promocionales 2026 dentro de la edición "Drácula: Rey Vampiro".

  - 16 cartas IMP 26-xx (edid IMP26-xx), Custodios AYDV 192 P (edid AYDV-192P) y
    3 promos DRAC (DRAC-065P, 067P, 068P). Todas van a la edición drac, con rareza promo.
  - Datos transcritos de las imágenes: data/dracula_promos_2026.json
  - Imágenes en ImageKit: dracula_promos_2026_imagekit_mapping.json (key -> url)

Idempotente: cada carta se busca por (edición, nombre); si no existe, por myl_id.
Correrlo dos veces actualiza en vez de duplicar.

Uso:
    # Local (con cartas-dracula/promos-2026/ y .env.imagekit): sube imágenes y siembra
    python manage.py seed_dracula_promos_2026 --upload

    # Servidor (mapping ya commiteado): solo siembra
    python manage.py seed_dracula_promos_2026
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from cards.models import Card, CardType, Edition

from ._mapping_health import validate_mapping_urls
from .seed_dracula_rey_vampiro import CDN_FOLDER, Command as DraculaCommand
from .seed_mazo_guerreros import _load_upload_file


REPO_DIR = Path(__file__).resolve().parents[4]
DATA_FILE = Path(__file__).resolve().parent / "data" / "dracula_promos_2026.json"
DEFAULT_MAPPING_FILE = REPO_DIR / "dracula_promos_2026_imagekit_mapping.json"
DEFAULT_SOURCE_DIR = REPO_DIR / "cartas-dracula" / "promos-2026"
EDITION_MYL_ID = "custom_drac"
RARITY_SLUG = "promo"


class Command(BaseCommand):
    help = "Seed 20 cartas promo 2026 (IMP 26-xx, AYDV 192 P, DRAC 065/067/068 P) en Drácula: Rey Vampiro"

    def add_arguments(self, parser):
        parser.add_argument(
            "--upload",
            action="store_true",
            help="Sube a ImageKit las imágenes que falten en el mapping (requiere --source-dir)",
        )
        parser.add_argument("--source-dir", default=str(DEFAULT_SOURCE_DIR))
        parser.add_argument("--mapping-file", default=str(DEFAULT_MAPPING_FILE))
        parser.add_argument("--skip-url-check", action="store_true")
        parser.add_argument("--url-check-timeout", type=int, default=10)

    def handle(self, *args, **options):
        cards = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        mapping_file = Path(options["mapping_file"]).expanduser().resolve()
        mapping: dict[str, str] = {}
        if mapping_file.exists():
            mapping = json.loads(mapping_file.read_text(encoding="utf-8"))

        if options["upload"]:
            self._upload_missing(cards, mapping, Path(options["source_dir"]), mapping_file)

        missing = sorted(c["key"] for c in cards if not mapping.get(c["key"]))
        if missing:
            raise CommandError(
                f"Faltan {len(missing)} imágenes en {mapping_file.name}: {', '.join(missing)}. "
                "Corre con --upload donde estén las imágenes y .env.imagekit."
            )

        validate_mapping_urls(
            {c["key"]: mapping[c["key"]] for c in cards},
            self,
            "Drácula promos 2026",
            skip_check=options["skip_url_check"],
            timeout=max(1, options["url_check_timeout"]),
        )

        edition = Edition.objects.filter(myl_id=EDITION_MYL_ID).first()
        if edition is None:
            raise CommandError(
                "No existe la edición Drácula: Rey Vampiro. Corre antes seed_dracula_rey_vampiro."
            )

        # Reusar la resolución de rarezas/razas compuestas del seed de Drácula.
        helper = DraculaCommand(stdout=self.stdout, stderr=self.stderr)
        rarity = helper._resolve_rarity(RARITY_SLUG)
        types = {t.slug: t for t in CardType.objects.all()}

        created_count = updated_count = 0
        with transaction.atomic():
            for c in cards:
                card_type = types.get(c["type_slug"])
                if card_type is None:
                    raise CommandError(f"No existe CardType '{c['type_slug']}' ({c['edid']})")

                myl_id = f"custom_{c['key']}"
                fields = {
                    "myl_id": myl_id,
                    "edid": c["edid"],
                    "slug": f"{slugify(c['name'])}-{c['edid'].lower()}",
                    "name": c["name"],
                    "edition": edition,
                    "rarity": rarity,
                    "race": helper._resolve_race(c["race_slug"]),
                    "card_type": card_type,
                    "cost": c["cost"],
                    "damage": c["damage"],
                    "ability": c["ability"],
                    "flavour": c["flavour"],
                    "imagekit_image_url": mapping[c["key"]],
                    "custom_image_url": mapping[c["key"]],
                }
                card = (
                    Card.objects.filter(edition=edition, name=c["name"]).first()
                    or Card.objects.filter(myl_id=myl_id).first()
                )
                if card is None:
                    Card.objects.create(**fields)
                    created_count += 1
                    action = "Created"
                else:
                    for attr, value in fields.items():
                        setattr(card, attr, value)
                    card.save()
                    updated_count += 1
                    action = "Updated"
                self.stdout.write(f"  {action}: {c['edid']} {c['name']}")

        self.stdout.write(self.style.SUCCESS(
            f"\nDone! Created: {created_count}, Updated: {updated_count} ({len(cards)} total)"
        ))

    def _upload_missing(self, cards, mapping, source_dir: Path, mapping_file: Path):
        upload_file = _load_upload_file()
        os.environ["CDN_PROVIDER"] = "imagekit"
        pending = [c for c in cards if not mapping.get(c["key"])]
        self.stdout.write(self.style.MIGRATE_HEADING(
            f"Subiendo {len(pending)} imágenes a ImageKit ({CDN_FOLDER})..."
        ))
        errors = 0
        for i, c in enumerate(pending, 1):
            path = source_dir / c["image_file"]
            if not path.exists():
                self.stderr.write(f"  [{i}/{len(pending)}] FALTA {path}")
                errors += 1
                continue
            try:
                url = upload_file(str(path), public_id=f"{CDN_FOLDER}/{c['key']}", overwrite=True)
            except Exception as exc:  # noqa: BLE001 - seguir con el resto y guardar progreso
                self.stderr.write(f"  [{i}/{len(pending)}] ERROR {c['key']}: {exc}")
                errors += 1
                continue
            mapping[c["key"]] = url
            self.stdout.write(f"  [{i}/{len(pending)}] {c['key']} -> {url}")
            # Guardar tras cada subida: si se corta, la próxima corrida retoma.
            mapping_file.write_text(
                json.dumps(dict(sorted(mapping.items())), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        if errors:
            self.stderr.write(self.style.WARNING(f"{errors} imágenes no se pudieron subir."))
