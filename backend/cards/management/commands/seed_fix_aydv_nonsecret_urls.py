from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from cards.models import Card, Edition


DEFAULT_MAPPING_FILE = Path(__file__).resolve().parents[4] / "aydv_vigilantes_nonsecret_mapping.json"
TARGET_EDITION_SLUG = "aydv"
TRIGGER_RARITIES = {"secreta", "legendaria"}


def _norm(text: str | None) -> str:
    value = (text or "").strip().replace("�", "")
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


class Command(BaseCommand):
    help = (
        "Corrige URLs de cartas no secretas/no legendarias en AYDV cuando existe "
        "contraparte secreta/legendaria, usando mapping de URLs previamente subidas."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--edition-slug",
            default=TARGET_EDITION_SLUG,
            help="Slug de edición objetivo (default: aydv)",
        )
        parser.add_argument(
            "--mapping-file",
            default=str(DEFAULT_MAPPING_FILE),
            help="Ruta a mapping JSON (myl_id -> image_url)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="No guarda cambios en BD",
        )
        parser.add_argument(
            "--progress-every",
            type=int,
            default=5,
            help="Imprime progreso cada N cartas (default: 5)",
        )

    def handle(self, *args, **options):
        edition_slug = str(options["edition_slug"] or TARGET_EDITION_SLUG).strip().lower()
        mapping_file = Path(options["mapping_file"]).expanduser().resolve()
        dry_run = bool(options["dry_run"])
        progress_every = max(1, int(options.get("progress_every") or 5))

        edition = Edition.objects.filter(slug=edition_slug).first()
        if not edition:
            raise CommandError(f"No existe edición con slug '{edition_slug}'")

        if edition_slug == TARGET_EDITION_SLUG:
            name = (edition.name or "").lower()
            if "vigilantes" not in name:
                raise CommandError(
                    f"La edición '{edition.slug}' no parece ser 'Ángeles y Demonios: Vigilantes' (name={edition.name!r})"
                )

        if not mapping_file.exists():
            raise CommandError(f"No existe mapping file: {mapping_file}")

        try:
            mapping = json.loads(mapping_file.read_text(encoding="utf-8"))
        except ValueError as exc:
            raise CommandError(f"Mapping JSON inválido: {mapping_file}") from exc

        if not isinstance(mapping, dict):
            raise CommandError("El mapping debe ser un objeto JSON de myl_id -> url")

        cards = list(Card.objects.filter(edition=edition).select_related("rarity").order_by("id"))
        if not cards:
            raise CommandError(f"La edición '{edition.slug}' no tiene cartas")

        trigger_names: set[str] = set()
        for card in cards:
            rarity_slug = str(getattr(getattr(card, "rarity", None), "slug", "") or "").strip().lower()
            if rarity_slug in TRIGGER_RARITIES:
                trigger_names.add(_norm(card.name))

        targets: list[Card] = []
        for card in cards:
            rarity_slug = str(getattr(getattr(card, "rarity", None), "slug", "") or "").strip().lower()
            if rarity_slug in TRIGGER_RARITIES:
                continue
            if _norm(card.name) in trigger_names:
                targets.append(card)

        total = len(targets)
        if total == 0:
            raise CommandError("No se encontraron cartas objetivo para corregir")

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"Edición {edition.slug} ({edition.name}): corrigiendo {total} no-secretas/no-legendarias"
            )
        )

        updated = 0
        kept = 0
        missing_map = 0
        missing_myl_id = 0

        for idx, card in enumerate(targets, start=1):
            myl_id = str(card.myl_id or "").strip()
            if not myl_id:
                missing_myl_id += 1
            else:
                mapped_url = str(mapping.get(myl_id) or "").strip()
                if not mapped_url:
                    missing_map += 1
                elif mapped_url == (card.custom_image_url or "").strip():
                    kept += 1
                else:
                    if not dry_run:
                        card.custom_image_url = mapped_url
                        card.save(update_fields=["custom_image_url"])
                    updated += 1

            if idx % progress_every == 0 or idx == total:
                pct = (idx / total) * 100 if total else 100
                self.stdout.write(
                    f"[apply {idx}/{total} {pct:.1f}%] Updated={updated} Kept={kept} "
                    f"MissingMap={missing_map} MissingMylId={missing_myl_id}"
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Targets={total} Updated={updated} Kept={kept} "
                f"MissingMap={missing_map} MissingMylId={missing_myl_id}"
            )
        )
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN: no se guardaron cambios en BD."))
