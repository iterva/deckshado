"""
Restaura mayúsculas y tildes en nombres de cartas guardados en minúsculas (QA #2 A4).

Estrategia, por carta con nombre que empieza en minúscula:
  1. Si otra carta con el mismo nombre normalizado (sin tildes, mayúsculas ni
     puntuación) tiene un nombre "mejor escrito" (con mayúsculas y/o tildes),
     se usa ese nombre. Es seguro: la forma correcta ya existe en la BD.
  2. Con --capitalize, a las que no tengan variante se les pone mayúscula
     inicial (no se pueden inventar tildes). Revisar el CSV antes de aplicar.

Siempre genera un CSV con los cambios (id, edición, nombre actual, nombre nuevo,
origen) para revisarlo a mano.

Uso:
    python manage.py fix_card_names --dry-run --csv cambios.csv
    python manage.py fix_card_names --csv cambios.csv
    python manage.py fix_card_names --capitalize --dry-run --csv cambios.csv
"""
import csv

from django.core.management.base import BaseCommand
from django.db import transaction

from cards.models import Card
from .normalize_card_names import norm, name_quality


class Command(BaseCommand):
    help = "Restaura mayúsculas/tildes en nombres de cartas guardados en minúsculas"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Solo muestra y escribe el CSV")
        parser.add_argument("--csv", default="fix_card_names.csv", help="Ruta del CSV de cambios")
        parser.add_argument(
            "--capitalize", action="store_true",
            help="Poner mayúscula inicial a las cartas sin variante bien escrita",
        )

    def handle(self, *args, **options):
        cards = list(Card.objects.select_related("edition").only("id", "name", "edition__title"))

        best_by_key = {}
        for c in cards:
            key = norm(c.name)
            current = best_by_key.get(key)
            if current is None or name_quality(c.name) > name_quality(current):
                best_by_key[key] = c.name

        changes = []  # (card, new_name, source)
        for c in cards:
            name = c.name.strip()
            if not name or not name[0].islower():
                continue
            best = best_by_key[norm(name)]
            if best != name and name_quality(best) > name_quality(name):
                changes.append((c, best, "variante"))
            elif options["capitalize"]:
                changes.append((c, name[0].upper() + name[1:], "mayuscula_inicial"))

        with open(options["csv"], "w", newline="", encoding="utf-8-sig") as fh:
            writer = csv.writer(fh)
            writer.writerow(["id", "edicion", "nombre_actual", "nombre_nuevo", "origen"])
            for c, new, source in changes:
                writer.writerow([c.id, c.edition.title if c.edition_id else "", c.name, new, source])

        by_source = {}
        for _, _, source in changes:
            by_source[source] = by_source.get(source, 0) + 1
        remaining = sum(1 for c in cards if c.name[:1].islower()) - len(changes)
        self.stdout.write(f"Cambios: {len(changes)} {by_source} · CSV: {options['csv']}")
        self.stdout.write(f"Seguirán en minúscula: {remaining} (necesitan fuente externa o --capitalize)")

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("(dry-run) no se aplicaron cambios"))
            return

        with transaction.atomic():
            for c, new, _ in changes:
                Card.objects.filter(pk=c.pk).update(name=new)
        self.stdout.write(self.style.SUCCESS(f"{len(changes)} cartas renombradas"))
