"""
Normaliza nombres de cartas con discrepancias menores (espacios, mayúsculas,
guiones) para que todas las versiones de una misma carta tengan idéntico
`name` en la BD.

Estrategia por grupo (cartas con el mismo nombre normalizado):
  1. Para cada nombre distinto en el grupo, contar cuántas Cards lo usan.
  2. Elegir como canónico el nombre con más cartas; en empate, el más corto;
     en empate, el lexicográficamente menor (determinístico).
  3. Hacer trim() obligatorio (jamás se preserva espacio al final).

Uso:
    python manage.py normalize_card_names            # aplica
    python manage.py normalize_card_names --dry-run  # solo muestra
"""
import re
import unicodedata
from collections import defaultdict

from django.core.management.base import BaseCommand
from cards.models import Card


def norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    s = re.sub(r"\s+", " ", s)
    return s


def lowercase_no_accent(s: str) -> str:
    """Forma canónica preferida: lowercase, sin acentos, conservando guiones/puntuación."""
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.lower().strip()


class Command(BaseCommand):
    help = "Unifica los nombres de cartas que difieren solo en espacios/mayúsculas/guiones"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument(
            "--format", default=None,
            help="Restringir a cartas de un format_code específico (e.g. 'imp')",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        fmt = options["format"]

        qs = Card.objects.all().only("id", "name")
        if fmt:
            qs = qs.filter(edition__format__code=fmt)
            self.stdout.write(f"Filtrando por format_code={fmt!r} ({qs.count()} cartas)")

        # name_string -> list[Card]
        cards_by_name = defaultdict(list)
        for c in qs:
            cards_by_name[c.name].append(c)

        # normalized -> dict[name_string -> count]
        groups = defaultdict(dict)
        for name, cards in cards_by_name.items():
            groups[norm(name)][name] = len(cards)

        plan = []  # (canonical, [(old_name, count), ...])
        for key, variants in groups.items():
            # Solo procesar grupos con discrepancia real (>=2 variantes distintas)
            if len(variants) < 2:
                continue

            # Canonical = lowercase sin tildes, trimmed (forma preferida).
            # Si entre las variantes ya existe una forma así, se prefiere esa.
            # Si no, se construye a partir de la variante con más cartas.
            preferred_existing = [v for v in variants if v == lowercase_no_accent(v)]
            if preferred_existing:
                canonical = sorted(
                    preferred_existing,
                    key=lambda v: (-variants[v], len(v), v)
                )[0]
            else:
                # Ninguna variante está en forma preferida → construirla a partir
                # de la más popular
                source = sorted(variants.items(), key=lambda kv: (-kv[1], len(kv[0]), kv[0]))[0][0]
                canonical = lowercase_no_accent(source)

            to_rename = [(orig, variants[orig]) for orig in variants if orig != canonical]
            if to_rename:
                plan.append((canonical, to_rename))

        if not plan:
            self.stdout.write(self.style.SUCCESS("No hay discrepancias que corregir."))
            return

        total_cards = 0
        for canonical, items in sorted(plan):
            self.stdout.write(f"\n→ Canónico: {canonical!r}")
            for orig, cnt in items:
                self.stdout.write(f"     {orig!r:50}  ({cnt} carta{'s' if cnt != 1 else ''})")
                total_cards += cnt

        self.stdout.write(f"\nTotal: {len(plan)} grupos, {total_cards} cartas a renombrar")

        if dry_run:
            self.stdout.write(self.style.WARNING("(dry-run) no se aplicaron cambios"))
            return

        updated = 0
        for canonical, items in plan:
            for orig, _ in items:
                rename_qs = Card.objects.filter(name=orig)
                if fmt:
                    rename_qs = rename_qs.filter(edition__format__code=fmt)
                updated += rename_qs.update(name=canonical)

        self.stdout.write(self.style.SUCCESS(f"\n✅ {updated} cartas renombradas"))
