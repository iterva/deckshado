"""
Update Imperio (racial) and VCR banlists for formato Imperio.
April 2026 update — MERGED with previous banlist (old entries preserved,
new entries override conflicting old ones).

Conflict resolution (new wins):
    - Anillo del Vacío:  racial limited_1 -> racial banned
    - Legión Paladín:    racial limited_2 -> racial limited_1
    - Sable Corto:       vcr limited_2    -> vcr banned

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

# -------- RACIAL --------
RACIAL_BANNED = [
    # Previous racial banlist (kept)
    ("Cancha Rayada", 321),
    ("Flechero", 896),
    ("Fusil Patriota", 324),
    ("Hitodama", 1633),
    ("Hook", 572),
    ("Horda Tenebris", 276),
    ("Ishikawa Goemon", 1541),
    ("Koromodako", 1568),
    ("Maho no Meiso", 1556),
    ("Niten Ichi Ryu", 1012),
    ("Perseguir el Sol", 946),
    ("San Bruno", 396),
    ("Senso-ji", 1642),
    ("Septimus", 597),
    ("Tenshi X-2", 1448),
    # New (April 2026)
    ("Anillo del Vacío", 1013),
    ("Kokudaka", 1733),
]

RACIAL_LIMITED_1 = [
    # Previous limited_1 (kept; Anillo del Vacío removed — promoted to banned)
    ("Anillo de Tierra", 1521),
    ("Cueva de Xalpen", 500),
    ("E.A. Poe", 879),
    ("El Rey y el Verdugo", 884),
    ("Fujibayashi Nagato", 1690),
    ("Justo Estay", 357),
    ("Levisterio", 375),
    ("Mariano Osorio", 315),
    ("Padre de la Patria", 309),
    ("Paladín (BES-017-161)", 4833),
    ("Ramón Freire", 340),
    ("Rey de Amarillo", 535),
    ("Ryugu Jo", 963),
    ("Shakar Raj", 1192),
    ("Sherlock Holmes", 551),
    ("Tesoro de los Césares", 327),
    # New (April 2026) — Legión Paladín bajó de limited_2
    ("Legión Paladín", 275),
    ("Los Umbras", 1037),
    ("León Indiferente", 238),
    ("Lucerna", 409),
    ("Manuel Bulnes", 382),
    # Únicas por habilidad de carta
    ("Torii", 940),
]

RACIAL_LIMITED_2 = [
    # Previous limited_2 (kept; Legión Paladín removida — bajó a limited_1)
    ("Alicia en Wonderland", 882),
    ("Ciudad de los Césares", 305),
    ("Cthulhu", 558),
    ("El Mago", 1044),
    ("Manuel Rodríguez", 299),
    ("Nyssara Cautiva", 259),
    ("Sheut", 253),
    # New (April 2026)
    ("Azí Sruvara", 1102),
    ("Kuchiku el Cazador", 11),
]

# -------- VCR --------
VCR_BANNED = [
    # Previous (kept)
    ("Estela Sagrada", 128),
    ("Forma de Niebla", 620),
    ("Kogarasumaru", 1557),
    ("Momificar", 831),
    ("París", 623),
    # New (April 2026) — Sable Corto promovida desde limited_2
    ("Sable Corto", 452),
    ("Libro de Thoth", 1135),
    ("Furia Berserker", 1328),
    ("Alka", 1172),
    # Carry-over de Imperio (banned en racial → banned en vcr)
    ("Anillo del Vacío", 1013),
    ("Kokudaka", 1733),
    ("Maho no Meiso", 1556),
]

VCR_LIMITED_1 = [
    # Previous (kept)
    ("Ayyappan", 1098),
    ("Azí Sruvara", 1102),
    ("El Cuero", 339),
    ("Escorpion de Seth", 833),
    ("Gusano Blanco", 595),
    ("Invasión", 80),
    ("Laterna", 936),
    ("Misil de Rastreo", 82),
    ("Monitor Araucano", 374),
    ("Oda Nobunaga", 1529),
    ("Piramide Roja", 1437),
    ("Pirata Wakou", None),
    ("Plaza de Armas", 372),
    ("Quantum Megumi", 129),
    ("Shedo Titán", 114),
    ("Tumulto Voraz", 84),
    ("Watson", 592),
    ("Zmaj Depredador", 104),
    # New (April 2026)
    ("Peripillan", 363),
    ("Capitán O'Brien", 342),
    ("Lola", 5335),
    ("Javiera Carrera", 399),
    ("Ahriman", 1111),
    ("Muro de los Caídos", 97),
    ("Tanuki", 1537),
    ("Lupus B7", 106),
    # Únicas por habilidad de carta
    ("Torii", 940),
]

VCR_LIMITED_2 = [
    # Previous (kept; Sable Corto removida — promovida a banned)
    ("Miguel Grau", 490),
]


class Command(BaseCommand):
    help = "Update Imperio (racial) and VCR banlists — April 2026 (merged)"

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
        entries += self._build("vcr", "limited_2", VCR_LIMITED_2)

        # Validate referenced card IDs
        ids = {e["card_id"] for e in entries if e["card_id"] is not None}
        existing = set(Card.objects.filter(id__in=ids).values_list("id", flat=True))
        missing = ids - existing
        if missing:
            self.stdout.write(self.style.WARNING(
                f"⚠ Card IDs no encontrados: {sorted(missing)} — entradas sin enlace"
            ))

        for e in entries:
            cid = e["card_id"]
            link = "✓" if cid in existing else ("(sin id)" if cid is None else "⚠")
            self.stdout.write(
                f"  [{e['sub_format']:6}] [{e['status']:9}] {e['card_name']} "
                f"(max {e['max_copies']}) id={cid} {link}"
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
            if payload["card_id"] is not None and payload["card_id"] not in existing:
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
