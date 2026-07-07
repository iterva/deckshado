"""
Seed aditivo de banlist Imperio (racial + VCR) desde blog oficial.

- No elimina entradas existentes.
- Solo crea/actualiza entradas encontradas en la banlist publicada.
- Ignora filas marcadas como Libre.

Uso:
    python manage.py seed_imperio_vcr_banlist_blog
    python manage.py seed_imperio_vcr_banlist_blog --dry-run
"""
import re
import unicodedata

import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand, CommandError

from cards.models import BanlistEntry, Card


BANLIST_URL = "https://blog.myl.cl/banlists-actualizadas/"
FORMAT_CODE = "imp"
TARGET_SUBFORMATS = {"racial", "vcr"}

STATUS_PRIORITY = {
    BanlistEntry.BANNED: 0,
    BanlistEntry.LIMITED_1: 1,
    BanlistEntry.LIMITED_2: 2,
}

# Snapshot de respaldo (2026-07-06) para entornos sin salida HTTPS al blog.
FALLBACK_BANLIST = [
    ("racial", "Akuma el Terrible", BanlistEntry.LIMITED_1),
    ("racial", "Alicia en Wonderland", BanlistEntry.LIMITED_2),
    ("racial", "Azí Sruvara", BanlistEntry.LIMITED_2),
    ("racial", "Batallón de Ovejas", BanlistEntry.LIMITED_1),
    ("racial", "Cancha Rayada", BanlistEntry.BANNED),
    ("racial", "Creación de Temaukel", BanlistEntry.BANNED),
    ("racial", "Crono Diamante", BanlistEntry.LIMITED_1),
    ("racial", "Cthulhu", BanlistEntry.BANNED),
    ("racial", "Cueva de Xalpen", BanlistEntry.LIMITED_1),
    ("racial", "E.A. Poe", BanlistEntry.LIMITED_1),
    ("racial", "El Mago", BanlistEntry.LIMITED_2),
    ("racial", "El Rey y el Verdugo", BanlistEntry.LIMITED_1),
    ("racial", "Ereshkigal", BanlistEntry.LIMITED_2),
    ("racial", "Flechero", BanlistEntry.BANNED),
    ("racial", "Fusil Patriota", BanlistEntry.BANNED),
    ("racial", "Hook", BanlistEntry.BANNED),
    ("racial", "Horda Tenebris", BanlistEntry.BANNED),
    ("racial", "Kuchiku el Cazador", BanlistEntry.LIMITED_2),
    ("racial", "Legión Paladín", BanlistEntry.LIMITED_1),
    ("racial", "Levisterio", BanlistEntry.LIMITED_1),
    ("racial", "León Indiferente", BanlistEntry.LIMITED_1),
    ("racial", "Liberar Esclavos", BanlistEntry.BANNED),
    ("racial", "Los Umbras", BanlistEntry.LIMITED_1),
    ("racial", "Lucerna", BanlistEntry.LIMITED_1),
    ("racial", "Manuel Bulnes", BanlistEntry.LIMITED_1),
    ("racial", "Nyssara Cautiva", BanlistEntry.LIMITED_2),
    ("racial", "Padre de la Patria", BanlistEntry.LIMITED_1),
    ("racial", "Paladín (BES-017-161)", BanlistEntry.LIMITED_1),
    ("racial", "Perseguir el Sol", BanlistEntry.BANNED),
    ("racial", "Ramón Freire", BanlistEntry.LIMITED_1),
    ("racial", "Resistencia de Acero", BanlistEntry.LIMITED_1),
    ("racial", "Rey de Amarillo", BanlistEntry.LIMITED_1),
    ("racial", "Ryugu Jo", BanlistEntry.LIMITED_1),
    ("racial", "San Bruno", BanlistEntry.BANNED),
    ("racial", "Septimus", BanlistEntry.BANNED),
    ("racial", "Sherlock Holmes", BanlistEntry.LIMITED_1),
    ("racial", "Sheut", BanlistEntry.LIMITED_2),
    ("racial", "Tesoro de los Césares", BanlistEntry.LIMITED_1),
    ("racial", "Yelmo Mambrino", BanlistEntry.LIMITED_1),
    ("vcr", "Ahriman", BanlistEntry.LIMITED_1),
    ("vcr", "Alka", BanlistEntry.BANNED),
    ("vcr", "Ayyappan", BanlistEntry.LIMITED_1),
    ("vcr", "Azí Sruvara", BanlistEntry.LIMITED_1),
    ("vcr", "Capitan O'Brien", BanlistEntry.LIMITED_1),
    ("vcr", "Colaborador Titán", BanlistEntry.LIMITED_1),
    ("vcr", "El Cuero", BanlistEntry.LIMITED_1),
    ("vcr", "Escorpion de Seth", BanlistEntry.LIMITED_1),
    ("vcr", "Estela Sagrada", BanlistEntry.BANNED),
    ("vcr", "Forma de Niebla", BanlistEntry.BANNED),
    ("vcr", "Furia Berserker", BanlistEntry.BANNED),
    ("vcr", "Gusano Blanco", BanlistEntry.LIMITED_1),
    ("vcr", "Ik'i B'alam", BanlistEntry.LIMITED_1),
    ("vcr", "Invasión", BanlistEntry.BANNED),
    ("vcr", "Javiera Carrera", BanlistEntry.LIMITED_1),
    ("vcr", "Kogarasumaru", BanlistEntry.BANNED),
    ("vcr", "Laterna", BanlistEntry.LIMITED_1),
    ("vcr", "Libro de Thoth", BanlistEntry.BANNED),
    ("vcr", "Lola", BanlistEntry.LIMITED_1),
    ("vcr", "Lupus B7", BanlistEntry.LIMITED_1),
    ("vcr", "Miguel Grau", BanlistEntry.LIMITED_2),
    ("vcr", "Misil de Rastreo", BanlistEntry.LIMITED_1),
    ("vcr", "Momificar", BanlistEntry.BANNED),
    ("vcr", "Monitor Araucano", BanlistEntry.LIMITED_1),
    ("vcr", "Muro de los Caídos", BanlistEntry.LIMITED_1),
    ("vcr", "Necro Titán", BanlistEntry.LIMITED_1),
    ("vcr", "Oda Nobunaga", BanlistEntry.LIMITED_1),
    ("vcr", "París", BanlistEntry.BANNED),
    ("vcr", "Peripillan", BanlistEntry.LIMITED_1),
    ("vcr", "Piramide Roja", BanlistEntry.LIMITED_1),
    ("vcr", "Pirata Wakou", BanlistEntry.LIMITED_1),
    ("vcr", "Plaza de Armas", BanlistEntry.LIMITED_1),
    ("vcr", "Prendick", BanlistEntry.LIMITED_1),
    ("vcr", "Quantum Megumi", BanlistEntry.LIMITED_1),
    ("vcr", "Sable Corto", BanlistEntry.BANNED),
    ("vcr", "Shedo Titán", BanlistEntry.BANNED),
    ("vcr", "Tanuki", BanlistEntry.LIMITED_1),
    ("vcr", "Tumulto Voraz", BanlistEntry.LIMITED_1),
    ("vcr", "Watson", BanlistEntry.LIMITED_1),
    ("vcr", "Wayra Tata", BanlistEntry.LIMITED_1),
    ("vcr", "Zmaj Depredador", BanlistEntry.LIMITED_1),
]


def normalize_spaces(text):
    return re.sub(r"\s+", " ", (text or "").replace("\xa0", " ")).strip()


def strip_accents(text):
    text = unicodedata.normalize("NFD", text or "")
    return "".join(ch for ch in text if unicodedata.category(ch) != "Mn")


def normalize_key(text):
    text = strip_accents(normalize_spaces(text)).lower()
    text = text.replace("’", "'").replace("`", "'").replace("´", "'")
    text = text.replace("-", " ").replace(".", " ")
    text = re.sub(r"[^a-z0-9' ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    # Variantes frecuentes entre blog y DB.
    text = text.replace("cthulu", "cthulhu")
    text = text.replace("misil de rastreo", "misiles de rastreo")
    text = text.replace("libro de thot", "libro de thoth")
    text = text.replace("ryugu jo", "ryugu jo")
    text = text.replace("sherlok holmes", "sherlock holmes")
    text = text.replace("o brian", "o'brien")
    text = text.replace("o' brian", "o'brien")
    text = text.replace("s hedo titan", "shedo titan")
    text = text.replace("xalpen", "xalpen")
    return text


def parse_status(text):
    low = normalize_key(text)
    if "prohibida" in low:
        return BanlistEntry.BANNED, 0
    if "limitada a dos copias" in low or "limitado a dos copias" in low:
        return BanlistEntry.LIMITED_2, 2
    if "limitada a una copia" in low or "limitado a una copia" in low:
        return BanlistEntry.LIMITED_1, 1
    return None, None


def extract_name_from_li(raw_text):
    text = normalize_spaces(raw_text)
    text = re.sub(r"^[\-\*\u2022\s]+", "", text)
    text = re.sub(r"^[^\w]+", "", text)

    low = normalize_key(text)
    markers = [
        "prohibida",
        "limitada a una copia",
        "limitado a una copia",
        "limitada a dos copias",
        "limitado a dos copias",
        "libre",
    ]
    cut = len(text)
    for marker in markers:
        idx = low.find(marker)
        if idx != -1:
            cut = min(cut, idx)
    text = text[:cut]

    text = re.sub(r"\s+[\-\u2013\u2014]\s*$", "", text)
    text = text.rstrip(" -\u2013\u2014:;.,")
    return normalize_spaces(text)


class Command(BaseCommand):
    help = "Seed aditivo de banlist Imperio (racial + VCR) desde blog oficial"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Solo mostrar cambios, sin escribir en BD",
        )
        parser.add_argument(
            "--url", type=str, default=BANLIST_URL,
            help=f"URL de banlist a parsear (default: {BANLIST_URL})",
        )
        parser.add_argument(
            "--source", type=str, default="auto", choices=["auto", "web", "fallback"],
            help="Fuente de datos: auto (intenta web y cae a fallback), web, fallback",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        url = options["url"]
        source = options["source"]

        parsed = None

        if source in {"auto", "web"}:
            self.stdout.write(f"Descargando banlist desde {url}...")
            try:
                response = requests.get(url, timeout=30)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, "lxml")
                content = soup.find("div", class_="entry-content") or soup.find("article") or soup
                parsed = self._parse_imperio_section(content)
            except requests.RequestException as exc:
                if source == "web":
                    raise CommandError(f"No se pudo descargar la banlist desde web: {exc}") from exc
                self.stdout.write(self.style.WARNING(
                    f"No se pudo descargar la banlist ({exc}). Se usara fallback local."
                ))

        if source == "fallback" or not parsed:
            self.stdout.write("Usando snapshot fallback de banlist (2026-07-06)...")
            parsed = self._build_entries_from_fallback()

        if not parsed:
            self.stdout.write(self.style.ERROR("No se encontraron entradas parseables para Imperio/VCR."))
            return

        parsed = self._normalize_with_existing_names(parsed)
        parsed = self._attach_cards(parsed)

        created = 0
        updated = 0

        for entry in sorted(parsed.values(), key=lambda e: (e["sub_format"], e["card_name"])):
            lookup = {
                "card_name": entry["card_name"],
                "format_code": entry["format_code"],
                "sub_format": entry["sub_format"],
            }
            defaults = {
                "status": entry["status"],
                "max_copies": entry["max_copies"],
                "card": entry["card"],
            }

            if dry_run:
                exists = BanlistEntry.objects.filter(**lookup).exists()
                action = "UPD" if exists else "NEW"
            else:
                _, was_created = BanlistEntry.objects.update_or_create(
                    **lookup,
                    defaults=defaults,
                )
                action = "NEW" if was_created else "UPD"
                if was_created:
                    created += 1
                else:
                    updated += 1

            card_info = f"id={entry['card'].id}" if entry["card"] else "sin_link"
            self.stdout.write(
                f"  [{action}] [{entry['sub_format']}] [{entry['status']}] "
                f"{entry['card_name']} (max {entry['max_copies']}) {card_info}"
            )

        total = len(parsed)
        if dry_run:
            self.stdout.write(self.style.SUCCESS(f"\n(dry-run) {total} entradas detectadas para upsert"))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"\nSeed completado: {total} procesadas, {created} creadas, {updated} actualizadas"
            ))

    def _parse_imperio_section(self, content):
        entries = {}

        imperio_h2 = content.find(
            lambda tag: getattr(tag, "name", None) == "h2" and "imperio" in normalize_key(tag.get_text(" ", strip=True))
        )
        if not imperio_h2:
            return entries

        mode = "racial"

        for node in imperio_h2.next_elements:
            if node is imperio_h2:
                continue

            tag = getattr(node, "name", None)
            if not tag:
                continue

            if tag == "h2":
                break

            text = normalize_spaces(node.get_text(" ", strip=True))
            key_text = normalize_key(text)

            if tag in {"p", "h3", "h4"}:
                if re.search(r"\bvcr\b", key_text):
                    mode = "vcr"
                    continue
                if "triadas" in key_text:
                    mode = None
                    continue
                if "formato racial" in key_text or key_text == "racial":
                    mode = "racial"
                    continue

            if tag == "table":
                table_sub = mode or "racial"
                for row in node.find_all("tr"):
                    cells = [normalize_spaces(c.get_text(" ", strip=True)) for c in row.find_all(["td", "th"])]
                    if not cells:
                        continue

                    joined = normalize_key(" ".join(cells))
                    if "nombre" in joined and "estatus" in joined:
                        continue

                    status, max_copies = parse_status(cells[-1])
                    if status is None:
                        continue

                    sub = table_sub
                    if re.search(r"\bvcr\b", joined):
                        sub = "vcr"
                    elif sub is None:
                        sub = "racial"

                    name = self._extract_name_from_table_cells(cells)
                    if not name:
                        continue

                    self._add_entry(entries, name, sub, status, max_copies)

            if tag == "ul" and mode in TARGET_SUBFORMATS:
                for li in node.find_all("li", recursive=False):
                    li_text = normalize_spaces(li.get_text(" ", strip=True))
                    status, max_copies = parse_status(li_text)
                    if status is None:
                        continue
                    name = extract_name_from_li(li_text)
                    if not name:
                        continue
                    self._add_entry(entries, name, mode, status, max_copies)

        return entries

    def _extract_name_from_table_cells(self, cells):
        if len(cells) >= 5:
            # [actualizacion, formato, nombre, edicion, estatus]
            return normalize_spaces(cells[2])
        if len(cells) == 4:
            # [formato, nombre, edicion, estatus] o [actualizacion, nombre, edicion, estatus]
            first = normalize_key(cells[0])
            if "imperio" in first or "vcr" in first:
                return normalize_spaces(cells[1])
            return normalize_spaces(cells[1])
        if len(cells) >= 2:
            return normalize_spaces(cells[0])
        return None

    @staticmethod
    def _max_copies(status):
        return 0 if status == BanlistEntry.BANNED else (1 if status == BanlistEntry.LIMITED_1 else 2)

    def _build_entries_from_fallback(self):
        entries = {}
        for sub_format, card_name, status in FALLBACK_BANLIST:
            self._add_entry(
                entries,
                raw_name=card_name,
                sub_format=sub_format,
                status=status,
                max_copies=self._max_copies(status),
            )
        return entries

    def _add_entry(self, entries, raw_name, sub_format, status, max_copies):
        if sub_format not in TARGET_SUBFORMATS:
            return

        name = normalize_spaces(raw_name).rstrip(" .")
        key = (sub_format, normalize_key(name))
        payload = {
            "card_name": name,
            "format_code": FORMAT_CODE,
            "sub_format": sub_format,
            "status": status,
            "max_copies": max_copies,
            "card": None,
        }

        existing = entries.get(key)
        if not existing:
            entries[key] = payload
            return

        # Si aparece repetida con conflicto, conservar la mas restrictiva.
        if STATUS_PRIORITY[status] < STATUS_PRIORITY[existing["status"]]:
            entries[key] = payload

    def _normalize_with_existing_names(self, entries):
        alias_by_key = {
            normalize_key("Sherlok Holmes"): "Sherlock Holmes",
            normalize_key("Ryugu-Jo"): "Ryugu Jo",
            normalize_key("Libro de Thot"): "Libro de Thoth",
            normalize_key("Capitan O'Brian"): "Capitan O'Brien",
            normalize_key("Capitan O Brian"): "Capitan O'Brien",
            normalize_key("Azi Sruvara"): "Azi Sruvara",
            normalize_key("Peripillan"): "Peripillan",
            normalize_key("S hedo Titan"): "Shedo Titán",
        }

        existing_rows = BanlistEntry.objects.filter(
            format_code=FORMAT_CODE,
            sub_format__in=TARGET_SUBFORMATS,
        ).only("card_name", "sub_format")
        existing_name_by_key = {
            (row.sub_format, normalize_key(row.card_name)): row.card_name
            for row in existing_rows
        }

        normalized = {}
        for (sub, _), entry in entries.items():
            current_name = entry["card_name"]
            name_key = normalize_key(current_name)

            resolved = existing_name_by_key.get((sub, name_key))
            if not resolved:
                resolved = alias_by_key.get(name_key, current_name)

            entry["card_name"] = resolved
            final_key = (sub, normalize_key(resolved))

            prev = normalized.get(final_key)
            if not prev or STATUS_PRIORITY[entry["status"]] < STATUS_PRIORITY[prev["status"]]:
                normalized[final_key] = entry

        return normalized

    def _attach_cards(self, entries):
        all_cards = Card.objects.select_related("edition", "edition__format").only(
            "id", "name", "edition__format__code"
        )

        card_index = {}
        for card in all_cards.iterator(chunk_size=2000):
            card_index.setdefault(normalize_key(card.name), []).append(card)

        linked = 0
        for entry in entries.values():
            candidates = card_index.get(normalize_key(entry["card_name"]), [])
            if not candidates:
                continue

            best = next(
                (c for c in candidates if c.edition and c.edition.format and c.edition.format.code == FORMAT_CODE),
                None,
            )
            entry["card"] = best or candidates[0]
            linked += 1

        self.stdout.write(f"Entradas parseadas: {len(entries)} | enlazadas a Card: {linked}")
        return entries