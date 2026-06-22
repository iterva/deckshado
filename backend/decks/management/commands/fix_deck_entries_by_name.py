"""
Corrige entradas de mazo fuera de formato sin depender de IDs fijos.

Reglas:
1) Detecta cartas fuera de formato segun deck.format.
2) Busca reemplazo por nombre normalizado dentro del formato correcto.
3) Si encuentra reemplazo:
   - Reemplaza la carta, o
   - Fusiona cantidades si la carta destino ya existe en el mazo.
4) Si no encuentra reemplazo, elimina la entrada (a menos que se use --keep-unmatched).

Uso:
    python manage.py fix_deck_entries_by_name --dry-run
    python manage.py fix_deck_entries_by_name
    python manage.py fix_deck_entries_by_name --only-format imp --owner iterva
"""
from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction

from cards.models import Card
from decks.models import Deck, DeckEntry


ESC_EDITION_SLUGS = {
    "bushido",
    "sol-naciente",
    "dominio",
    "contraataque",
    "aguila-imperial",
    "steampunk",
    "axis-mundi",
    "hijos-del-sol",
    "legado-gotico",
    "escuelas_elementales",
    "heroes_de_dharma",
}


def normalize_name(value: str) -> str:
    value = unicodedata.normalize("NFD", value or "")
    value = "".join(ch for ch in value if unicodedata.category(ch) != "Mn")
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", " ", value).strip()
    return re.sub(r"\s+", " ", value)


class Command(BaseCommand):
    help = "Sanea mazos reemplazando cartas fuera de formato por nombre normalizado."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Solo reporta cambios")
        parser.add_argument("--keep-unmatched", action="store_true", help="No elimina entradas sin reemplazo")
        parser.add_argument("--only-format", default=None, help="Filtrar mazos por formato (ej: imp)")
        parser.add_argument("--owner", default=None, help="Filtrar mazos por username propietario")
        parser.add_argument(
            "--deck-id",
            type=int,
            action="append",
            dest="deck_ids",
            help="Procesar solo deck(s) especificos (repetible)",
        )

    def handle(self, *args, **options):
        dry_run = bool(options["dry_run"])
        keep_unmatched = bool(options["keep_unmatched"])
        only_format = options.get("only_format")
        owner = options.get("owner")
        deck_ids = options.get("deck_ids") or []

        decks_qs = Deck.objects.all().order_by("id")
        if only_format:
            decks_qs = decks_qs.filter(format=only_format)
        if owner:
            decks_qs = decks_qs.filter(owner__username=owner)
        if deck_ids:
            decks_qs = decks_qs.filter(id__in=deck_ids)

        decks = list(decks_qs)
        if not decks:
            self.stdout.write(self.style.WARNING("No hay mazos para procesar con esos filtros."))
            return

        cards_by_norm = self._build_card_name_index()
        stats = {
            "decks_scanned": 0,
            "mismatches": 0,
            "replaced": 0,
            "merged": 0,
            "removed": 0,
            "unmatched": 0,
        }

        for deck in decks:
            stats["decks_scanned"] += 1
            entries = list(
                DeckEntry.objects.filter(deck=deck).select_related(
                    "card", "card__edition", "card__edition__format"
                )
            )
            for entry in entries:
                if not self._is_off_format(deck, entry.card):
                    continue

                stats["mismatches"] += 1
                replacement = self._find_replacement(deck, entry.card, cards_by_norm)
                if replacement is None:
                    stats["unmatched"] += 1
                    if keep_unmatched:
                        self.stdout.write(
                            f"[SKIP] Deck {deck.id} '{deck.name}': sin reemplazo para '{entry.card.name}'"
                        )
                        continue

                    self.stdout.write(
                        f"[REMOVE] Deck {deck.id} '{deck.name}': '{entry.card.name}' (sin reemplazo)"
                    )
                    if not dry_run:
                        entry.delete()
                        stats["removed"] += 1
                    continue

                action = "REPLACE"
                if DeckEntry.objects.filter(
                    deck=deck,
                    card_id=replacement.id,
                    is_sideboard=entry.is_sideboard,
                ).exists():
                    action = "MERGE"

                self.stdout.write(
                    f"[{action}] Deck {deck.id} '{deck.name}': '{entry.card.name}' -> '{replacement.name}'"
                )

                if dry_run:
                    continue

                with transaction.atomic():
                    target = DeckEntry.objects.select_for_update().filter(
                        deck=deck,
                        card_id=replacement.id,
                        is_sideboard=entry.is_sideboard,
                    ).first()
                    if target:
                        target.quantity += entry.quantity
                        target.save(update_fields=["quantity"])
                        entry.delete()
                        stats["merged"] += 1
                    else:
                        entry.card = replacement
                        entry.save(update_fields=["card"])
                        stats["replaced"] += 1

        summary = (
            f"decks_scanned={stats['decks_scanned']} | mismatches={stats['mismatches']} | "
            f"replaced={stats['replaced']} | merged={stats['merged']} | "
            f"removed={stats['removed']} | unmatched={stats['unmatched']}"
        )
        if dry_run:
            self.stdout.write(self.style.WARNING("(dry-run) " + summary))
        else:
            self.stdout.write(self.style.SUCCESS("OK " + summary))

    def _build_card_name_index(self):
        cards_by_norm = defaultdict(list)
        qs = Card.objects.select_related("edition", "edition__format").all()
        for card in qs:
            cards_by_norm[normalize_name(card.name)].append(card)
        return cards_by_norm

    def _is_card_allowed_for_format(self, card: Card, deck_format: str) -> bool:
        edition = getattr(card, "edition", None)
        if edition is None:
            return True

        if deck_format == "esc":
            return getattr(edition, "slug", "") in ESC_EDITION_SLUGS

        card_format = getattr(getattr(edition, "format", None), "code", None)
        if not card_format:
            return True
        return card_format == deck_format

    def _is_off_format(self, deck: Deck, card: Card) -> bool:
        return not self._is_card_allowed_for_format(card, deck.format or "imp")

    def _find_replacement(self, deck: Deck, source_card: Card, cards_by_norm):
        key = normalize_name(source_card.name)
        candidates = []
        for candidate in cards_by_norm.get(key, []):
            if candidate.id == source_card.id:
                continue
            if self._is_card_allowed_for_format(candidate, deck.format or "imp"):
                candidates.append(candidate)

        if not candidates:
            return None

        def sort_key(card: Card):
            edition = getattr(card, "edition", None)
            active = 1 if getattr(edition, "active", False) else 0
            rel = getattr(edition, "date_release", None) or date.min
            return (-active, -rel.toordinal(), card.id)

        candidates.sort(key=sort_key)
        return candidates[0]
