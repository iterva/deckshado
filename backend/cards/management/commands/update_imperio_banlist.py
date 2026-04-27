"""
Update Imperio (racial) and VCR banlists for formato Imperio.
Banlist source: official update (April 2026).

Also fixes typos:
- BanlistEntry "Cthulu" -> "Cthulhu"
- Card name "trempilcahue" -> "tempilcahue"

Usage:
    python manage.py update_imperio_banlist            # apply
    python manage.py update_imperio_banlist --dry-run  # preview
"""
from django.core.management.base import BaseCommand
from cards.models import BanlistEntry, Card


FORMAT_CODE = "imp"

# (card_name, card_id) — IDs are pinned so links remain stable across re-runs.
IMPERIO_BANNED = [
    ("Anillo del Vacío", 1013),
    ("Kokudaka", 1733),
]
IMPERIO_LIMITED_1 = [
    ("Legión Paladín", 275),
    ("Los Umbras", 1037),
    ("León Indiferente", 238),
    ("Lucerna", 409),
    ("Manuel Bulnes", 382),
]
IMPERIO_LIMITED_2 = [
    ("Azí Sruvara", 1102),
    ("Kuchiku el Cazador", 11),
]

VCR_BANNED_EXTRA = [
    ("Sable Corto", 452),
    ("Libro de Thoth", 1135),
    ("Furia Berserker", 1328),
    ("Alka", 1172),
]
VCR_BANNED = VCR_BANNED_EXTRA + IMPERIO_BANNED  # carry-over from Imperio
VCR_LIMITED_1 = [
    ("Peripillan", 363),
    ("Capitán O'Brien", 342),
    ("Lola", 5335),
    ("Javiera Carrera", 399),
    ("Ahriman", 1111),
    ("Muro de los Caídos", 97),
    ("Tanuki", 1537),
    ("Lupus B7", 106),
]
VCR_LIMITED_2: list[tuple[str, int]] = []


class Command(BaseCommand):
    help = "Update Imperio (racial) and VCR banlists"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Solo mostrar lo que se haría, sin escribir en la BD",
        )

    def _max_copies(self, status):
        return 0 if status == "banned" else (1 if status == "limited_1" else 2)

    def _build(self, sub_format, status, items):
        out = []
        for name, cid in items:
            out.append({
                "card_name": name,
                "format_code": FORMAT_CODE,
                "sub_format": sub_format,
                "status": status,
                "max_copies": self._max_copies(status),
                "card_id": cid,
            })
        return out

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        entries = []
        entries += self._build("racial", "banned", IMPERIO_BANNED)
        entries += self._build("racial", "limited_1", IMPERIO_LIMITED_1)
        entries += self._build("racial", "limited_2", IMPERIO_LIMITED_2)
        entries += self._build("vcr", "banned", VCR_BANNED)
        entries += self._build("vcr", "limited_1", VCR_LIMITED_1)
        entries += self._build("vcr", "limited_2", VCR_LIMITED_2)

        # Validate that referenced card IDs exist
        ids = {e["card_id"] for e in entries}
        existing = set(Card.objects.filter(id__in=ids).values_list("id", flat=True))
        missing = ids - existing
        if missing:
            self.stdout.write(self.style.WARNING(
                f"⚠ Card IDs no encontrados: {sorted(missing)} — se crearán entradas sin enlace"
            ))

        for e in entries:
            link = "✓" if e["card_id"] in existing else "⚠ sin enlace"
            self.stdout.write(
                f"  [{e['sub_format']:6}] [{e['status']:9}] {e['card_name']} "
                f"(max {e['max_copies']}) id={e['card_id']} {link}"
            )

        if dry_run:
            self.stdout.write(f"\n(dry-run) {len(entries)} entradas para imp/racial+vcr")
            return

        deleted, _ = BanlistEntry.objects.filter(
            format_code=FORMAT_CODE, sub_format__in=["racial", "vcr"]
        ).delete()
        if deleted:
            self.stdout.write(f"Eliminadas {deleted} entradas previas (racial+vcr)")

        for e in entries:
            payload = dict(e)
            if payload["card_id"] not in existing:
                payload["card_id"] = None
            BanlistEntry.objects.create(**payload)

        # --- Fix typos ---
        b = BanlistEntry.objects.filter(card_name="Cthulu").first()
        if b:
            b.card_name = "Cthulhu"
            b.save()
            self.stdout.write("Typo corregido: BanlistEntry 'Cthulu' -> 'Cthulhu'")

        c = Card.objects.filter(name="trempilcahue").first()
        if c:
            c.name = "tempilcahue"
            c.save()
            self.stdout.write("Typo corregido: Card 'trempilcahue' -> 'tempilcahue'")

        self.stdout.write(self.style.SUCCESS(
            f"\n✅ Imperio banlist actualizada: {len(entries)} entradas (racial+vcr)"
        ))
