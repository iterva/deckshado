"""
Seed the VCR banlist entries for formato Imperio.
Data sourced from the official VCR banlist image (April 2026).
"""
import re
import unicodedata

from django.core.management.base import BaseCommand
from cards.models import BanlistEntry, Card


VCR_BANLIST = [
    # Prohibidas (banned, max_copies=0)
    ("Estela Sagrada",      "banned", 0),
    ("Momificar",           "banned", 0),
    ("Kogarasumaru",        "banned", 0),
    ("París",               "banned", 0),
    ("Forma de Niebla",     "banned", 0),

    # Limitada a una copia (limited_1, max_copies=1)
    ("Shedo Titán",         "limited_1", 1),
    ("Invasión",            "limited_1", 1),
    ("Tumulto Voraz",       "limited_1", 1),
    ("Plaza de Armas",      "limited_1", 1),
    ("Zmaj Depredador",     "limited_1", 1),
    ("Laterna",             "limited_1", 1),
    ("Oda Nobunaga",        "limited_1", 1),
    ("Azí Sruvara",         "limited_1", 1),
    ("Piramide Roja",       "limited_1", 1),
    ("Pirata Wakou",        "limited_1", 1),
    ("Escorpion de Seth",   "limited_1", 1),
    ("Monitor Araucano",    "limited_1", 1),
    ("Ayyappan",            "limited_1", 1),
    ("Quantum Megumi",      "limited_1", 1),
    ("Misil de Rastreo",    "limited_1", 1),
    ("El Cuero",            "limited_1", 1),
    ("Watson",              "limited_1", 1),
    ("Gusano Blanco",       "limited_1", 1),

    # Limitada a dos copias (limited_2, max_copies=2)
    ("Miguel Grau",         "limited_2", 2),
    ("Sable Corto",         "limited_2", 2),
]

FORMAT_CODE = "imp"
SUB_FORMAT = "vcr"


def normalize(text):
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.lower().replace("-", " ").replace(".", " ")
    text = re.sub(r"\s+", " ", text).strip()
    text = text.replace("misil de rastreo", "misiles de rastreo")
    return text


class Command(BaseCommand):
    help = "Seed VCR banlist entries for formato Imperio"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Solo mostrar lo que se haría, sin escribir en la BD",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        # Build card name index for linking
        all_cards = Card.objects.select_related("edition", "edition__format").only(
            "id", "name", "edition__slug", "edition__format__code"
        )
        card_index = {}
        for c in all_cards.iterator(chunk_size=2000):
            norm = normalize(c.name)
            card_index.setdefault(norm, []).append(c)

        entries_data = []
        for card_name, status, max_copies in VCR_BANLIST:
            norm_name = normalize(card_name)
            candidates = card_index.get(norm_name, [])

            # Prefer card within imp format
            linked_card = None
            if candidates:
                fmt_match = next(
                    (c for c in candidates if c.edition.format and c.edition.format.code == FORMAT_CODE),
                    None,
                )
                linked_card = fmt_match or candidates[0]

            entries_data.append({
                "card_name": card_name,
                "format_code": FORMAT_CODE,
                "sub_format": SUB_FORMAT,
                "status": status,
                "max_copies": max_copies,
                "card": linked_card,
            })

            link_info = f"→ {linked_card}" if linked_card else "⚠ sin enlace"
            self.stdout.write(f"  [{status}] {card_name} (max {max_copies}) {link_info}")

        if dry_run:
            self.stdout.write(f"\n(dry-run) {len(entries_data)} entradas para VCR")
            return

        # Clear existing VCR banlist
        deleted, _ = BanlistEntry.objects.filter(
            format_code=FORMAT_CODE, sub_format=SUB_FORMAT
        ).delete()
        if deleted:
            self.stdout.write(f"Eliminadas {deleted} entradas VCR anteriores")

        created = 0
        linked = 0
        for e in entries_data:
            BanlistEntry.objects.create(**e)
            created += 1
            if e["card"]:
                linked += 1

        self.stdout.write(self.style.SUCCESS(
            f"\n✅ VCR banlist: {created} entradas creadas, {linked} enlazadas a cartas"
        ))
