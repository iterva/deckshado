"""Validador de mazos Riftbound (formato Standard).

Reglas oficiales (fuente: Deckbuilding Primer + Core Rules de Riot):
- Main Deck: exactamente 40 cartas.
- Rune Deck: 12 runas exactas.
- Champion Legend: 1 carta exacta.
- Battlefields: 3 cartas DISTINTAS (no se permiten duplicados).
- Sideboard: 8 cartas exactas, sólo en juego de torneo (opcional).
- Máximo 3 copias de cualquier carta (incluida la copia inicial del Chosen Champion).
"""
from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from .models import (
    ZONE_MAIN, ZONE_SIDE, ZONE_RUNE, ZONE_CHAMPION, ZONE_BATTLEFIELD,
)

if TYPE_CHECKING:
    from .models import RiftboundDeck


# Reglas exactas (zonas con tamaño fijo)
RULES_EXACT = {
    ZONE_MAIN: 40,
    ZONE_RUNE: 12,
    ZONE_CHAMPION: 1,
    ZONE_BATTLEFIELD: 3,
}
# Mínimos (zona puede tener más)
RULES_MIN: dict[str, int] = {}
# Reglas opcionales (sólo torneo, se valida si hay cartas)
RULES_OPTIONAL_EXACT = {
    ZONE_SIDE: 8,
}
# Vista combinada para el frontend (compatibilidad con `rules`)
RULES = {**RULES_EXACT, ZONE_SIDE: 8}
MAX_COPIES_DEFAULT = 3


def validate_riftbound_deck(deck: "RiftboundDeck") -> dict:
    """Devuelve un dict con conteos por zona, errores y warnings."""
    errors: list[str] = []
    warnings: list[str] = []
    counts: dict[str, int] = defaultdict(int)
    copies: dict[int, int] = defaultdict(int)
    bg_card_ids: list[int] = []
    rune_card_ids: set[int] = set()

    # Pre-cargar banlist
    banlist = {}
    if deck.format_id:
        from .models import RiftboundBanlistEntry
        for be in RiftboundBanlistEntry.objects.filter(format_id=deck.format_id).select_related("card"):
            banlist[be.card_id] = be

    for entry in deck.entries.all():
        counts[entry.zone] += entry.quantity
        copies[entry.card_id] += entry.quantity
        if entry.zone == ZONE_BATTLEFIELD:
            # registrar tantas instancias como quantity para chequear duplicados
            bg_card_ids.extend([entry.card_id] * entry.quantity)
        if entry.zone == ZONE_RUNE:
            rune_card_ids.add(entry.card_id)

    # Mínimos (main deck)
    for zone, minimum in RULES_MIN.items():
        actual = counts.get(zone, 0)
        if actual < minimum:
            errors.append(
                f"Zona '{zone}' tiene {actual} cartas, se requieren al menos {minimum}."
            )

    # Exactos obligatorios (runas, champion legend, battlefields)
    for zone, expected in RULES_EXACT.items():
        actual = counts.get(zone, 0)
        if actual != expected:
            errors.append(
                f"Zona '{zone}' tiene {actual} cartas, se requieren exactamente {expected}."
            )

    # Battlefields deben ser distintos
    if len(bg_card_ids) != len(set(bg_card_ids)):
        errors.append("Los 3 battlefields deben ser cartas distintas (no se permiten duplicados).")

    # Sideboard: opcional, pero si hay alguna debe ser exactamente 8 (formato torneo)
    side_count = counts.get(ZONE_SIDE, 0)
    if side_count > 0 and side_count != RULES_OPTIONAL_EXACT[ZONE_SIDE]:
        warnings.append(
            f"El sideboard de torneo requiere exactamente {RULES_OPTIONAL_EXACT[ZONE_SIDE]} cartas "
            f"(tienes {side_count}). En juego casual el sideboard no es obligatorio."
        )

    # Copias maximas (la copia inicial del Chosen Champion ya esta representada en sus entries).
    # Las runas estan exentas: pueden repetirse hasta llenar la zona de runas.
    for card_id, qty in copies.items():
        if card_id in rune_card_ids:
            continue
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
