from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from cards.models import Card, Edition, Format
from carpeta.models import StoreOrderItem
from decks.models import DeckEntry
from wordle.models import DailyWord


class Command(BaseCommand):
    help = (
        "Valida y opcionalmente purga cartas de formatos ocultos "
        "(por defecto: pb, pe, imp_r)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--formats",
            nargs="+",
            default=["pb", "pe", "imp_r"],
            help="Codigos de formato a purgar.",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Aplica cambios. Si no se usa, solo valida (dry-run).",
        )
        parser.add_argument(
            "--prune-protected-links",
            action="store_true",
            help=(
                "Elimina referencias protegidas (DeckEntry, StoreOrderItem, DailyWord) "
                "antes de borrar cartas."
            ),
        )
        parser.add_argument(
            "--delete-empty-editions",
            action="store_true",
            help="Elimina ediciones de esos formatos que queden sin cartas.",
        )
        parser.add_argument(
            "--delete-empty-formats",
            action="store_true",
            help="Elimina formatos que queden sin ediciones (requiere --delete-empty-editions).",
        )

    def handle(self, *args, **options):
        format_codes = sorted({(code or "").strip().lower() for code in options["formats"] if code})
        if not format_codes:
            raise CommandError("Debes indicar al menos un formato en --formats.")

        apply_changes = bool(options["apply"])
        prune_protected = bool(options["prune_protected_links"])
        delete_empty_editions = bool(options["delete_empty_editions"])
        delete_empty_formats = bool(options["delete_empty_formats"])

        if delete_empty_formats and not delete_empty_editions:
            raise CommandError("--delete-empty-formats requiere --delete-empty-editions.")

        target_cards = Card.objects.filter(edition__format__code__in=format_codes)
        target_card_ids = target_cards.values_list("id", flat=True)

        target_editions = Edition.objects.filter(format__code__in=format_codes)
        target_formats = Format.objects.filter(code__in=format_codes)

        deck_entries_qs = DeckEntry.objects.filter(card_id__in=target_card_ids)
        store_items_qs = StoreOrderItem.objects.filter(card_id__in=target_card_ids)
        daily_words_qs = DailyWord.objects.filter(card_id__in=target_card_ids)

        total_cards = target_cards.count()
        total_editions = target_editions.count()
        total_formats = target_formats.count()

        protected_counts = {
            "deck_entries": deck_entries_qs.count(),
            "store_order_items": store_items_qs.count(),
            "daily_words": daily_words_qs.count(),
        }
        protected_total = sum(protected_counts.values())

        by_format = list(
            target_cards.values_list("edition__format__code")
            .order_by("edition__format__code")
        )
        format_card_counts = {}
        for (code,) in by_format:
            format_card_counts[code] = format_card_counts.get(code, 0) + 1

        self.stdout.write(self.style.MIGRATE_HEADING("Validacion de purga de formatos ocultos"))
        self.stdout.write(f"Formatos objetivo: {', '.join(format_codes)}")
        self.stdout.write(f"Formatos encontrados: {total_formats}")
        self.stdout.write(f"Ediciones objetivo: {total_editions}")
        self.stdout.write(f"Cartas objetivo: {total_cards}")
        if format_card_counts:
            self.stdout.write("Cartas por formato:")
            for code in sorted(format_card_counts):
                self.stdout.write(f"  - {code}: {format_card_counts[code]}")

        self.stdout.write("Referencias protegidas detectadas:")
        self.stdout.write(f"  - DeckEntry: {protected_counts['deck_entries']}")
        self.stdout.write(f"  - StoreOrderItem: {protected_counts['store_order_items']}")
        self.stdout.write(f"  - DailyWord: {protected_counts['daily_words']}")

        if not apply_changes:
            self.stdout.write(self.style.WARNING("Modo dry-run: no se aplicaron cambios."))
            self.stdout.write(
                "Para ejecutar borrado usa --apply "
                "(y --prune-protected-links si hay referencias protegidas)."
            )
            return

        if total_cards == 0:
            self.stdout.write(self.style.SUCCESS("No hay cartas para borrar."))
            return

        if protected_total > 0 and not prune_protected:
            raise CommandError(
                "Existen referencias protegidas. Ejecuta primero en dry-run y luego usa "
                "--apply --prune-protected-links para permitir la purga."
            )

        with transaction.atomic():
            pruned = {
                "deck_entries": 0,
                "store_order_items": 0,
                "daily_words": 0,
            }
            if prune_protected:
                pruned["deck_entries"], _ = deck_entries_qs.delete()
                pruned["store_order_items"], _ = store_items_qs.delete()
                pruned["daily_words"], _ = daily_words_qs.delete()

            deleted_cards, _ = target_cards.delete()

            deleted_editions = 0
            if delete_empty_editions:
                empty_editions_qs = target_editions.filter(cards__isnull=True).distinct()
                deleted_editions, _ = empty_editions_qs.delete()

            deleted_formats = 0
            if delete_empty_formats:
                empty_formats_qs = target_formats.filter(editions__isnull=True).distinct()
                deleted_formats, _ = empty_formats_qs.delete()

        self.stdout.write(self.style.SUCCESS("Purga completada."))
        self.stdout.write(f"DeckEntry borrados: {pruned['deck_entries']}")
        self.stdout.write(f"StoreOrderItem borrados: {pruned['store_order_items']}")
        self.stdout.write(f"DailyWord borrados: {pruned['daily_words']}")
        self.stdout.write(f"Filas borradas por delete() en cards: {deleted_cards}")
        self.stdout.write(f"Filas borradas por delete() en editions: {deleted_editions}")
        self.stdout.write(f"Filas borradas por delete() en formats: {deleted_formats}")