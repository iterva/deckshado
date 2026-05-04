"""Validador de mazos Riftbound (formato Standard)."""
from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from .models import (
    ZONE_MAIN, ZONE_SIDE, ZONE_RUNE, ZONE_CHAMPION, ZONE_BATTLEFIELD,
)

if TYPE_CHECKING:
    from .models import RiftboundDeck


# Reglas Standard
RULES = {
    ZONE_MAIN: 40,
    ZONE_SIDE: 8,
    ZONE_RUNE: 12,
    ZONE_CHAMPION: 1,
    ZONE_BATTLEFIELD: 3,
}
MAX_COPIES_DEFAULT = 3


def validate_riftbound_deck(deck: "RiftboundDeck") -> dict:
    """Devuelve un dict con conteos por zona, errores y warnings."""
    errors: list[str] = []
    warnings: list[str] = []
    counts = defaultdict(int)
    copies = defaultdict(int)  # (card_id, zone) ignored — copias se cuentan globalmente

    # Pre-cargar banlist
    banlist = {}
    if deck.format_id:
        from .models import RiftboundBanlistEntry
        for be in RiftboundBanlistEntry.objects.filter(format_id=deck.format_id).select_related("card"):
            banlist[be.card_id] = be

    for entry in deck.entries.all():
        counts[entry.zone] += entry.quantity
        copies[entry.card_id] += entry.quantity

    # Conteos esperados
    for zone, expected in RULES.items():
        actual = counts.get(zone, 0)
        if actual != expected:
            errors.append(
                f"Zona '{zone}' tiene {actual} cartas, se requieren exactamente {expected}."
            )

    # Copias máximas
    for card_id, qty in copies.items():
        be = banlist.get(card_id)
        if be:
            if be.status == "banned" or be.max_copies == 0:
                errors.append(f"Carta prohibida en este formato (id={card_id}).")
                continue
            if qty > be.max_copies:
                errors.append(
                    f"Carta limitada a {be.max_copies} copia(s) (id={card_id}), tienes {qty}."
                )
                continue
        if qty > MAX_COPIES_DEFAULT:
            errors.append(
                f"Máximo {MAX_COPIES_DEFAULT} copias por carta (id={card_id}), tienes {qty}."
            )

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "counts": dict(counts),
        "rules": RULES,
    }
