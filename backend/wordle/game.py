"""Lógica de selección/validación de la Wordle diaria."""
from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import date as _date
from typing import Iterable

from django.db import transaction
from django.utils import timezone

from cards.models import Card

from .models import DailyWord


MAX_ATTEMPTS = 10
MIN_LEN = 4
MAX_LEN = 12


def normalize(text: str) -> str:
    """Quita tildes, pasa a minúsculas y deja sólo letras a-zñ."""
    if not text:
        return ""
    # NFD para separar diacríticos, luego quita combining marks
    nf = unicodedata.normalize("NFD", text)
    no_diac = "".join(c for c in nf if unicodedata.category(c) != "Mn")
    lower = no_diac.lower()
    # Permitimos a-z y ñ
    return re.sub(r"[^a-zñ]", "", lower)


def _seed_for_date(d: _date) -> int:
    h = hashlib.sha256(d.isoformat().encode("utf-8")).hexdigest()
    return int(h[:12], 16)


def _candidate_cards() -> list[Card]:
    """Cartas elegibles: nombre de UNA palabra (sin espacios) y largo válido."""
    cards = list(
        Card.objects.exclude(name__contains=" ")
        .select_related("card_type", "race", "edition")
    )
    out = []
    for c in cards:
        norm = normalize(c.name)
        if MIN_LEN <= len(norm) <= MAX_LEN and norm.isalpha():
            out.append(c)
    return out


def _build_hint(card: Card) -> str:
    parts = []
    if card.card_type and card.card_type.name:
        parts.append(f"Tipo: {card.card_type.name}")
    if card.race and card.race.name:
        parts.append(f"Raza: {card.race.name}")
    if card.edition and card.edition.title:
        parts.append(f"Edición: {card.edition.title}")
    if card.cost:
        parts.append(f"Costo: {card.cost}")
    if card.damage:
        parts.append(f"Daño: {card.damage}")
    initial = normalize(card.name)[:1].upper()
    if initial:
        parts.append(f"Empieza con: {initial}")
    return " · ".join(parts)


def get_or_create_today(today: _date | None = None) -> DailyWord:
    """Devuelve la DailyWord para la fecha actual; la crea de manera determinista."""
    if today is None:
        today = timezone.localdate()
    existing = DailyWord.objects.filter(date=today).first()
    if existing:
        return existing
    cards = _candidate_cards()
    if not cards:
        raise RuntimeError("No hay cartas elegibles para la palabra del día")
    cards.sort(key=lambda c: c.id)  # orden estable
    seed = _seed_for_date(today)
    chosen = cards[seed % len(cards)]
    norm = normalize(chosen.name)
    with transaction.atomic():
        # Re-check para evitar carrera
        existing = DailyWord.objects.filter(date=today).first()
        if existing:
            return existing
        return DailyWord.objects.create(
            date=today,
            card=chosen,
            word=norm,
            display_word=chosen.name,
            length=len(norm),
            hint=_build_hint(chosen),
        )


def evaluate_guess(guess_norm: str, target: str) -> list[str]:
    """Devuelve estado por letra: 'correct' | 'present' | 'absent'."""
    n = len(target)
    result = ["absent"] * n
    target_chars = list(target)
    # Pasa 1: correctas
    for i in range(n):
        if i < len(guess_norm) and guess_norm[i] == target[i]:
            result[i] = "correct"
            target_chars[i] = "_"  # consumida
    # Pasa 2: presentes
    for i in range(n):
        if result[i] == "correct":
            continue
        if i < len(guess_norm):
            ch = guess_norm[i]
            if ch in target_chars:
                result[i] = "present"
                target_chars[target_chars.index(ch)] = "_"
    return result


def calc_score(attempts_used: int, won: bool, hint_revealed: bool) -> int:
    if not won:
        return 0
    base = (MAX_ATTEMPTS - attempts_used + 1) * 10
    if hint_revealed:
        base = max(0, base - 20)
    return base
