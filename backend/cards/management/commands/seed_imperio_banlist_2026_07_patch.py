"""
Parche puntual de banlist Imperio (2026-07) con cambios reportados.

Cambios aplicados:
- Cthulhu -> Prohibida (racial)
- Yelmo Mambrino -> Limitada a 1 (racial)
- Crono Diamante -> Limitada a 1 (racial)
- Mariano Osorio -> Libre (se elimina entrada imp)
- Justo Estay -> Libre (se elimina entrada imp)
- Javiera Carrera -> Libre (se elimina entrada imp, racial/vcr)
- Manuel Rodriguez -> Libre (se elimina entrada imp)
- Ciudad de los Cesares -> Libre (se elimina entrada imp)
- Daikaiju Furioso -> Libre (se elimina entrada imp)

Uso:
  python manage.py seed_imperio_banlist_2026_07_patch
  python manage.py seed_imperio_banlist_2026_07_patch --dry-run
"""

from __future__ import annotations

import re
import unicodedata

from django.core.management.base import BaseCommand

from cards.models import BanlistEntry, Card


FORMAT_CODE = "imp"
TARGET_SUBFORMATS = ("racial", "vcr")

TO_SET = [
    ("Cthulhu", "racial", BanlistEntry.BANNED, 0),
    ("Yelmo Mambrino", "racial", BanlistEntry.LIMITED_1, 1),
    ("Crono Diamante", "racial", BanlistEntry.LIMITED_1, 1),
]

TO_UNLIMIT = [
    "Mariano Osorio",
    "Justo Estay",
    "Javiera Carrera",
    "Manuel Rodriguez",
    "Ciudad de los Cesares",
    "Daikaiju Furioso",
]


def _normalize_key(text: str | None) -> str:
    value = unicodedata.normalize("NFD", text or "")
    value = "".join(ch for ch in value if unicodedata.category(ch) != "Mn")
    value = value.lower().replace("’", "'").replace("`", "'").replace("´", "'")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _link_card(card_name: str) -> Card | None:
    card = Card.objects.filter(name__iexact=card_name).first()
    if card:
        return card

    key = _normalize_key(card_name)
    for candidate in Card.objects.filter(name__icontains=card_name.split(" ")[0]):
        if _normalize_key(candidate.name) == key:
            return candidate
    return None


class Command(BaseCommand):
    help = "Aplica parche puntual de banlist Imperio (2026-07)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Solo muestra cambios, sin escribir en BD",
        )

    def handle(self, *args, **options):
        dry_run = bool(options["dry_run"])

        existing = list(
            BanlistEntry.objects.filter(
                format_code=FORMAT_CODE,
                sub_format__in=TARGET_SUBFORMATS,
            ).select_related("card")
        )

        created = 0
        updated = 0
        deleted = 0
        kept = 0

        # 1) Aplicar estados (banned/limited_1)
        for card_name, sub_format, status, max_copies in TO_SET:
            key = _normalize_key(card_name)
            matches = [
                entry for entry in existing
                if entry.sub_format == sub_format and _normalize_key(entry.card_name) == key
            ]

            if matches:
                entry = matches[0]
                changed = False

                if entry.card_name != card_name:
                    entry.card_name = card_name
                    changed = True
                if entry.status != status:
                    entry.status = status
                    changed = True
                if entry.max_copies != max_copies:
                    entry.max_copies = max_copies
                    changed = True

                if entry.card_id is None:
                    linked = _link_card(card_name)
                    if linked is not None:
                        entry.card = linked
                        changed = True

                if changed:
                    updated += 1
                    self.stdout.write(
                        f"  [{'DRY ' if dry_run else ''}UPD] {card_name} -> {status} ({sub_format})"
                    )
                    if not dry_run:
                        entry.save(update_fields=["card_name", "status", "max_copies", "card"])
                else:
                    kept += 1
                    self.stdout.write(f"  KEEP {card_name} ({sub_format})")
                continue

            linked = _link_card(card_name)
            created += 1
            self.stdout.write(
                f"  [{'DRY ' if dry_run else ''}NEW] {card_name} -> {status} ({sub_format})"
            )
            if not dry_run:
                new_entry = BanlistEntry.objects.create(
                    card_name=card_name,
                    format_code=FORMAT_CODE,
                    sub_format=sub_format,
                    status=status,
                    max_copies=max_copies,
                    card=linked,
                )
                existing.append(new_entry)

        # 2) Eliminar entradas que pasan a Libre
        unlimit_keys = {_normalize_key(name) for name in TO_UNLIMIT}
        to_delete = [
            entry for entry in existing
            if _normalize_key(entry.card_name) in unlimit_keys
        ]

        seen = set()
        for entry in to_delete:
            uniq = (entry.card_name, entry.sub_format)
            if uniq in seen:
                continue
            seen.add(uniq)

            deleted += 1
            self.stdout.write(
                f"  [{'DRY ' if dry_run else ''}DEL] {entry.card_name} ({entry.sub_format}) -> libre"
            )

        if not dry_run and to_delete:
            BanlistEntry.objects.filter(id__in=[entry.id for entry in to_delete]).delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Created={created} Updated={updated} Deleted={deleted} Kept={kept}"
            )
        )
