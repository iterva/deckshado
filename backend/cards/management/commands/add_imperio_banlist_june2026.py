"""
Add new banlist entries for formato Imperio — June 2026 update.
Does NOT delete existing entries; adds new ones or updates status if already present.

Usage:
    python manage.py add_imperio_banlist_june2026            # apply
    python manage.py add_imperio_banlist_june2026 --dry-run  # preview
"""
from django.core.management.base import BaseCommand
from cards.models import BanlistEntry, Card


FORMAT_CODE = "imp"

# -------- RACIAL (new/updated) --------
RACIAL_BANNED = [
    ("Creación de Temaukel", 510),
    ("Liberar Esclavos", 150),
]

RACIAL_LIMITED_1 = [
    ("Javiera Carrera", 399),
    ("Cthulhu", 558),
    ("Akuma el Terrible", 260),
    ("Daikaiju Furioso", 258),
    ("Batallón de Ovejas", 905),
    ("Resistencia de Acero", 283),
]

RACIAL_LIMITED_2 = [
    ("Ereshkigal", 273),
]

# -------- VCR (new/updated) --------
VCR_BANNED = [
    ("Invasión", 80),
    ("Shedo Titán", 114),
]

VCR_LIMITED_1 = [
    ("Colaborador Titán", 147),
    ("Necro Titán", 77),
    ("Prendick", 634),
    ("Wayra Tata", 389),
    ("Ik'i B'alam", 1109),
]


class Command(BaseCommand):
    help = "Add Imperio banlist entries — June 2026 update (additive, no delete)"

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
        entries += self._build("racial", "banned", RACIAL_BANNED)
        entries += self._build("racial", "limited_1", RACIAL_LIMITED_1)
        entries += self._build("racial", "limited_2", RACIAL_LIMITED_2)
        entries += self._build("vcr", "banned", VCR_BANNED)
        entries += self._build("vcr", "limited_1", VCR_LIMITED_1)

        # Validate referenced card IDs
        ids = {e["card_id"] for e in entries if e["card_id"] is not None}
        existing_ids = set(Card.objects.filter(id__in=ids).values_list("id", flat=True))
        missing = ids - existing_ids
        if missing:
            self.stdout.write(self.style.WARNING(
                f"⚠ Card IDs no encontrados: {sorted(missing)} — entradas sin enlace"
            ))

        created = 0
        updated = 0

        for e in entries:
            cid = e["card_id"]
            if cid not in existing_ids:
                cid = None

            action = "—"
            if not dry_run:
                obj, was_created = BanlistEntry.objects.update_or_create(
                    format_code=e["format_code"],
                    sub_format=e["sub_format"],
                    card_name=e["card_name"],
                    defaults={
                        "status": e["status"],
                        "max_copies": e["max_copies"],
                        "card_id": cid,
                    },
                )
                if was_created:
                    created += 1
                    action = "NEW"
                else:
                    updated += 1
                    action = "UPD"
            else:
                exists = BanlistEntry.objects.filter(
                    format_code=e["format_code"],
                    sub_format=e["sub_format"],
                    card_name=e["card_name"],
                ).first()
                action = "UPD" if exists else "NEW"

            link = "✓" if cid and cid in existing_ids else "⚠"
            self.stdout.write(
                f"  [{action}] [{e['sub_format']:6}] [{e['status']:9}] "
                f"{e['card_name']} (max {e['max_copies']}) id={e['card_id']} {link}"
            )

        if dry_run:
            self.stdout.write(f"\n(dry-run) {len(entries)} entradas procesadas")
        else:
            self.stdout.write(self.style.SUCCESS(
                f"\n✅ Imperio banlist June 2026: {created} creadas, {updated} actualizadas"
            ))
