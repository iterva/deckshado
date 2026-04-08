import re
import unicodedata
import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.db.models.functions import Lower
from cards.models import BanlistEntry, Card

BANLIST_URL = "https://blog.myl.cl/banlists-actualizadas/"

# Mapping from page heading text to our format codes
FORMAT_MAP = {
    "imperio": "imp",
    "furia extendido": "fx",
}

# Mapping from page sub-format text to our codes
SUB_FORMAT_MAP = {
    "formato racial:": "racial",
    "formato racial": "racial",
    "vcr:": "vcr",
    "vcr": "vcr",
    "triadas": "triadas",
    "racial libre": "racial_libre",
    "racial limitado": "racial_limitado",
}


def parse_status(text):
    """Parse restriction text and return (status, max_copies)."""
    text = text.lower().strip()
    if "prohibida" in text:
        return BanlistEntry.BANNED, 0
    if "limitada a dos copias" in text or "limitado a dos copias" in text:
        return BanlistEntry.LIMITED_2, 2
    if "limitada a una copia" in text or "limitado a una copia" in text:
        return BanlistEntry.LIMITED_1, 1
    return None, None


def clean_card_name(raw):
    """Extract card name from a list item text, removing emoji and status."""
    # Remove emoji prefixes
    raw = re.sub(r"^[⛔️☢️\s]+", "", raw)
    # Split only on en-dash/em-dash (NOT regular hyphen) to separate name from status
    parts = re.split(r"\s*[\u2013\u2014]\s*", raw, maxsplit=1)
    name = parts[0].strip()
    # Remove trailing periods and whitespace
    name = name.rstrip(". ")
    return name


STATUS_PRIORITY = {
    BanlistEntry.BANNED: 0,
    BanlistEntry.LIMITED_1: 1,
    BanlistEntry.LIMITED_2: 2,
}


class Command(BaseCommand):
    help = "Sincroniza la banlist desde blog.myl.cl"

    def add_arguments(self, parser):
        parser.add_argument(
            "--format", type=str, default="all",
            choices=["imp", "fx", "all"],
            help="Formato a sincronizar (default: all)",
        )
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Solo mostrar lo que se haría, sin escribir en la BD",
        )

    def handle(self, *args, **options):
        target_format = options["format"]
        dry_run = options["dry_run"]

        self.stdout.write(f"Descargando banlist desde {BANLIST_URL}...")
        resp = requests.get(BANLIST_URL, timeout=30)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")

        # Find the main content area
        content = soup.find("div", class_="entry-content")
        if not content:
            content = soup.find("article") or soup

        entries = []
        current_format = None
        current_sub = None

        for el in content.children:
            tag = getattr(el, "name", None)
            if not tag:
                continue

            # h2 = format heading
            if tag == "h2":
                text = el.get_text(strip=True).lower()
                current_format = FORMAT_MAP.get(text)
                current_sub = None
                if current_format:
                    self.stdout.write(f"\n--- Formato: {text} ({current_format}) ---")

            # p with strong = sub-format heading
            elif tag == "p" and current_format:
                text = el.get_text(strip=True).lower()
                matched_sub = SUB_FORMAT_MAP.get(text)
                if matched_sub:
                    current_sub = matched_sub
                    self.stdout.write(f"  Sub-formato: {current_sub}")

            # ul = list of banlist entries
            elif tag == "ul" and current_format and current_sub:
                for li in el.find_all("li", recursive=False):
                    full_text = li.get_text(strip=True)
                    name = clean_card_name(full_text)
                    status, max_copies = parse_status(full_text)

                    if not name or status is None:
                        self.stdout.write(
                            self.style.WARNING(f"    ? No se pudo parsear: {full_text}")
                        )
                        continue

                    # Handle duplicates: keep most restrictive
                    key = (name, current_format, current_sub)
                    existing = next(
                        (e for e in entries if (e["card_name"], e["format_code"], e["sub_format"]) == key),
                        None,
                    )
                    if existing:
                        if STATUS_PRIORITY.get(status, 99) < STATUS_PRIORITY.get(existing["status"], 99):
                            existing["status"] = status
                            existing["max_copies"] = max_copies
                            self.stdout.write(
                                self.style.WARNING(f"    ↑ Duplicado, se usa más restrictivo: {name} → {status}")
                            )
                        continue

                    entries.append({
                        "card_name": name,
                        "format_code": current_format,
                        "sub_format": current_sub,
                        "status": status,
                        "max_copies": max_copies,
                    })

        # Filter by target format
        if target_format != "all":
            entries = [e for e in entries if e["format_code"] == target_format]

        self.stdout.write(f"\nTotal entradas parseadas: {len(entries)}")

        if dry_run:
            for e in entries:
                self.stdout.write(
                    f"  [{e['format_code']}/{e['sub_format']}] "
                    f"{e['card_name']} → {e['status']} (max {e['max_copies']})"
                )
            return

        # Try to match card names to Card objects
        self._link_cards(entries)

        # Sync to DB
        formats_to_clear = set(e["format_code"] for e in entries)
        if target_format != "all":
            formats_to_clear = {target_format}

        deleted, _ = BanlistEntry.objects.filter(format_code__in=formats_to_clear).delete()
        if deleted:
            self.stdout.write(f"Eliminadas {deleted} entradas anteriores")

        created = 0
        linked = 0
        for e in entries:
            obj = BanlistEntry.objects.create(**e)
            created += 1
            if obj.card:
                linked += 1

        self.stdout.write(self.style.SUCCESS(
            f"\n✅ Sync completado: {created} entradas creadas, {linked} enlazadas a cartas"
        ))

    def _link_cards(self, entries):
        """Try to link each entry's card_name to a Card in the DB."""
        # Build a lookup: normalized_name → list of Card objects
        all_cards = Card.objects.select_related("edition", "edition__format").only(
            "id", "name", "edid", "edition__slug", "edition__format__code"
        )
        card_index = {}  # norm_name → [(card, edition_format_code)]
        for c in all_cards.iterator(chunk_size=2000):
            norm = self._normalize(c.name)
            card_index.setdefault(norm, []).append(c)

        for entry in entries:
            fmt = entry["format_code"]
            name = entry["card_name"]

            # Handle names with edition code like "Paladín (BES-017-161)"
            edition_hint = None
            match = re.search(r"\(([A-Z]{2,4}-\d+-\d+)\)", name)
            if match:
                edition_hint = match.group(1)
                name_clean = re.sub(r"\s*\([A-Z]{2,4}-\d+-\d+\)\s*", "", name).strip()
            else:
                name_clean = name

            norm_name = self._normalize(name_clean)
            candidates = card_index.get(norm_name, [])

            if edition_hint and candidates:
                parts = edition_hint.split("-")
                if len(parts) == 3:
                    ed_prefix = parts[0].lower()
                    edid = parts[2]
                    specific = next(
                        (c for c in candidates
                         if ed_prefix in c.edition.slug and c.edid == edid),
                        None,
                    )
                    if specific:
                        entry["card"] = specific
                        continue

            if candidates:
                # Prefer card within the target format
                fmt_match = next(
                    (c for c in candidates if c.edition.format and c.edition.format.code == fmt),
                    None,
                )
                entry["card"] = fmt_match or candidates[0]
            else:
                self.stdout.write(
                    self.style.WARNING(f"  ⚠ No se encontró carta: {name}")
                )

    @staticmethod
    def _normalize(text):
        """Normalize card name: strip accents, lowercase, remove hyphens, collapse spaces."""
        text = unicodedata.normalize("NFD", text)
        text = "".join(c for c in text if unicodedata.category(c) != "Mn")
        text = text.lower().replace("-", " ").replace(".", " ")
        text = re.sub(r"\s+", " ", text).strip()
        # Common banlist vs DB name differences
        text = text.replace("misil de rastreo", "misiles de rastreo")
        text = text.replace("cthulu", "cthulhu")
        text = text.replace("anillo del vacio", "anillo de vacio")
        text = text.replace("e a  poe", "ea poe").replace("e a poe", "ea poe")
        return text
